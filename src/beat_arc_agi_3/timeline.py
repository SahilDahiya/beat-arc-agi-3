import json
import os
from pathlib import Path
from typing import Literal, Self

from arcengine import GameState
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from beat_arc_agi_3.schemas import ArcAction, GameObservation


class TimelineError(RuntimeError):
    """Base error for timeline invariants and persistence."""


class TimelineChainError(TimelineError):
    """Raised when a proposed record does not continue the Timeline."""


class TimelineCorruptionError(TimelineError):
    """Raised when persisted Timeline data violates the canonical contract."""


class TimelineNotFoundError(TimelineError):
    """Raised when code attempts to open a Timeline that was not created."""


class Transition(BaseModel):
    """One derived, immutable real-environment transition."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    before: GameObservation
    action: ArcAction
    after: GameObservation
    level_up: bool
    dead: bool
    win: bool

    @model_validator(mode="after")
    def validate_transition(self) -> Self:
        if self.before.game_id != self.after.game_id:
            raise ValueError("before and after observations have different game IDs")

        expected = {
            "level_up": (
                self.after.levels_completed > self.before.levels_completed
            ),
            "dead": self.after.state is GameState.GAME_OVER,
            "win": self.after.state is GameState.WIN,
        }
        actual = {
            "level_up": self.level_up,
            "dead": self.dead,
            "win": self.win,
        }
        if actual != expected:
            raise ValueError(
                "terminal flags do not match observations: "
                f"expected {expected}, got {actual}"
            )
        return self

    @classmethod
    def create(
        cls,
        *,
        index: int,
        before: GameObservation,
        action: ArcAction,
        after: GameObservation,
    ) -> Self:
        return cls(
            index=index,
            before=before,
            action=action,
            after=after,
            level_up=after.levels_completed > before.levels_completed,
            dead=after.state is GameState.GAME_OVER,
            win=after.state is GameState.WIN,
        )


class InitialObservationRecord(BaseModel):
    """The single initial observation at the head of a persisted Timeline."""

    model_config = ConfigDict(frozen=True)

    type: Literal["initial_observation"] = "initial_observation"
    observation: GameObservation


class ActionResultRecord(BaseModel):
    """One persisted action and its resulting observation."""

    model_config = ConfigDict(frozen=True)

    type: Literal["action_result"] = "action_result"
    index: int = Field(ge=0)
    action: ArcAction
    after: GameObservation


TimelineRecord = InitialObservationRecord | ActionResultRecord


class JsonlTimeline:
    """Single-writer, append-only JSONL storage for real ARC evidence."""

    def __init__(self, path: str | Path, *, game_id: str) -> None:
        self.path = Path(path)
        if not game_id:
            raise ValueError("game_id is required")
        self.game_id = game_id
        if not self.path.exists():
            raise TimelineNotFoundError(f"timeline does not exist: {self.path}")
        if not self.path.is_file():
            raise TimelineError(f"timeline path is not a file: {self.path}")
        self._initial, self._transitions = self._load()

    @classmethod
    def create(cls, path: str | Path, *, game_id: str) -> Self:
        if not game_id:
            raise ValueError("game_id is required")
        timeline_path = Path(path)
        timeline_path.parent.mkdir(parents=True, exist_ok=True)
        with timeline_path.open("x", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        return cls(timeline_path, game_id=game_id)

    @property
    def initial_observation(self) -> GameObservation | None:
        return self._initial

    def transitions(self) -> tuple[Transition, ...]:
        return tuple(self._transitions)

    def initialize(self, observation: GameObservation) -> None:
        if self._initial is not None:
            raise TimelineChainError("timeline is already initialized")
        if observation.game_id != self.game_id:
            raise TimelineChainError(
                f"initial observation must match session game {self.game_id}"
            )

        self._append_record(InitialObservationRecord(observation=observation))
        self._initial = observation

    def append(
        self,
        *,
        action: ArcAction,
        after: GameObservation,
    ) -> Transition:
        if self._initial is None:
            raise TimelineChainError(
                "timeline requires an initial observation before actions"
            )
        if after.game_id != self.game_id:
            raise TimelineChainError(
                f"result observation must match session game {self.game_id}"
            )

        before = (
            self._transitions[-1].after
            if self._transitions
            else self._initial
        )
        transition = Transition.create(
            index=len(self._transitions),
            before=before,
            action=action,
            after=after,
        )
        self._append_record(
            ActionResultRecord(
                index=transition.index,
                action=transition.action,
                after=transition.after,
            )
        )
        self._transitions.append(transition)
        return transition

    def _append_record(self, record: TimelineRecord) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(f"{record.model_dump_json(exclude_none=True)}\n")
                handle.flush()
                os.fsync(handle.fileno())
        except FileNotFoundError as exc:
            raise TimelineNotFoundError(
                f"timeline does not exist: {self.path}"
            ) from exc

    def _load(self) -> tuple[GameObservation | None, list[Transition]]:
        initial: GameObservation | None = None
        transitions: list[Transition] = []
        try:
            handle = self.path.open("r", encoding="utf-8")
        except FileNotFoundError as exc:
            raise TimelineNotFoundError(
                f"timeline does not exist: {self.path}"
            ) from exc

        with handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    raise TimelineCorruptionError(
                        f"timeline line {line_number} is empty"
                    )
                try:
                    raw = json.loads(line)
                    record_type = raw.get("type")
                    if record_type == "initial_observation":
                        record: TimelineRecord = (
                            InitialObservationRecord.model_validate(raw)
                        )
                    elif record_type == "action_result":
                        record = ActionResultRecord.model_validate(raw)
                    else:
                        raise ValueError(f"unknown record type {record_type!r}")
                except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                    raise TimelineCorruptionError(
                        f"invalid timeline record on line {line_number}: {exc}"
                    ) from exc

                if isinstance(record, InitialObservationRecord):
                    if line_number != 1 or initial is not None:
                        raise TimelineCorruptionError(
                            "initial observation must be the first and only "
                            "initial record"
                        )
                    if record.observation.game_id != self.game_id:
                        raise TimelineCorruptionError(
                            f"timeline belongs to game "
                            f"{record.observation.game_id}; expected {self.game_id}"
                        )
                    initial = record.observation
                    continue

                if initial is None:
                    raise TimelineCorruptionError(
                        "action result exists before an initial observation"
                    )
                expected_index = len(transitions)
                if record.index != expected_index:
                    raise TimelineCorruptionError(
                        f"timeline line {line_number} has index {record.index}; "
                        f"expected {expected_index}"
                    )
                if record.after.game_id != self.game_id:
                    raise TimelineCorruptionError(
                        f"timeline line {line_number} belongs to game "
                        f"{record.after.game_id}; expected {self.game_id}"
                    )
                before = transitions[-1].after if transitions else initial
                transitions.append(
                    Transition.create(
                        index=record.index,
                        before=before,
                        action=record.action,
                        after=record.after,
                    )
                )
        return initial, transitions
