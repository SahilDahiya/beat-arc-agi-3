from dataclasses import dataclass
from typing import Protocol

from arcengine import FrameData, FrameDataRaw, GameAction

from beat_arc_agi_3.schemas import ArcAction, GameObservation


class ArcEnvironment(Protocol):
    action_space: list[GameAction]

    def reset(self) -> FrameData | FrameDataRaw | None: ...

    def step(
        self,
        action: GameAction,
        data: dict[str, int] | None = None,
    ) -> FrameData | FrameDataRaw | None: ...


@dataclass(frozen=True)
class ArcGameAdapter:
    """Explicit boundary for applying one validated action to ARC."""

    environment: ArcEnvironment

    @property
    def available_actions(self) -> tuple[str, ...]:
        return tuple(action.name for action in self.environment.action_space)

    def reset(self) -> GameObservation:
        frame = self.environment.reset()
        if frame is None:
            raise RuntimeError("ARC environment reset returned no observation")
        return GameObservation.from_frame(frame)

    def apply(self, action: ArcAction) -> GameObservation:
        if (
            action.action != GameAction.RESET.name
            and action.action not in self.available_actions
        ):
            raise ValueError(
                f"Action {action.action} is unavailable; "
                f"legal actions are {self.available_actions}"
            )
        frame = self.environment.step(action.to_game_action(), data=action.data)
        if frame is None:
            raise RuntimeError("ARC environment step returned no observation")
        return GameObservation.from_frame(frame)
