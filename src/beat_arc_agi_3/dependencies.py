from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.workspace import WorkspaceTools


HistoryDetail = Literal["brief", "full", "animation"]


class HistoryQuery(BaseModel):
    """Bounded query supported by the first history-reader contract."""

    model_config = ConfigDict(frozen=True)

    detail: HistoryDetail = "brief"
    limit: int = Field(default=20, ge=1, le=100)


class HistoryReader(Protocol):
    async def read(self, query: HistoryQuery) -> str: ...


@dataclass(frozen=True)
class AgentDeps:
    """Read-only capabilities available during one deliberation turn."""

    observation: GameObservation
    history: HistoryReader
    workspace: WorkspaceTools
