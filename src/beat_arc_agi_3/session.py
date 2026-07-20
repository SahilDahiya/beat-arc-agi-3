import fcntl
import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    model_validator,
)
from pydantic_ai import ModelRequest

from beat_arc_agi_3.conversation import ConversationError, JsonlConversation
from beat_arc_agi_3.events import (
    EventJournal,
    EventJournalError,
    InheritedSnapshot,
    SessionRestartedEvent,
    SessionStartedEvent,
    WorldModelSnapshottedEvent,
)
from beat_arc_agi_3.synthesis import SynthesisHarness
from beat_arc_agi_3.timeline import (
    JsonlTimeline,
    TimelineError,
)
from beat_arc_agi_3.workspace import SessionWorkspace
from beat_arc_agi_3.world_model import (
    WORLD_MODEL_FILENAME,
    inspect_world_model_source,
)


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

- Selected hypothesis:
- Competing hypothesis:
- Predicate:
- Evidence:
- Falsifier:

## Decision mode

- Mode: goal_search | discriminating_experiment
- Why:

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
    origin: Literal["fresh", "replay_restart"] = "fresh"
    parent_session_id: SessionId | None = None
    replayed_transitions: int = Field(default=0, ge=0)
    resumes_pending_deliberation: bool = False
    operation_mode: Literal[
        "normal", "online", "offline", "competition"
    ] | None = None
    environment_guid: str | None = None
    scorecard_id: str | None = None

    @model_validator(mode="after")
    def validate_lineage(self) -> Self:
        if self.origin == "fresh":
            if (
                self.parent_session_id is not None
                or self.replayed_transitions
                or self.resumes_pending_deliberation
            ):
                raise ValueError("fresh session cannot carry restart lineage")
        elif self.parent_session_id is None:
            raise ValueError("replay restart requires parent_session_id")
        return self


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
        restart_parent: "Session | None" = None,
        operation_mode: str | None = None,
        environment_guid: str | None = None,
        scorecard_id: str | None = None,
    ) -> Self:
        validated_id = cls._validate_session_id(session_id)
        if restart_parent is not None:
            if restart_parent.metadata.game_id != game_id:
                raise ValueError("restart parent game does not match child game")
            if restart_parent.metadata.session_id == validated_id:
                raise ValueError("restart child must have a new session_id")
            restart_files = cls._read_restart_files(restart_parent)
            inherited_snapshots = cls._read_inherited_snapshots(restart_parent)
            resumes_pending_deliberation = cls._has_pending_deliberation(
                restart_parent
            )
        else:
            restart_files = None
            inherited_snapshots = ()
            resumes_pending_deliberation = False
        metadata = SessionMetadata(
            session_id=validated_id,
            game_id=game_id,
            model=model,
            created_at=datetime.now(UTC),
            origin=(
                "replay_restart" if restart_parent is not None else "fresh"
            ),
            parent_session_id=(
                restart_parent.metadata.session_id
                if restart_parent is not None
                else None
            ),
            replayed_transitions=(
                len(restart_parent.timeline.transitions())
                if restart_parent is not None
                else 0
            ),
            resumes_pending_deliberation=resumes_pending_deliberation,
            operation_mode=operation_mode,
            environment_guid=environment_guid,
            scorecard_id=scorecard_id,
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
                timeline_path = staging_path / "timeline.jsonl"
                if restart_parent is None:
                    JsonlTimeline.create(
                        timeline_path,
                        game_id=metadata.game_id,
                    )
                else:
                    cls._copy_file_fsynced(
                        restart_parent.timeline.path,
                        timeline_path,
                    )
                    JsonlTimeline(timeline_path, game_id=metadata.game_id)
                conversation = JsonlConversation.create(
                    staging_path / "messages.jsonl"
                )
                if restart_parent is not None:
                    messages = restart_parent.conversation.messages()
                    if messages:
                        conversation.append(messages)
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
                if restart_parent is not None:
                    checkpoint = cls._last_observation(restart_parent)
                    events.append(
                        turn=0,
                        event=SessionRestartedEvent(
                            summary=(
                                f"Restarted from "
                                f"{restart_parent.metadata.session_id} after "
                                f"replaying {metadata.replayed_transitions} "
                                "transition(s)"
                            ),
                            parent_session_id=(
                                restart_parent.metadata.session_id
                            ),
                            replayed_transitions=metadata.replayed_transitions,
                            checkpoint_state=checkpoint.state,
                            checkpoint_levels_completed=(
                                checkpoint.levels_completed
                            ),
                            resumes_pending_deliberation=(
                                metadata.resumes_pending_deliberation
                            ),
                            inherited_snapshots=inherited_snapshots,
                        ),
                    )
                metadata_path = staging_path / "session.json"
                with metadata_path.open("x", encoding="utf-8") as handle:
                    handle.write(f"{metadata.model_dump_json(indent=2)}\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                if restart_files is None:
                    notes_path = staging_path / "notes.md"
                    with notes_path.open("x", encoding="utf-8") as handle:
                        handle.write(NOTES_TEMPLATE)
                        handle.flush()
                        os.fsync(handle.fileno())
                else:
                    workspace = SessionWorkspace(staging_path)
                    for relative_path, content in restart_files.items():
                        target = workspace.resolve_writable(relative_path).path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        workspace.atomic_write_text(target, content)
                    if inherited_snapshots:
                        snapshots_path = staging_path / "snapshots"
                        snapshots_path.mkdir()
                        for inherited in inherited_snapshots:
                            cls._copy_file_fsynced(
                                restart_parent.path / inherited.path,
                                staging_path / inherited.path,
                            )
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

    @staticmethod
    def _last_observation(session: "Session"):
        transitions = session.timeline.transitions()
        if transitions:
            return transitions[-1].after
        initial = session.timeline.initial_observation
        if initial is None:
            raise SessionCorruptionError(
                "restart parent has no initial observation"
            )
        return initial

    @staticmethod
    def _has_pending_deliberation(session: "Session") -> bool:
        last_started = 0
        last_commit = 0
        for entry in session.events.entries():
            if entry.event.type == "deliberation_started":
                last_started = entry.seq
            elif entry.event.type == "commit_accepted":
                last_commit = entry.seq
        pending = last_started > last_commit
        if not pending:
            return False
        messages = session.conversation.messages()
        if (
            not messages
            or not isinstance(messages[-1], ModelRequest)
            or messages[-1].state != "complete"
        ):
            raise SessionCorruptionError(
                "pending deliberation has no provider-valid request checkpoint"
            )
        return True

    @classmethod
    def _read_restart_files(cls, parent: "Session") -> dict[str, str]:
        files: dict[str, str] = {}
        for path in sorted(parent.path.rglob("*")):
            relative = path.relative_to(parent.path).as_posix()
            if relative == "snapshots" or relative.startswith("snapshots/"):
                continue
            if relative in SessionWorkspace._RESERVED_FILES:
                continue
            if path.is_symlink():
                raise SessionCorruptionError(
                    f"restart workspace contains symlink: {relative}"
                )
            if path.is_dir():
                continue
            if not path.is_file():
                raise SessionCorruptionError(
                    f"restart workspace contains special file: {relative}"
                )
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise SessionCorruptionError(
                    f"restart workspace file is not UTF-8: {relative}"
                ) from exc
            if relative == WORLD_MODEL_FILENAME:
                inspect_world_model_source(
                    content,
                    workspace_root=parent.path,
                )
            files[relative] = content
        if "notes.md" not in files:
            raise SessionCorruptionError("restart parent has no notes.md")
        return files

    @staticmethod
    def _read_inherited_snapshots(
        parent: "Session",
    ) -> tuple[InheritedSnapshot, ...]:
        snapshots_path = parent.path / "snapshots"
        if not snapshots_path.exists():
            return ()
        if not snapshots_path.is_dir() or snapshots_path.is_symlink():
            raise SessionCorruptionError(
                f"invalid inherited snapshot directory: {snapshots_path}"
            )
        inherited: list[InheritedSnapshot] = []
        for path in sorted(snapshots_path.iterdir()):
            if not path.is_file() or path.is_symlink():
                raise SessionCorruptionError(
                    f"invalid inherited snapshot file: {path}"
                )
            level_text = path.stem.removeprefix("cleared_level_")
            if not level_text.isdigit():
                raise SessionCorruptionError(
                    f"invalid inherited snapshot name: {path.name}"
                )
            content = path.read_bytes()
            inherited.append(
                InheritedSnapshot(
                    cleared_level=int(level_text),
                    revision=hashlib.sha256(content).hexdigest(),
                    path=f"snapshots/{path.name}",
                )
            )
        return tuple(inherited)

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
        restart_events = [
            entry.event
            for entry in event_entries
            if isinstance(entry.event, SessionRestartedEvent)
        ]
        if metadata.origin == "fresh":
            if restart_events:
                raise SessionCorruptionError(
                    "fresh session cannot contain session_restarted"
                )
        elif (
            len(restart_events) != 1
            or len(event_entries) < 2
            or event_entries[1].event is not restart_events[0]
            or restart_events[0].parent_session_id
            != metadata.parent_session_id
            or restart_events[0].replayed_transitions
            != metadata.replayed_transitions
            or restart_events[0].resumes_pending_deliberation
            != metadata.resumes_pending_deliberation
        ):
            raise SessionCorruptionError(
                "session restart event does not match metadata lineage"
            )
        snapshotted_levels: set[int] = set()
        snapshot_evidence: list[InheritedSnapshot] = []
        if restart_events:
            snapshot_evidence.extend(restart_events[0].inherited_snapshots)
        for entry in event_entries:
            event = entry.event
            if not isinstance(event, WorldModelSnapshottedEvent):
                continue
            snapshot_evidence.append(
                InheritedSnapshot(
                    cleared_level=event.cleared_level,
                    revision=event.revision,
                    path=event.path,
                )
            )
        for evidence in snapshot_evidence:
            expected_path = (
                f"snapshots/cleared_level_{evidence.cleared_level}.py"
            )
            if (
                evidence.path != expected_path
                or evidence.cleared_level in snapshotted_levels
            ):
                raise SessionCorruptionError(
                    f"invalid world model snapshot event: {evidence.path}"
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
            if snapshot_revision != evidence.revision:
                raise SessionCorruptionError(
                    f"world model snapshot revision mismatch: {snapshot_path}"
                )
            snapshotted_levels.add(evidence.cleared_level)
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

    @staticmethod
    def _copy_file_fsynced(source: Path, target: Path) -> None:
        with (
            source.open("rb") as source_handle,
            target.open("xb") as target_handle,
        ):
            shutil.copyfileobj(source_handle, target_handle)
            target_handle.flush()
            os.fsync(target_handle.fileno())
