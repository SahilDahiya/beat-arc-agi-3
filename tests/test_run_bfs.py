from pathlib import Path

import pytest
from arcengine import FrameData, GameState

from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.synthesis import BacktestRequiredError, SynthesisHarness
from beat_arc_agi_3.timeline import JsonlTimeline
from beat_arc_agi_3.world_model import WorldModelContractError


MODEL = '''
def init_state(entry_grid):
    return {"value": entry_grid[0][0]}


def predict(state, grid, action, x=None, y=None):
    value = state["value"] + (1 if action == "ACTION1" else 0)
    return (
        [[value]],
        {"level_up": value >= 2, "dead": False, "win": value >= 3},
        {"value": value},
    )


def is_goal(state, grid):
    return state["value"] >= 2
'''.lstrip()


def harness(
    tmp_path: Path,
    *,
    backtest: bool = True,
    source: str = MODEL,
) -> SynthesisHarness:
    (tmp_path / "world_model_v5.py").write_text(source, encoding="utf-8")
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(
        GameObservation.from_frame(
            FrameData(
                game_id="test-game",
                frame=[[[0]]],
                state=GameState.NOT_FINISHED,
                available_actions=[1],
            )
        )
    )
    result = SynthesisHarness(
        model_path=tmp_path / "world_model_v5.py",
        timeline=timeline,
    )
    if backtest:
        result.run_backtest()
    return result


def test_bfs_finds_a_goal_plan_in_the_green_model(tmp_path: Path) -> None:
    report = harness(tmp_path).run_bfs(
        target="is_goal",
        max_depth=4,
        node_budget=100,
        click_candidates=(),
        timeout_seconds=10,
    )

    assert report.status == "found"
    assert report.target == "is_goal"
    assert [action.action for action in report.actions] == [
        "ACTION1",
        "ACTION1",
    ]
    assert report.depth == 2
    assert report.predicted_grid == ((2,),)
    assert report.revision


def test_bfs_reports_bounded_exhaustion(tmp_path: Path) -> None:
    report = harness(tmp_path).run_bfs(
        target="win",
        max_depth=2,
        node_budget=100,
        click_candidates=(),
        timeout_seconds=10,
    )

    assert report.status == "exhausted"
    assert report.actions == ()
    assert report.depth is None


def test_bfs_requires_a_green_current_revision(tmp_path: Path) -> None:
    with pytest.raises(
        BacktestRequiredError,
        match="has not been backtested",
    ):
        harness(tmp_path, backtest=False).run_bfs(
            target="is_goal",
            max_depth=4,
            node_budget=100,
            click_candidates=(),
            timeout_seconds=10,
        )


def test_bfs_validates_every_modeled_transition_grid(tmp_path: Path) -> None:
    malformed_after_smoke = MODEL.replace(
        "value = state[\"value\"] + (1 if action == \"ACTION1\" else 0)",
        (
            "value = state[\"value\"] + "
            "(1 if action == \"ACTION1\" else 0)\n"
            "    if value >= 2:\n"
            "        return ([value], "
            '{"level_up": True, "dead": False, "win": False}, '
            '{"value": value})'
        ),
    )
    model_harness = harness(tmp_path, source=malformed_after_smoke)

    with pytest.raises(
        WorldModelContractError,
        match="predicted grid",
    ):
        model_harness.run_bfs(
            target="is_goal",
            max_depth=4,
            node_budget=100,
            click_candidates=(),
            timeout_seconds=10,
        )
