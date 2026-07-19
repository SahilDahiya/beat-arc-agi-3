from pathlib import Path

import pytest

from beat_arc_agi_3.schemas import ArcAction
from beat_arc_agi_3.world_model import (
    WorldModelContractError,
    WorldModelRuntime,
)


VALID_MODEL = '''
def init_state(entry_grid):
    return {"steps": 0}


def predict(state, grid, action, x=None, y=None):
    next_grid = [row[:] for row in grid]
    next_grid[0][0] = state["steps"] + 1
    return (
        next_grid,
        {"level_up": False, "dead": False, "win": False},
        {"steps": state["steps"] + 1},
    )


def is_goal(state, grid):
    return state["steps"] >= 2
'''.lstrip()


def write_model(tmp_path: Path, source: str = VALID_MODEL) -> Path:
    path = tmp_path / "world_model_v5.py"
    path.write_text(source, encoding="utf-8")
    return path


def test_runtime_validates_the_canonical_stateful_interface(
    tmp_path: Path,
) -> None:
    runtime = WorldModelRuntime(write_model(tmp_path))

    info = runtime.inspect()

    assert info.revision == runtime.revision
    assert info.interfaces == ("init_state", "predict", "is_goal")


def test_runtime_rejects_a_model_missing_required_interfaces(
    tmp_path: Path,
) -> None:
    runtime = WorldModelRuntime(
        write_model(tmp_path, "def predict(state, grid, action):\n    pass\n")
    )

    with pytest.raises(
        WorldModelContractError,
        match="missing required callable: init_state",
    ):
        runtime.inspect()


def test_runtime_initializes_predicts_and_checks_the_goal(
    tmp_path: Path,
) -> None:
    runtime = WorldModelRuntime(write_model(tmp_path))
    grid = ((0, 0), (0, 0))

    state = runtime.init_state(grid)
    first = runtime.predict(
        state=state,
        grid=grid,
        action=ArcAction(action="ACTION1"),
    )
    second = runtime.predict(
        state=first.state,
        grid=first.grid,
        action=ArcAction(action="ACTION2"),
    )

    assert state == {"steps": 0}
    assert first.grid == ((1, 0), (0, 0))
    assert first.flags.model_dump() == {
        "level_up": False,
        "dead": False,
        "win": False,
    }
    assert first.state == {"steps": 1}
    assert runtime.is_goal(state=first.state, grid=first.grid) is False
    assert runtime.is_goal(state=second.state, grid=second.grid) is True


def test_runtime_rejects_non_json_model_state(tmp_path: Path) -> None:
    source = VALID_MODEL.replace(
        'return {"steps": 0}',
        "return {1, 2, 3}",
    )
    runtime = WorldModelRuntime(write_model(tmp_path, source))

    with pytest.raises(
        WorldModelContractError,
        match="result is not JSON-serializable",
    ):
        runtime.init_state(((0,),))


def test_runtime_rejects_a_prediction_with_a_different_grid_shape(
    tmp_path: Path,
) -> None:
    source = VALID_MODEL.replace(
        "next_grid = [row[:] for row in grid]",
        "next_grid = [[0]]",
    )
    runtime = WorldModelRuntime(write_model(tmp_path, source))

    with pytest.raises(
        WorldModelContractError,
        match="predicted grid shape",
    ):
        runtime.predict(
            state={"steps": 0},
            grid=((0, 0), (0, 0)),
            action=ArcAction(action="ACTION1"),
        )


def test_runtime_rejects_non_integer_predicted_colors(tmp_path: Path) -> None:
    source = VALID_MODEL.replace(
        "next_grid[0][0] = state[\"steps\"] + 1",
        'next_grid[0][0] = "1"',
    )
    runtime = WorldModelRuntime(write_model(tmp_path, source))

    with pytest.raises(
        WorldModelContractError,
        match="integer color",
    ):
        runtime.predict(
            state={"steps": 0},
            grid=((0, 0), (0, 0)),
            action=ArcAction(action="ACTION1"),
        )
