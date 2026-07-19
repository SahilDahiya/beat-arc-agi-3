import fcntl
import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Self
from uuid import uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
)

from beat_arc_agi_3.conversation import ConversationError, JsonlConversation
from beat_arc_agi_3.events import (
    EventJournal,
    EventJournalError,
    SessionStartedEvent,
    WorldModelSnapshottedEvent,
)
from beat_arc_agi_3.synthesis import SynthesisHarness
from beat_arc_agi_3.timeline import (
    JsonlTimeline,
    TimelineError,
)
from beat_arc_agi_3.workspace import SessionWorkspace


SessionId = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]
SESSION_ID_ADAPTER = TypeAdapter(SessionId)

NOTES_TEMPLATE = """# Notes - living scientific scratchpad

Keep observations separate from hypotheses. Prune stale conclusions as new
evidence arrives.

## Confirmed mechanics

## Current level

## Level-entry grounding

### Observed facts

### Hypotheses

### Known unknowns

### Cheapest discriminating probe

## Temporary goal

- Predicate:
- Evidence:
- Falsifier:

## Hypotheses to test

## Confirmed facts

## Current plan
"""


class SessionError(RuntimeError):
    """Base error for session lifecycle and durable state."""


class SessionExistsError(SessionError):
    """Raised when explicit session creation targets an existing path."""


class SessionNotFoundError(SessionError):
    """Raised when an explicitly requested session does not exist."""


class SessionCorruptionError(SessionError):
    """Raised when persisted session state violates its contract."""


class SessionSnapshotError(SessionError):
    """Raised when an immutable level snapshot cannot be persisted."""


class SessionMetadata(BaseModel):
    """Immutable identity and creation metadata for one agent run."""

    model_config = ConfigDict(frozen=True)

    session_id: SessionId
    game_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    created_at: AwareDatetime


