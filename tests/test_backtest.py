from pathlib import Path

import pytest
from arcengine import FrameData, GameState

from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.synthesis import (
    BacktestRequiredError,
    SynthesisHarness,
)
from beat_arc_agi_3.timeline import JsonlTimeline
from beat_arc_agi_3.timeline import ModelPredictionRecord
from beat_arc_agi_3.world_model import WorldModelContractError


MODEL = '''
def init_state(entry_grid):
    return {"steps": 0}


def predict(state, grid, action, x=None, y=None):
    result = [row[:] for row in grid]
    result[0][0] += 1
    return (
        result,
        {"level_up": False, "dead": False, "win": False},
        {"steps": state["steps"] + 1},
    )


def is_goal(state, grid):
    return False
'''.lstrip()


def observation(
    value: int,
    *,
    state: GameState = GameState.NOT_FINISHED,
    levels_completed: int = 0,
) -> GameObservation:
    return GameObservation.from_frame(
        FrameData(
            game_id="test-game",
            frame=[[[value]]],
            state=state,
            levels_completed=levels_completed,
            available_actions=[1],
        )
    )


def build_harness(
    tmp_path: Path,
    resulting_values: list[int],
    *,
    source: str = MODEL,
) -> SynthesisHarness:
    model_path = tmp_path / "world_model_v5.py"
    model_path.write_text(source, encoding="utf-8")
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))
    for value in resulting_values:
        timeline.append(
            action=ArcAction(action="ACTION1"),
            after=observation(value),
            model_revision="setup",
            prediction=ModelPredictionRecord(
                grid=((value,),),
                level_up=False,
                dead=False,
                win=False,
            ),
        )
    return SynthesisHarness(
        model_path=model_path,
        timeline=timeline,
    )


def test_backtest_marks_an_exact_revision_green(tmp_path: Path) -> None:
    harness = build_harness(tmp_path, [1, 2])

    report = harness.run_backtest(max_details=3)

    assert report.status == "green"
    assert report.transitions_checked == 2
    assert report.exact_transitions == 2
    assert report.mismatch is None
    assert harness.require_green().revision == report.revision


def test_empty_backtest_smoke_tests_predict_output(tmp_path: Path) -> None:
    malformed = '''
def init_state(entry_grid):
    return {}


def predict(state, grid, action, x=None, y=None):
    rows = ["".join(str(value) for value in row) for row in grid]
    return rows, {"level_up": False, "dead": False, "win": False}, state


def is_goal(state, grid):
    return False
'''.lstrip()
    harness = build_harness(tmp_path, [], source=malformed)

    with pytest.raises(
        WorldModelContractError,
        match="predicted grid rows must be arrays",
    ):
        harness.run_backtest()


def test_backtest_reports_the_earliest_counterexample(tmp_path: Path) -> None:
    harness = build_harness(tmp_path, [1, 3])

    report = harness.run_backtest(max_details=3)

    assert report.status == "mismatch"
    assert report.transitions_checked == 2
    assert report.exact_transitions == 1
    assert report.mismatch is not None
    assert report.mismatch.transition_index == 1
    assert report.mismatch.action.action == "ACTION1"
    assert report.mismatch.differing_cells == 1
    assert report.mismatch.differences[0].model_dump() == {
        "row": 0,
        "column": 0,
        "predicted": 2,
        "actual": 3,
    }
    with pytest.raises(BacktestRequiredError, match="has a mismatch"):
        harness.require_green()


def test_editing_the_model_invalidates_green_status(tmp_path: Path) -> None:
    harness = build_harness(tmp_path, [1])
    first = harness.run_backtest()
    model_path = tmp_path / "world_model_v5.py"
    model_path.write_text(MODEL + "\n# new revision\n", encoding="utf-8")

    with pytest.raises(
        BacktestRequiredError,
        match="current world model revision has not been backtested",
    ):
        harness.require_green()

    second = harness.run_backtest()
    assert second.revision != first.revision


def test_new_timeline_evidence_invalidates_green_status(tmp_path: Path) -> None:
    harness = build_harness(tmp_path, [1])
    harness.run_backtest()
    harness.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(2),
        model_revision="setup",
        prediction=ModelPredictionRecord(
            grid=((2,),),
            level_up=False,
            dead=False,
            win=False,
        ),
    )

    with pytest.raises(
        BacktestRequiredError,
        match="current Timeline has not been backtested",
    ):
        harness.require_green()


def test_exact_online_prediction_advances_green_trust(tmp_path: Path) -> None:
    harness = build_harness(tmp_path, [])
    harness.run_backtest()

    pending = harness.predict_action(ArcAction(action="ACTION1"))
    transition = harness.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(1),
        model_revision=pending.revision,
        prediction=pending.record,
    )

    assert harness.observe(pending, transition) is True
    assert harness.require_green().timeline_transitions == 1


def test_multi_action_preflight_advances_modeled_state_between_actions(
    tmp_path: Path,
) -> None:
    source = '''
def init_state(entry_grid):
    return {"steps": 0}


def predict(state, grid, action, x=None, y=None):
    if action == "ACTION2" and state["steps"] != 1:
        raise ValueError("ACTION2 requires the modeled ACTION1 prefix")
    return (
        [[grid[0][0] + 1]],
        {"level_up": False, "dead": False, "win": False},
        {"steps": state["steps"] + 1},
    )


def is_goal(state, grid):
    return False
'''.lstrip()
    harness = build_harness(tmp_path, [], source=source)
    harness.run_backtest()

    harness.preflight_actions(
        (
            ArcAction(action="ACTION1"),
            ArcAction(action="ACTION2"),
        )
    )


def test_online_misprediction_invalidates_green_trust(tmp_path: Path) -> None:
    harness = build_harness(tmp_path, [])
    harness.run_backtest()

    pending = harness.predict_action(ArcAction(action="ACTION1"))
    transition = harness.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(9),
        model_revision=pending.revision,
        prediction=pending.record,
    )

    assert harness.observe(pending, transition) is False
    with pytest.raises(BacktestRequiredError, match="has a mismatch"):
        harness.require_green()


def test_backtest_ignores_terminal_grid_and_reinitializes_from_reality(
    tmp_path: Path,
) -> None:
    source = '''
def init_state(entry_grid):
    return {"value": entry_grid[0][0]}


def predict(state, grid, action, x=None, y=None):
    value = state["value"] + 1
    return (
        [[value]],
        {"level_up": state["value"] == 0, "dead": False, "win": False},
        {"value": value},
    )


def is_goal(state, grid):
    return False
'''.lstrip()
    harness = build_harness(tmp_path, [], source=source)
    harness.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(9, levels_completed=1),
        model_revision="setup",
        prediction=None,
    )
    harness.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(10, levels_completed=1),
        model_revision="setup",
        prediction=None,
    )

    report = harness.run_backtest()

    assert report.status == "green"
    assert report.exact_transitions == 2
    assert harness.require_green().state == {"value": 10}


def test_backtest_still_requires_exact_terminal_flags(tmp_path: Path) -> None:
    harness = build_harness(tmp_path, [])
    harness.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(9, levels_completed=1),
        model_revision="setup",
        prediction=None,
    )

    report = harness.run_backtest()

    assert report.status == "mismatch"
    assert report.mismatch is not None
    assert report.mismatch.differing_cells == 0
    assert report.mismatch.actual_flags.level_up is True
