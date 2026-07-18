from arcengine import FrameData, GameAction, GameState

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.schemas import ActionDecision


class FakeEnvironment:
    action_space = [GameAction.ACTION1, GameAction.ACTION6]

    def __init__(self) -> None:
        self.actions: list[GameAction] = []

    def step(self, action: GameAction) -> FrameData:
        self.actions.append(action)
        return FrameData(
            game_id="ls20",
            frame=[[[1, 2, 3]]],
            state=GameState.WIN,
            available_actions=[1, 6],
        )


def test_adapter_exposes_actions_and_returns_typed_observation() -> None:
    environment = FakeEnvironment()
    adapter = ArcGameAdapter(environment=environment)

    assert adapter.available_actions == ("ACTION1", "ACTION6")

    observation = adapter.apply(
        ActionDecision(
            action="ACTION6",
            x=4,
            y=5,
            reasoning="Inspect the marked location.",
            confidence=0.7,
        )
    )

    assert environment.actions[0].action_data.x == 4
    assert environment.actions[0].action_data.y == 5
    assert observation.state is GameState.WIN
