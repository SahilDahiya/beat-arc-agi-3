import pytest
from arcengine import FrameData, GameState
from pydantic import ValidationError

from beat_arc_agi_3.schemas import ArcAction, CommitActions, GameObservation


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
    assert observation.grid == ((0, 0, 0),)
    assert observation.ticks == ()


def test_observation_separates_intermediate_ticks_from_the_final_grid() -> None:
    frame = FrameData(
        game_id="ls20",
        frame=[[[1]], [[2]], [[3]]],
        state=GameState.NOT_FINISHED,
        available_actions=[1],
    )

    observation = GameObservation.from_frame(frame)

    assert observation.grid == ((3,),)
    assert observation.ticks == (((1,),), ((2,),))


def test_game_over_observation_preserves_raw_actions_but_only_reset_is_legal() -> None:
    observation = GameObservation.from_frame(
        FrameData(
            game_id="ls20",
            frame=[[[1]]],
            state=GameState.GAME_OVER,
            available_actions=[1, 2, 3, 4],
        )
    )

    assert observation.available_action_names == (
        "ACTION1",
        "ACTION2",
        "ACTION3",
        "ACTION4",
    )
    assert observation.legal_action_names == ("RESET",)


def test_simple_action_converts_to_game_action() -> None:
    decision = ArcAction(action="ACTION1")

    assert decision.to_game_action().name == "ACTION1"


def test_complex_action_requires_coordinates() -> None:
    with pytest.raises(ValidationError, match="requires both x and y"):
        ArcAction(action="ACTION6")


def test_simple_action_rejects_coordinates() -> None:
    with pytest.raises(ValidationError, match="does not accept x/y"):
        ArcAction(action="ACTION1", x=2)


def test_complex_action_converts_coordinates() -> None:
    decision = ArcAction(action="ACTION6", x=12, y=31)

    assert decision.to_game_action().name == "ACTION6"
    assert decision.data == {"x": 12, "y": 31}
    assert decision.model_dump() == {"action": "ACTION6", "x": 12, "y": 31}


def test_action_coordinates_stay_inside_the_arc_grid() -> None:
    with pytest.raises(ValidationError):
        ArcAction(action="ACTION6", x=64, y=0)


def test_commit_requires_at_least_one_action() -> None:
    with pytest.raises(ValidationError):
        CommitActions(
            actions=[],
            reason="No action selected.",
            suggestion="Continue reasoning.",
        )


def test_commit_accepts_a_multi_action_experimental_queue() -> None:
    commit = CommitActions(
        actions=[ArcAction(action="ACTION1"), ArcAction(action="ACTION2")],
        reason="Follow the known route, then test the uncertain interaction.",
        suggestion="Inspect the frontier action if prediction disagrees.",
    )

    assert [action.action for action in commit.actions] == ["ACTION1", "ACTION2"]
