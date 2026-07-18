from dataclasses import dataclass
from typing import Protocol

from arcengine import FrameData, GameAction

from beat_arc_agi_3.schemas import ActionDecision, GameObservation


class ArcEnvironment(Protocol):
    action_space: list[GameAction]

    def step(self, action: GameAction) -> FrameData: ...


@dataclass(frozen=True)
class ArcGameAdapter:
    """Explicit boundary for applying one validated action to ARC."""

    environment: ArcEnvironment

    @property
    def available_actions(self) -> tuple[str, ...]:
        return tuple(action.name for action in self.environment.action_space)

    def apply(self, decision: ActionDecision) -> GameObservation:
        if decision.action not in self.available_actions:
            raise ValueError(
                f"Action {decision.action} is unavailable; "
                f"legal actions are {self.available_actions}"
            )
        return GameObservation.from_frame(
            self.environment.step(decision.to_game_action())
        )
