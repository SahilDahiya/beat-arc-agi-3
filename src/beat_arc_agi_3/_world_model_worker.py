"""Isolated JSON worker for executing generated world-model code."""

import contextlib
import importlib.util
import io
import json
import sys
import traceback
from collections import deque
from pathlib import Path
from types import ModuleType
from typing import NoReturn


REQUIRED_INTERFACES = ("init_state", "predict", "is_goal")


class ContractFailure(RuntimeError):
    pass


def fail(kind: str, message: str) -> NoReturn:
    sys.__stdout__.write(
        json.dumps(
            {
                "ok": False,
                "error_kind": kind,
                "error": message,
            }
        )
    )
    raise SystemExit(1)


def load_model(model_path: Path) -> ModuleType:
    if not model_path.is_file():
        raise ContractFailure(f"world model does not exist: {model_path}")
    sys.path.insert(0, str(model_path.parent))
    spec = importlib.util.spec_from_file_location(
        "generated_world_model",
        model_path,
    )
    if spec is None or spec.loader is None:
        raise ContractFailure(f"could not load world model: {model_path}")
    module = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        spec.loader.exec_module(module)
    for name in REQUIRED_INTERFACES:
        if not callable(getattr(module, name, None)):
            raise ContractFailure(f"missing required callable: {name}")
    return module


def ensure_json(value: object) -> object:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ContractFailure("result is not JSON-serializable") from exc
    return value


def grid_shape(grid: object, *, label: str) -> tuple[int, ...]:
    if not isinstance(grid, (list, tuple)):
        raise ContractFailure(f"{label} must be a nested grid")
    shape = [len(grid)]
    for row in grid:
        if not isinstance(row, (list, tuple)):
            raise ContractFailure(f"{label} rows must be arrays")
        shape.append(len(row))
    return tuple(shape)


def validate_predicted_grid(predicted: object, current: object) -> None:
    predicted_shape = grid_shape(predicted, label="predicted grid")
    current_shape = grid_shape(current, label="current grid")
    if predicted_shape != current_shape:
        raise ContractFailure(
            f"predicted grid shape {predicted_shape} does not match "
            f"current grid shape {current_shape}"
        )
    assert isinstance(predicted, (list, tuple))
    for row in predicted:
        assert isinstance(row, (list, tuple))
        for value in row:
            if type(value) is not int or not 0 <= value <= 15:
                raise ContractFailure(
                    "predicted grid cells must be integer colors from 0 through 15"
                )


def predict(
    module: ModuleType,
    *,
    state: object,
    grid: object,
    action: dict[str, object],
) -> tuple[object, dict[str, object], object]:
    result = module.predict(
        state,
        grid,
        action["action"],
        action.get("x"),
        action.get("y"),
    )
    if not isinstance(result, (tuple, list)) or len(result) != 3:
        raise ContractFailure("predict must return (grid, flags, next_state)")
    next_grid, flags, next_state = result
    validate_predicted_grid(next_grid, grid)
    ensure_json(next_grid)
    ensure_json(flags)
    ensure_json(next_state)
    if not isinstance(flags, dict):
        raise ContractFailure("predict flags must be an object")
    required_flags = ("level_up", "dead", "win")
    if any(not isinstance(flags.get(name), bool) for name in required_flags):
        raise ContractFailure(
            "predict flags must contain boolean level_up, dead, and win"
        )
    return next_grid, flags, next_state


def state_key(state: object, grid: object) -> str:
    return json.dumps([state, grid], sort_keys=True, separators=(",", ":"))


def run_bfs(module: ModuleType, payload: dict[str, object]) -> dict[str, object]:
    state = payload["state"]
    grid = payload["grid"]
    actions = payload.get("actions")
    target = payload.get("target")
    max_depth = payload.get("max_depth")
    node_budget = payload.get("node_budget")
    if not isinstance(actions, list) or not actions:
        raise ContractFailure("bfs requires at least one action candidate")
    if target not in {"is_goal", "level_up", "win"}:
        raise ContractFailure(f"unsupported bfs target: {target}")
    if not isinstance(max_depth, int) or max_depth < 0:
        raise ContractFailure("max_depth must be a non-negative integer")
    if not isinstance(node_budget, int) or node_budget < 1:
        raise ContractFailure("node_budget must be a positive integer")

    if target == "is_goal":
        initial_goal = module.is_goal(state, grid)
        if not isinstance(initial_goal, bool):
            raise ContractFailure("is_goal must return bool")
        if initial_goal:
            return {
                "status": "found",
                "actions": [],
                "predicted_grid": grid,
                "expanded_nodes": 0,
                "distinct_states": 1,
                "depth": 0,
            }

    queue = deque([(state, grid, [])])
    visited = {state_key(state, grid)}
    expanded = 0
    while queue and expanded < node_budget:
        current_state, current_grid, plan = queue.popleft()
        if len(plan) >= max_depth:
            continue
        expanded += 1
        for action in actions:
            if not isinstance(action, dict) or "action" not in action:
                raise ContractFailure("invalid bfs action candidate")
            next_grid, flags, next_state = predict(
                module,
                state=current_state,
                grid=current_grid,
                action=action,
            )
            next_plan = [*plan, action]
            if target == "is_goal":
                reached = module.is_goal(next_state, next_grid)
                if not isinstance(reached, bool):
                    raise ContractFailure("is_goal must return bool")
            else:
                reached = bool(flags[target])
            key = state_key(next_state, next_grid)
            if reached:
                return {
                    "status": "found",
                    "actions": next_plan,
                    "predicted_grid": next_grid,
                    "expanded_nodes": expanded,
                    "distinct_states": len(visited | {key}),
                    "depth": len(next_plan),
                }
            if key not in visited:
                visited.add(key)
                queue.append((next_state, next_grid, next_plan))
    return {
        "status": "exhausted",
        "actions": [],
        "predicted_grid": None,
        "expanded_nodes": expanded,
        "distinct_states": len(visited),
        "depth": None,
    }


def execute(module: ModuleType, operation: str, payload: dict[str, object]) -> dict[str, object]:
    if operation == "inspect":
        return {"interfaces": list(REQUIRED_INTERFACES)}
    if operation == "init_state":
        state = module.init_state(payload["entry_grid"])
        return {"state": ensure_json(state)}
    if operation == "predict":
        grid, flags, state = predict(
            module,
            state=payload["state"],
            grid=payload["grid"],
            action={
                "action": payload["action"],
                "x": payload.get("x"),
                "y": payload.get("y"),
            },
        )
        return {
            "grid": grid,
            "flags": flags,
            "state": state,
        }
    if operation == "is_goal":
        result = module.is_goal(payload["state"], payload["grid"])
        if not isinstance(result, bool):
            raise ContractFailure("is_goal must return bool")
        return {"is_goal": result}
    if operation == "bfs":
        return run_bfs(module, payload)
    raise ContractFailure(f"unknown operation: {operation}")


def main() -> None:
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ContractFailure("request must be an object")
        payload = request.get("payload")
        if not isinstance(payload, dict):
            raise ContractFailure("payload must be an object")
        module = load_model(Path(str(request.get("model_path"))).resolve())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            result = execute(module, str(request.get("operation")), payload)
        sys.__stdout__.write(json.dumps({"ok": True, "result": result}))
    except ContractFailure as exc:
        fail("contract", str(exc))
    except BaseException as exc:
        fail(
            "execution",
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=5)}",
        )


if __name__ == "__main__":
    main()