@dataclass(frozen=True)
class Session:
    """One explicit ARC run and its durable evidence and conversation."""

    path: Path
    metadata: SessionMetadata
    timeline: JsonlTimeline
    conversation: JsonlConversation
    events: EventJournal
    workspace: SessionWorkspace
    synthesis: SynthesisHarness

    @property
    def metadata_path(self) -> Path:
        return self.path / "session.json"

    def snapshot_world_model(
        self,
        *,
        cleared_level: int,
        revision: str,
    ) -> Path:
        """Atomically preserve one exact model revision for a cleared level."""

        if cleared_level < 0:
            raise ValueError("cleared_level must be non-negative")
        source_path = self.synthesis.model_path
        try:
            source = source_path.read_bytes()
        except OSError as exc:
            raise SessionSnapshotError(
                f"world model is not readable: {source_path}"
            ) from exc
        actual_revision = hashlib.sha256(source).hexdigest()
        if actual_revision != revision:
            raise SessionSnapshotError(
                f"world model revision {actual_revision} does not match "
                f"expected revision {revision}"
            )

        snapshot_directory = self.path / "snapshots"
        if not snapshot_directory.exists():
            snapshot_directory.mkdir()
            self._sync_directory(self.path)
        elif not snapshot_directory.is_dir():
            raise SessionSnapshotError(
                f"snapshot path is not a directory: {snapshot_directory}"
            )
        target = snapshot_directory / f"cleared_level_{cleared_level}.py"
        descriptor, temporary_name = tempfile.mkstemp(
            dir=snapshot_directory,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(source)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary_path, target)
            except FileExistsError as exc:
                raise SessionSnapshotError(
                    f"world model snapshot already exists: {target}"
                ) from exc
            self._sync_directory(snapshot_directory)
        finally:
            temporary_path.unlink(missing_ok=True)
        return target

    @classmethod
    def create(
        cls,
        *,
        sessions_root: str | Path,
        session_id: str,
        game_id: str,
        model: str,
    ) -> Self:
        validated_id = cls._validate_session_id(session_id)
        metadata = SessionMetadata(
            session_id=validated_id,
            game_id=game_id,
            model=model,
            created_at=datetime.now(UTC),
        )
        root = Path(sessions_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        session_path = root / validated_id
        root_descriptor = os.open(root, os.O_RDONLY)
        fcntl.flock(root_descriptor, fcntl.LOCK_EX)
        try:
            if session_path.exists():
                raise SessionExistsError(
                    f"session already exists: {validated_id}"
                )

            staging_path = root / f".{validated_id}.creating-{uuid4().hex}"
            staging_path.mkdir()
            try:
                JsonlTimeline.create(
                    staging_path / "timeline.jsonl",
                    game_id=metadata.game_id,
                )
                JsonlConversation.create(staging_path / "messages.jsonl")
                events = EventJournal.create(
                    staging_path / "events.jsonl",
                    session_id=metadata.session_id,
                )
                events.append(
                    turn=0,
                    event=SessionStartedEvent(
                        summary=(
                            f"Started {metadata.game_id} session with "
                            f"{metadata.model}"
                        ),
                        game_id=metadata.game_id,
                        model=metadata.model,
                    ),
                )
                metadata_path = staging_path / "session.json"
                with metadata_path.open("x", encoding="utf-8") as handle:
                    handle.write(f"{metadata.model_dump_json(indent=2)}\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                notes_path = staging_path / "notes.md"
                with notes_path.open("x", encoding="utf-8") as handle:
                    handle.write(NOTES_TEMPLATE)
                    handle.flush()
                    os.fsync(handle.fileno())
                cls._sync_directory(staging_path)
                staging_path.rename(session_path)
                cls._sync_directory(root)
            except Exception:
                if staging_path.exists():
                    shutil.rmtree(staging_path)
                raise
        finally:
            fcntl.flock(root_descriptor, fcntl.LOCK_UN)
            os.close(root_descriptor)

        timeline = JsonlTimeline(
            session_path / "timeline.jsonl",
            game_id=metadata.game_id,
        )
        conversation = JsonlConversation(session_path / "messages.jsonl")
        events = EventJournal(
            session_path / "events.jsonl",
            session_id=metadata.session_id,
        )
        workspace = SessionWorkspace(session_path)
        return cls(
            path=session_path,
            metadata=metadata,
            timeline=timeline,
            conversation=conversation,
            events=events,
            workspace=workspace,
            synthesis=SynthesisHarness(
                model_path=session_path / "world_model_v5.py",
                timeline=timeline,
            ),
        )

    @classmethod
    def open(
        cls,
        *,
        sessions_root: str | Path,
        session_id: str,
    ) -> Self:
        validated_id = cls._validate_session_id(session_id)
        session_path = Path(sessions_root).resolve() / validated_id
        if not session_path.is_dir():
            raise SessionNotFoundError(
                f"session does not exist: {validated_id}"
            )

        metadata_path = session_path / "session.json"
        try:
            metadata = SessionMetadata.model_validate_json(
                metadata_path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError, ValueError) as exc:
            raise SessionCorruptionError(
                f"invalid session metadata: {metadata_path}"
            ) from exc
        if metadata.session_id != validated_id:
            raise SessionCorruptionError(
                f"session metadata ID {metadata.session_id} does not match "
                f"directory {validated_id}"
            )

        try:
            timeline = JsonlTimeline(
                session_path / "timeline.jsonl",
                game_id=metadata.game_id,
            )
        except TimelineError as exc:
            raise SessionCorruptionError(
                f"invalid session Timeline: {session_path / 'timeline.jsonl'}"
            ) from exc
        try:
            conversation = JsonlConversation(session_path / "messages.jsonl")
        except ConversationError as exc:
            raise SessionCorruptionError(
                "invalid session conversation: "
                f"{session_path / 'messages.jsonl'}"
            ) from exc
        try:
            events = EventJournal(
                session_path / "events.jsonl",
                session_id=metadata.session_id,
            )
        except EventJournalError as exc:
            raise SessionCorruptionError(
                "invalid session event journal: "
                f"{session_path / 'events.jsonl'}"
            ) from exc
        event_entries = events.entries()
        if not event_entries or not isinstance(
            event_entries[0].event, SessionStartedEvent
        ):
            raise SessionCorruptionError(
                "event journal must start with session_started"
            )
        started = event_entries[0].event
        if started.game_id != metadata.game_id or started.model != metadata.model:
            raise SessionCorruptionError(
                "session_started identity does not match session metadata"
            )
        snapshotted_levels: set[int] = set()
        for entry in event_entries:
            event = entry.event
            if not isinstance(event, WorldModelSnapshottedEvent):
                continue
            expected_path = (
                f"snapshots/cleared_level_{event.cleared_level}.py"
            )
            if (
                event.path != expected_path
                or event.cleared_level in snapshotted_levels
            ):
                raise SessionCorruptionError(
                    f"invalid world model snapshot event: {event.path}"
                )
            snapshot_path = session_path / expected_path
            try:
                snapshot_revision = hashlib.sha256(
                    snapshot_path.read_bytes()
                ).hexdigest()
            except OSError as exc:
                raise SessionCorruptionError(
                    f"invalid world model snapshot: {snapshot_path}"
                ) from exc
            if snapshot_revision != event.revision:
                raise SessionCorruptionError(
                    f"world model snapshot revision mismatch: {snapshot_path}"
                )
            snapshotted_levels.add(event.cleared_level)
        expected_levels = {
            transition.before.levels_completed
            for transition in timeline.transitions()
            if transition.level_up
        }
        snapshots_path = session_path / "snapshots"
        invalid_snapshot_path = snapshots_path.exists() and (
            not snapshots_path.is_dir() or snapshots_path.is_symlink()
        )
        snapshot_entries = (
            tuple(snapshots_path.iterdir())
            if snapshots_path.is_dir() and not snapshots_path.is_symlink()
            else ()
        )
        invalid_snapshot_entry = any(
            not path.is_file() or path.is_symlink()
            for path in snapshot_entries
        )
        actual_snapshot_names = {path.name for path in snapshot_entries}
        expected_snapshot_names = {
            f"cleared_level_{level}.py" for level in snapshotted_levels
        }
        if (
            invalid_snapshot_path
            or invalid_snapshot_entry
            or snapshotted_levels != expected_levels
            or actual_snapshot_names != expected_snapshot_names
        ):
            raise SessionCorruptionError(
                "session snapshot evidence does not match level transitions"
            )
        workspace = SessionWorkspace(session_path)
        try:
            workspace.read_text("notes.md")
        except (OSError, UnicodeError) as exc:
            raise SessionCorruptionError(
                f"invalid session notes: {session_path / 'notes.md'}"
            ) from exc
        return cls(
            path=session_path,
            metadata=metadata,
            timeline=timeline,
            conversation=conversation,
            events=events,
            workspace=workspace,
            synthesis=SynthesisHarness(
                model_path=session_path / "world_model_v5.py",
                timeline=timeline,
            ),
        )

    @staticmethod
    def _validate_session_id(session_id: str) -> str:
        try:
            return SESSION_ID_ADAPTER.validate_python(session_id)
        except ValidationError as exc:
            raise ValueError(f"invalid session_id: {session_id!r}") from exc

    @staticmethod
    def _sync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
