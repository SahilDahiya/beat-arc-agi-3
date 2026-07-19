import fcntl
import os
import shutil
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


class SessionError(RuntimeError):
    """Base error for session lifecycle and durable state."""


class SessionExistsError(SessionError):
    """Raised when explicit session creation targets an existing path."""


class SessionNotFoundError(SessionError):
    """Raised when an explicitly requested session does not exist."""


class SessionCorruptionError(SessionError):
    """Raised when persisted session state violates its contract."""


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
    workspace: SessionWorkspace

    @property
    def metadata_path(self) -> Path:
        return self.path / "session.json"

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
                metadata_path = staging_path / "session.json"
                with metadata_path.open("x", encoding="utf-8") as handle:
                    handle.write(f"{metadata.model_dump_json(indent=2)}\n")
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
        return cls(
            path=session_path,
            metadata=metadata,
            timeline=timeline,
            conversation=conversation,
            workspace=SessionWorkspace(session_path),
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
        return cls(
            path=session_path,
            metadata=metadata,
            timeline=timeline,
            conversation=conversation,
            workspace=SessionWorkspace(session_path),
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
