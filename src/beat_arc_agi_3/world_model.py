import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from beat_arc_agi_3.sandbox import (
    SandboxUnavailableError,
    isolated_python_command,
)
from beat_arc_agi_3.schemas import ArcAction, Grid


WORLD_MODEL_FILENAME = "world_model_v5.py"
WORLD_MODEL_INTERFACES = ("init_state", "predict", "is_goal")


class WorldModelError(RuntimeError):
    """Base error for the generated world-model boundary."""


class WorldModelContractError(WorldModelError):
    """Raised when generated code violates the canonical model contract."""


class WorldModelExecutionError(WorldModelError):
    """Raised when isolated model execution fails or times out."""


class WorldModelInfo(BaseModel):
    """Identity and installed interfaces for one generated model revision."""

    model_config = ConfigDict(frozen=True)

    revision: str
    interfaces: tuple[Literal["init_state", "predict", "is_goal"], ...]


class PredictedFlags(BaseModel):
    """Terminal signals predicted for one modeled transition."""

    model_config = ConfigDict(frozen=True)

    level_up: bool
    dead: bool
    win: bool


class WorldModelPrediction(BaseModel):
    """One canonical result returned by generated transition code."""

    model_config = ConfigDict(frozen=True)

    grid: Grid
    flags: PredictedFlags
    state: JsonValue


class WorldModelRuntime:
    """Execute one generated model behind a subprocess JSON boundary."""

    def __init__(self, path: str | Path, *, timeout_seconds: float = 10) -> None:
        self.path = Path(path).resolve()
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds

    @property
    def revision(self) -> str:
        try:
            source = self.path.read_bytes()
        except OSError as exc:
            raise WorldModelContractError(
                f"world model is not readable: {self.path}"
            ) from exc
        return hashlib.sha256(source).hexdigest()

    def inspect(self) -> WorldModelInfo:
        response = self._request("inspect", {})
        return WorldModelInfo(
            revision=self.revision,
            interfaces=tuple(response["interfaces"]),
        )

    def init_state(self, entry_grid: Grid) -> JsonValue:
        response = self._request(
            "init_state",
            {"entry_grid": entry_grid},
        )
        return response["state"]

    def predict(
        self,
        *,
        state: JsonValue,
        grid: Grid,
        action: ArcAction,
    ) -> WorldModelPrediction:
        response = self._request(
            "predict",
            {
                "state": state,
                "grid": grid,
                "action": action.action,
                "x": action.x,
                "y": action.y,
            },
        )
        try:
            return WorldModelPrediction.model_validate(response)
        except ValidationError as exc:
            raise WorldModelContractError(
                f"predict returned an invalid result: {exc}"
            ) from exc

    def is_goal(self, *, state: JsonValue, grid: Grid) -> bool:
        response = self._request(
            "is_goal",
            {"state": state, "grid": grid},
        )
        result = response.get("is_goal")
        if not isinstance(result, bool):
            raise WorldModelContractError("is_goal must return bool")
        return result

    def search(
        self,
        *,
        state: JsonValue,
        grid: Grid,
        actions: tuple[ArcAction, ...],
        target: Literal["is_goal", "level_up", "win"],
        max_depth: int,
        node_budget: int,
        timeout_seconds: int,
    ) -> dict[str, object]:
        return self._request(
            "bfs",
            {
                "state": state,
                "grid": grid,
                "actions": [
                    action.model_dump(mode="json", exclude_none=True)
                    for action in actions
                ],
                "target": target,
                "max_depth": max_depth,
                "node_budget": node_budget,
            },
            timeout_seconds=timeout_seconds,
        )

    def _request(
        self,
        operation: str,
        payload: dict[str, object],
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, object]:
        worker = Path(__file__).with_name("_world_model_worker.py")
        request = {
            "operation": operation,
            "model_path": f"/workspace/{self.path.name}",
            "payload": payload,
        }
        try:
            command = isolated_python_command(
                workspace_root=self.path.parent,
                python_arguments=[str(worker)],
                read_only_paths=(worker.parent,),
            )
        except SandboxUnavailableError as exc:
            raise WorldModelExecutionError(str(exc)) from exc
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(request),
                text=True,
                capture_output=True,
                timeout=(
                    self.timeout_seconds
                    if timeout_seconds is None
                    else timeout_seconds
                ),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WorldModelExecutionError(
                "world model timed out after "
                f"{self.timeout_seconds if timeout_seconds is None else timeout_seconds:g}s"
            ) from exc

        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            diagnostic = completed.stderr.strip() or completed.stdout.strip()
            raise WorldModelExecutionError(
                "world-model worker returned invalid output"
                + (f": {diagnostic}" if diagnostic else "")
            ) from exc
        if not isinstance(response, dict):
            raise WorldModelExecutionError(
                "world-model worker response must be an object"
            )
        if response.get("ok") is not True:
            message = str(response.get("error", "unknown world-model error"))
            if response.get("error_kind") == "contract":
                raise WorldModelContractError(message)
            raise WorldModelExecutionError(message)
        result = response.get("result")
        if not isinstance(result, dict):
            raise WorldModelExecutionError(
                "world-model worker result must be an object"
            )
        return result


def inspect_world_model_source(
    source: str,
    *,
    workspace_root: Path,
) -> WorldModelInfo:
    """Validate prospective live-model source before durable replacement."""

    descriptor, temporary_name = tempfile.mkstemp(
        dir=workspace_root,
        prefix=".world_model_v5.validation-",
        suffix=".py",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(source)
        return WorldModelRuntime(temporary_path).inspect()
    finally:
        temporary_path.unlink(missing_ok=True)
