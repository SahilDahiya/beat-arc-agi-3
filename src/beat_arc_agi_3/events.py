from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, Self

from arcengine import GameState
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
)

from beat_arc_agi_3.schemas import ArcAction


class EventJournalError(RuntimeError):
    """Base error for the canonical append-only event journal."""


class EventJournalNotFoundError(EventJournalError):
    """Raised when an event journal has not been explicitly created."""


class EventJournalCorruptionError(EventJournalError):
    """Raised when persisted events violate the canonical contract."""


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1)


class SessionStartedEvent(_Event):
    type: Literal["session_started"] = "session_started"
    game_id: str = Field(min_length=1)
    model: str = Field(min_length=1)


class TurnStartedEvent(_Event):
    type: Literal["turn_started"] = "turn_started"
    state: GameState
    levels_completed: int = Field(ge=0)
    available_actions: tuple[str, ...]


class DeliberationStartedEvent(_Event):
    type: Literal["deliberation_started"] = "deliberation_started"


class ToolStartedEvent(_Event):
    type: Literal["tool_started"] = "tool_started"
    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)


class ToolCompletedEvent(_Event):
    type: Literal["tool_completed"] = "tool_completed"
    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    duration_ms: int = Field(ge=0)


class ToolFailedEvent(_Event):
    type: Literal["tool_failed"] = "tool_failed"
    tool_call_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    duration_ms: int = Field(ge=0)
    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class WorldModelInstalledEvent(_Event):
    type: Literal["world_model_installed"] = "world_model_installed"
    revision: str = Field(min_length=1)


class BacktestCompletedEvent(_Event):
    type: Literal["backtest_completed"] = "backtest_completed"
    revision: str = Field(min_length=1)
    status: Literal["green", "mismatch"]
    timeline_transitions: int = Field(ge=0)
    exact_transitions: int = Field(ge=0)


class CommitAcceptedEvent(_Event):
    type: Literal["commit_accepted"] = "commit_accepted"
    actions: tuple[ArcAction, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class ActionStartedEvent(_Event):
    type: Literal["action_started"] = "action_started"
    action_number: int = Field(ge=1)
    transition_index: int = Field(ge=0)
    action: ArcAction
    model_revision: str = Field(min_length=1)
    prediction_mode: Literal["certified", "unchecked"]


class ActionCompletedEvent(_Event):
    type: Literal["action_completed"] = "action_completed"
    action_number: int = Field(ge=1)
    transition_index: int = Field(ge=0)
    action: ArcAction
    model_revision: str = Field(min_length=1)
    prediction_status: Literal["exact", "mismatch", "unchecked"]
    state: GameState
    levels_completed: int = Field(ge=0)
    level_up: bool
    dead: bool
    win: bool


class WorldModelSnapshottedEvent(_Event):
    type: Literal["world_model_snapshotted"] = "world_model_snapshotted"
    cleared_level: int = Field(ge=0)
    revision: str = Field(min_length=1)
    prediction_status: Literal["exact", "mismatch", "unchecked"]
    path: str = Field(min_length=1)


class PredictionMismatchEvent(_Event):
    type: Literal["prediction_mismatch"] = "prediction_mismatch"
    transition_index: int = Field(ge=0)
    revision: str = Field(min_length=1)


class QueueCancelledEvent(_Event):
    type: Literal["queue_cancelled"] = "queue_cancelled"
    reason: Literal[
        "max_actions",
        "illegal_action",
        "prediction_mismatch",
        "level_up",
        "game_over",
        "win",
    ]
    committed_actions: int = Field(ge=1)
    executed_actions: int = Field(ge=0)


class TurnCompletedEvent(_Event):
    type: Literal["turn_completed"] = "turn_completed"
    committed_actions: int = Field(ge=1)
    executed_actions: int = Field(ge=0)
    queue_stop: str = Field(min_length=1)


class RunCompletedEvent(_Event):
    type: Literal["run_completed"] = "run_completed"
    stop_reason: Literal["win", "max_actions", "max_turns", "no_legal_actions"]
    turns: int = Field(ge=0)
    actions: int = Field(ge=0)
    state: GameState
    levels_completed: int = Field(ge=0)
    win_levels: int = Field(ge=0)


class RunFailedEvent(_Event):
    type: Literal["run_failed"] = "run_failed"
    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


class RunInterruptedEvent(_Event):
    type: Literal["run_interrupted"] = "run_interrupted"
    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)


