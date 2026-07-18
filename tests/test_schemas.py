import pytest
from arcengine import FrameData, GameState
from pydantic import ValidationError

from beat_arc_agi_3.schemas import ActionDecision, GameObservation


def test_observation_normalizes_frame_data() -> None:
    frame = FrameData(
        game_id="ls20",
        frame=[[[0, 0, 0]]],
        state=GameState.NOT_FINISHED,
        levels_completed=1,
        win_levels=3,
        available_actions=[1, 6],
    )

    observation = GameObservation.from_frame(frame)

    assert observation.game_id == "ls20"
    assert observation.state is GameState.NOT_FINISHED
    assert observation.available_actions == (1, 6)


def test_simple_action_converts_to_game_action() -> None:
    decision = ActionDecision(
        action="ACTION1",
        reasoning="Test the first available movement.",
        confidence=0.5,
    )

    assert decision.to_game_action().name == "ACTION1"


def test_complex_action_requires_coordinates() -> None:
    with pytest.raises(ValidationError, match="requires both x and y"):
        ActionDecision(action="ACTION6", reasoning="Click", confidence=0.5)


def test_simple_action_rejects_coordinates() -> None:
    with pytest.raises(ValidationError, match="does not accept x/y"):
        ActionDecision(
            action="ACTION1",
            x=2,
            reasoning="Movement",
            confidence=0.5,
        )


def test_complex_action_converts_coordinates() -> None:
    decision = ActionDecision(
        action="ACTION6",
        x=12,
        y=31,
        reasoning="Inspect the target.",
        confidence=0.8,
    )

    action = decision.to_game_action()

    assert action.name == "ACTION6"
    assert action.action_data.x == 12
    assert action.action_data.y == 31
