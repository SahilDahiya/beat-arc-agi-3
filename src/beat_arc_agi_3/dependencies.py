from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.events import ArcEvent
from beat_arc_agi_3.synthesis import BacktestReport, BacktestTrust, BfsReport
from beat_arc_agi_3.workspace import WorkspaceTools


HistoryDetail = Literal["brief", "full", "animation"]
HistoryFlag = Literal["level_up", "dead", "win", "reset", "mismatch"]
PredictionStatus = Literal["exact", "mismatch", "unchecked"]


class HistoryQuery(BaseModel):
    """Bounded selectors and filters over immutable real transitions."""

    model_config = ConfigDict(frozen=True)

    detail: HistoryDetail = "brief"
    limit: int | None = Field(default=None, ge=1, le=100)
    indices: tuple[int, ...] | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    action: int | None = Field(default=None, ge=0, le=7)
    flags: HistoryFlag | None = None
    prediction_status: PredictionStatus | None = None

    @model_validator(mode="after")
    def validate_selectors(self) -> "HistoryQuery":
        if self.indices is not None:
            if not self.indices:
                raise ValueError("indices must contain at least one index")
            if len(self.indices) > 100:
                raise ValueError("indices cannot contain more than 100 items")
            if self.start is not None or self.end is not None:
                raise ValueError("indices cannot be combined with start or end")
        if (self.start is None) != (self.end is None):
            raise ValueError("start and end must be provided together")
        if (
            self.start is not None
            and self.end is not None
            and self.end < self.start
        ):
            raise ValueError("end must be greater than or equal to start")
        if (
            self.start is not None
            and self.end is not None
            and self.end - self.start + 1 > 100
            and self.limit is None
        ):
            raise ValueError(
                "an unbounded history range cannot exceed 100 transitions"
            )
        return self


class HistoryReader(Protocol):
    async def read(self, query: HistoryQuery) -> str: ...


class EventWriter(Protocol):
    def append(self, *, turn: int, event: ArcEvent) -> object: ...


class SynthesisTools(Protocol):
    def inspect_model(self) -> str: ...

    def model_revision(self) -> str: ...

    def run_backtest(self, *, max_details: int = 1) -> BacktestReport: ...

    def require_green(self) -> BacktestTrust: ...

    def preflight_actions(self, actions: tuple[ArcAction, ...]) -> None: ...

    def run_bfs(
        self,
        *,
        target: Literal["is_goal", "level_up", "win"],
        max_depth: int,
        node_budget: int,
        click_candidates: tuple[tuple[int, int], ...],
        timeout_seconds: int,
    ) -> BfsReport: ...


@dataclass(frozen=True)
class AgentDeps:
    """Read-only capabilities available during one deliberation turn."""

    observation: GameObservation
    history: HistoryReader
    workspace: WorkspaceTools
    synthesis: SynthesisTools
    events: EventWriter
    turn: int