ArcEvent = Annotated[
    SessionStartedEvent
    | TurnStartedEvent
    | DeliberationStartedEvent
    | ToolStartedEvent
    | ToolCompletedEvent
    | ToolFailedEvent
    | WorldModelInstalledEvent
    | BacktestCompletedEvent
    | CommitAcceptedEvent
    | ActionStartedEvent
    | ActionCompletedEvent
    | WorldModelSnapshottedEvent
    | PredictionMismatchEvent
    | QueueCancelledEvent
    | TurnCompletedEvent
    | RunCompletedEvent
    | RunFailedEvent
    | RunInterruptedEvent,
    Field(discriminator="type"),
]


class EventJournalEntry(BaseModel):
    """One immutable, totally ordered event from one ARC Session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    seq: int = Field(ge=1)
    timestamp: AwareDatetime
    session_id: str = Field(min_length=1)
    turn: int = Field(ge=0)
    event: ArcEvent


_ENTRY_ADAPTER = TypeAdapter(EventJournalEntry)


class EventJournal:
    """Single-process append-only storage for canonical ARC lifecycle events."""

    def __init__(self, path: str | Path, *, session_id: str) -> None:
        self.path = Path(path)
        if not session_id:
            raise ValueError("session_id is required")
        self.session_id = session_id
        if not self.path.exists():
            raise EventJournalNotFoundError(
                f"event journal does not exist: {self.path}"
            )
        if not self.path.is_file():
            raise EventJournalError(
                f"event journal path is not a file: {self.path}"
            )
        self._lock = threading.Lock()
        self._entries = self._load()

    @classmethod
    def create(cls, path: str | Path, *, session_id: str) -> Self:
        event_path = Path(path)
        event_path.parent.mkdir(parents=True, exist_ok=True)
        with event_path.open("x", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        return cls(event_path, session_id=session_id)

    def entries(self) -> tuple[EventJournalEntry, ...]:
        with self._lock:
            return tuple(self._entries)

    def append(self, *, turn: int, event: ArcEvent) -> EventJournalEntry:
        with self._lock:
            entry = EventJournalEntry(
                seq=len(self._entries) + 1,
                timestamp=datetime.now(UTC),
                session_id=self.session_id,
                turn=turn,
                event=event,
            )
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        f"{entry.model_dump_json(exclude_none=True)}\n"
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileNotFoundError as exc:
                raise EventJournalNotFoundError(
                    f"event journal does not exist: {self.path}"
                ) from exc
            self._entries.append(entry)
            return entry

    def _load(self) -> list[EventJournalEntry]:
        entries: list[EventJournalEntry] = []
        try:
            handle = self.path.open("r", encoding="utf-8")
        except FileNotFoundError as exc:
            raise EventJournalNotFoundError(
                f"event journal does not exist: {self.path}"
            ) from exc

        with handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    raise EventJournalCorruptionError(
                        f"event journal line {line_number} is empty"
                    )
                try:
                    raw = json.loads(line)
                    entry = _ENTRY_ADAPTER.validate_python(raw)
                except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                    raise EventJournalCorruptionError(
                        f"invalid event on line {line_number}: {exc}"
                    ) from exc
                expected_seq = len(entries) + 1
                if entry.seq != expected_seq:
                    raise EventJournalCorruptionError(
                        f"event line {line_number} has sequence {entry.seq}; "
                        f"expected {expected_seq}"
                    )
                if entry.session_id != self.session_id:
                    raise EventJournalCorruptionError(
                        f"event journal belongs to session {entry.session_id}; "
                        f"expected {self.session_id}"
                    )
                entries.append(entry)
        return entries


__all__ = [
    "ActionCompletedEvent",
    "ActionStartedEvent",
    "ArcEvent",
    "BacktestCompletedEvent",
    "CommitAcceptedEvent",
    "DeliberationStartedEvent",
    "EventJournal",
    "EventJournalCorruptionError",
    "EventJournalEntry",
    "EventJournalError",
    "EventJournalNotFoundError",
    "PredictionMismatchEvent",
    "QueueCancelledEvent",
    "RunCompletedEvent",
    "RunFailedEvent",
    "RunInterruptedEvent",
    "SessionStartedEvent",
    "ToolCompletedEvent",
    "ToolFailedEvent",
    "ToolStartedEvent",
    "TurnCompletedEvent",
    "TurnStartedEvent",
    "WorldModelInstalledEvent",
    "WorldModelSnapshottedEvent",
]
