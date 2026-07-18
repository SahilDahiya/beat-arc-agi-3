from typing import Annotated, Literal, Self

from arcengine import FrameData, GameAction, GameState
from pydantic import BaseModel, ConfigDict, Field, model_validator


Color = Annotated[int, Field(ge=0, le=15)]
Coordinate = Annotated[int, Field(ge=0, le=63)]
ActionName = Literal[
    "RESET",
    "ACTION1",
    "ACTION2",
    "ACTION3",
    "ACTION4",
    "ACTION5",
    "ACTION6",
    "ACTION7",
]


class GameObservation(BaseModel):
    """Immutable, toolkit-independent view of one ARC frame."""

    model_config = ConfigDict(frozen=True)

    game_id: str
    frame: tuple[tuple[tuple[Color, ...], ...], ...]
    state: GameState
    levels_completed: int = Field(ge=0, le=254)
    win_levels: int = Field(ge=0, le=254)
    available_actions: tuple[int, ...]

    @model_validator(mode="after")
    def validate_available_actions(self) -> Self:
        for action_id in self.available_actions:
            GameAction.from_id(action_id)
        return self

    @classmethod
    def from_frame(cls, frame: FrameData) -> Self:
        return cls(
            game_id=frame.game_id,
            frame=tuple(
                tuple(tuple(cell for cell in row) for row in layer)
                for layer in frame.frame
            ),
            state=frame.state,
            levels_completed=frame.levels_completed,
            win_levels=frame.win_levels,
            available_actions=tuple(frame.available_actions),
        )

    @property
    def available_action_names(self) -> tuple[str, ...]:
        return tuple(
            GameAction.from_id(action_id).name
            for action_id in self.available_actions
        )


class ActionDecision(BaseModel):
    """One fully specified ARC action proposed by the agent."""

    model_config = ConfigDict(frozen=True)

    action: ActionName
    x: Coordinate | None = None
    y: Coordinate | None = None
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_action_data(self) -> Self:
        game_action = GameAction.from_name(self.action)
        if game_action.is_complex() and (self.x is None or self.y is None):
            raise ValueError(f"{self.action} requires both x and y")
        if game_action.is_simple() and (self.x is not None or self.y is not None):
            raise ValueError(f"{self.action} does not accept x/y")
        return self

    def to_game_action(self) -> GameAction:
        action = GameAction.from_name(self.action)
        if action.is_complex():
            assert self.x is not None and self.y is not None
            action.set_data({"x": self.x, "y": self.y})
        else:
            action.set_data({})
        return action


class CommitActions(BaseModel):
    """A queue that ends deliberation and hands intent to the next turn."""

    model_config = ConfigDict(frozen=True)

    actions: tuple[ActionDecision, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
