from typing import Annotated, Literal, Self

from arcengine import FrameData, FrameDataRaw, GameAction, GameState
from pydantic import BaseModel, ConfigDict, Field, model_validator


Color = Annotated[int, Field(ge=0, le=15)]
Coordinate = Annotated[int, Field(ge=0, le=63)]
Grid = tuple[tuple[Color, ...], ...]
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
    """Immutable final grid and optional animation ticks from one ARC response."""

    model_config = ConfigDict(frozen=True)

    game_id: str
    grid: Grid
    ticks: tuple[Grid, ...] = ()
    state: GameState
    levels_completed: int = Field(ge=0, le=254)
    win_levels: int = Field(ge=0, le=254)
    available_actions: tuple[int, ...]

    @model_validator(mode="after")
    def validate_observation(self) -> Self:
        for action_id in self.available_actions:
            GameAction.from_id(action_id)
        for grid in (*self.ticks, self.grid):
            if grid and any(len(row) != len(grid[0]) for row in grid):
                raise ValueError("ARC grids cannot be ragged")
        return self

    @classmethod
    def from_frame(cls, frame: FrameData | FrameDataRaw) -> Self:
        frames = tuple(
            tuple(tuple(cell for cell in row) for row in layer)
            for layer in frame.frame
        )
        return cls(
            game_id=frame.game_id,
            grid=frames[-1] if frames else (),
            ticks=frames[:-1],
            state=frame.state,
            levels_completed=frame.levels_completed,
            win_levels=frame.win_levels,
            available_actions=tuple(frame.available_actions),
        )

    @property
    def available_action_names(self) -> tuple[str, ...]:
        """Return the raw actions advertised by the ARC response."""

        return tuple(
            GameAction.from_id(action_id).name
            for action_id in self.available_actions
        )

    @property
    def legal_action_names(self) -> tuple[ActionName, ...]:
        """Return canonical state-aware actions the harness may execute."""

        if self.state is GameState.WIN:
            return ()
        if self.state is GameState.GAME_OVER:
            return ("RESET",)
        return self.available_action_names


class ArcAction(BaseModel):
    """One fully specified ARC environment action."""

    model_config = ConfigDict(frozen=True)

    action: ActionName
    x: Coordinate | None = None
    y: Coordinate | None = None

    @model_validator(mode="after")
    def validate_action_data(self) -> Self:
        game_action = GameAction.from_name(self.action)
        if game_action.is_complex() and (self.x is None or self.y is None):
            raise ValueError(f"{self.action} requires both x and y")
        if game_action.is_simple() and (self.x is not None or self.y is not None):
            raise ValueError(f"{self.action} does not accept x/y")
        return self

    def to_game_action(self) -> GameAction:
        return GameAction.from_name(self.action)

    @property
    def data(self) -> dict[str, int] | None:
        if not self.to_game_action().is_complex():
            return None
        assert self.x is not None and self.y is not None
        return {"x": self.x, "y": self.y}


class CommitActions(BaseModel):
    """A prediction-guarded queue that hands intent to the next turn."""

    model_config = ConfigDict(frozen=True)

    actions: tuple[ArcAction, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
