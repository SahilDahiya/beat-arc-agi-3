from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.events import ArcEvent
from beat_arc_agi_3.synthesis import BacktestReport, BacktestTrust, BfsReport
from beat_arc_agi_3.workspace import WorkspaceTools


HistoryDetail = Literal["brief", "full", "animation"]


class HistoryQuery(BaseModel):
    """Bounded query supported by the first history-reader contract."""

    model_config = ConfigDict(frozen=True)

    detail: HistoryDetail = "brief"
    limit: int = Field(default=20, ge=1, le=100)


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
