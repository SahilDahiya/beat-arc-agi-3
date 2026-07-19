from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from beat_arc_agi_3.schemas import ArcAction, Grid
from beat_arc_agi_3.timeline import (
    JsonlTimeline,
    ModelPredictionRecord,
    Transition,
)
from beat_arc_agi_3.world_model import (
    PredictedFlags,
    WorldModelPrediction,
    WorldModelRuntime,
)


class BacktestRequiredError(RuntimeError):
    """Raised when an action or search requires a current green backtest."""


class GridDifference(BaseModel):
    """One exact cell disagreement between a model and real evidence."""

    model_config = ConfigDict(frozen=True)

    row: int = Field(ge=0)
    column: int = Field(ge=0)
    predicted: int | None
    actual: int | None


class BacktestMismatch(BaseModel):
    """The earliest recorded transition rejected by a candidate model."""

    model_config = ConfigDict(frozen=True)

    transition_index: int = Field(ge=0)
    action: ArcAction
    differing_cells: int = Field(ge=0)
    differences: tuple[GridDifference, ...]
    predicted_flags: PredictedFlags
    actual_flags: PredictedFlags


class BacktestReport(BaseModel):
    """Finite replay result for one model revision and Timeline prefix."""

    model_config = ConfigDict(frozen=True)

    revision: str
    timeline_transitions: int = Field(ge=0)
    transitions_checked: int = Field(ge=0)
    exact_transitions: int = Field(ge=0)
    status: Literal["green", "mismatch"]
    mismatch: BacktestMismatch | None = None


class BfsReport(BaseModel):
    """Bounded search result from one exact green world-model revision."""

    model_config = ConfigDict(frozen=True)

    revision: str
    target: Literal["is_goal", "level_up", "win"]
    status: Literal["found", "exhausted"]
    actions: tuple[ArcAction, ...]
    predicted_grid: Grid | None
    expanded_nodes: int = Field(ge=0)
    distinct_states: int = Field(ge=1)
    depth: int | None = Field(default=None, ge=0)


@dataclass(frozen=True)
class BacktestTrust:
    """Internal current-state proof produced by an exact finite replay."""

    revision: str
    timeline_transitions: int
    state: JsonValue
    grid: Grid


@dataclass(frozen=True)
class PendingModelPrediction:
    """A model result produced immediately before one real action."""

    revision: str
    timeline_transitions: int
    action: ArcAction
    prediction: WorldModelPrediction

    @property
    def record(self) -> ModelPredictionRecord:
        return ModelPredictionRecord(
            grid=self.prediction.grid,
            level_up=self.prediction.flags.level_up,
            dead=self.prediction.flags.dead,
            win=self.prediction.flags.win,
        )


class SynthesisHarness:
    """Bind generated model revisions to exact real-transition evidence."""

    def __init__(
        self,
        *,
        model_path: str | Path,
        timeline: JsonlTimeline,
    ) -> None:
        self.model_path = Path(model_path).resolve()
        self.timeline = timeline
        self._last_report: BacktestReport | None = None
        self._trust: BacktestTrust | None = None

    @property
    def runtime(self) -> WorldModelRuntime:
        return WorldModelRuntime(self.model_path)

    def model_revision(self) -> str:
        """Return the exact revision of the installed generated program."""

        return self.runtime.revision

    def inspect_model(self) -> str:
        """Require an installed interface-valid model and return its revision."""

        return self.runtime.inspect().revision

    def run_backtest(self, *, max_details: int = 1) -> BacktestReport:
        if max_details < 0 or max_details > 100:
            raise ValueError("max_details must be between 0 and 100")
        initial = self.timeline.initial_observation
        if initial is None:
            raise BacktestRequiredError(
                "Timeline requires an initial observation before backtesting"
            )

        runtime = self.runtime
        runtime.inspect()
        revision = runtime.revision
        transitions = self.timeline.transitions()
        state = runtime.init_state(initial.grid)
        current_grid = initial.grid

        for checked, transition in enumerate(transitions, start=1):
            prediction = runtime.predict(
                state=state,
                grid=transition.before.grid,
                action=transition.action,
            )
            mismatch = self._compare(
                transition,
                prediction,
                max_details=max_details,
            )
            if mismatch is not None:
                report = BacktestReport(
                    revision=revision,
                    timeline_transitions=len(transitions),
                    transitions_checked=checked,
                    exact_transitions=checked - 1,
                    status="mismatch",
                    mismatch=mismatch,
                )
                self._last_report = report
                self._trust = None
                return report
            if transition.level_up or transition.dead or transition.win:
                state = runtime.init_state(transition.after.grid)
                current_grid = transition.after.grid
            else:
                state = prediction.state
                current_grid = prediction.grid

        current_observation = transitions[-1].after if transitions else initial
        for action in self._smoke_actions(current_observation.available_action_names):
            runtime.predict(
                state=state,
                grid=current_grid,
                action=action,
            )

        report = BacktestReport(
            revision=revision,
            timeline_transitions=len(transitions),
            transitions_checked=len(transitions),
            exact_transitions=len(transitions),
            status="green",
        )
        self._last_report = report
        self._trust = BacktestTrust(
            revision=revision,
            timeline_transitions=len(transitions),
            state=state,
            grid=current_grid,
        )
        return report

    def require_green(self) -> BacktestTrust:
        current_revision = self.runtime.revision
        transition_count = len(self.timeline.transitions())
        report = self._last_report
        if report is None or report.revision != current_revision:
            raise BacktestRequiredError(
                "current world model revision has not been backtested"
            )
        if report.timeline_transitions != transition_count:
            raise BacktestRequiredError(
                "current Timeline has not been backtested"
            )
        if report.status != "green" or self._trust is None:
            raise BacktestRequiredError(
                "current world model has a mismatch in recorded history"
            )
        return self._trust

    def predict_action(self, action: ArcAction) -> PendingModelPrediction:
        trust = self.require_green()
        prediction = self.runtime.predict(
            state=trust.state,
            grid=trust.grid,
            action=action,
        )
        return PendingModelPrediction(
            revision=trust.revision,
            timeline_transitions=trust.timeline_transitions,
            action=action,
            prediction=prediction,
        )

    def preflight_actions(self, actions: tuple[ArcAction, ...]) -> None:
        trust = self.require_green()
        state = trust.state
        grid = trust.grid
        for action in actions:
            prediction = self.runtime.predict(
                state=state,
                grid=grid,
                action=action,
            )
            state = prediction.state
            grid = prediction.grid

    def run_bfs(
        self,
        *,
        target: Literal["is_goal", "level_up", "win"],
        max_depth: int,
        node_budget: int,
        click_candidates: tuple[tuple[int, int], ...],
        timeout_seconds: int,
    ) -> BfsReport:
        if max_depth < 0 or max_depth > 200:
            raise ValueError("max_depth must be between 0 and 200")
        if node_budget < 1 or node_budget > 4_000_000:
            raise ValueError("node_budget must be between 1 and 4000000")
        if timeout_seconds < 1 or timeout_seconds > 600:
            raise ValueError("timeout_seconds must be between 1 and 600")

        trust = self.require_green()
        initial = self.timeline.initial_observation
        assert initial is not None
        transitions = self.timeline.transitions()
        observation = transitions[-1].after if transitions else initial
        candidates: list[ArcAction] = []
        for action_name in observation.available_action_names:
            if action_name == "ACTION6":
                candidates.extend(
                    ArcAction(action="ACTION6", x=x, y=y)
                    for x, y in click_candidates
                )
            else:
                candidates.append(ArcAction(action=action_name))
        if not candidates:
            raise ValueError("BFS has no action candidates")

        result = self.runtime.search(
            state=trust.state,
            grid=trust.grid,
            actions=tuple(candidates),
            target=target,
            max_depth=max_depth,
            node_budget=node_budget,
            timeout_seconds=timeout_seconds,
        )
        return BfsReport.model_validate(
            {
                **result,
                "revision": trust.revision,
                "target": target,
            }
        )

    def observe(
        self,
        pending: PendingModelPrediction,
        transition: Transition,
    ) -> bool:
        if transition.index != pending.timeline_transitions:
            raise RuntimeError(
                "observed transition does not continue the predicted Timeline"
            )
        if transition.action != pending.action:
            raise RuntimeError("observed action differs from predicted action")
        if transition.prediction != pending.record:
            raise RuntimeError("Timeline prediction differs from pending prediction")

        transition_count = len(self.timeline.transitions())
        mismatch = self._compare(
            transition,
            pending.prediction,
            max_details=20,
        )
        if mismatch is not None:
            self._last_report = BacktestReport(
                revision=pending.revision,
                timeline_transitions=transition_count,
                transitions_checked=transition_count,
                exact_transitions=transition_count - 1,
                status="mismatch",
                mismatch=mismatch,
            )
            self._trust = None
            return False

        self._last_report = BacktestReport(
            revision=pending.revision,
            timeline_transitions=transition_count,
            transitions_checked=transition_count,
            exact_transitions=transition_count,
            status="green",
        )
        self._trust = BacktestTrust(
            revision=pending.revision,
            timeline_transitions=transition_count,
            state=(
                self.runtime.init_state(transition.after.grid)
                if transition.level_up or transition.dead or transition.win
                else pending.prediction.state
            ),
            grid=(
                transition.after.grid
                if transition.level_up or transition.dead or transition.win
                else pending.prediction.grid
            ),
        )
        return True

    @staticmethod
    def _compare(
        transition: Transition,
        prediction: WorldModelPrediction,
        *,
        max_details: int,
    ) -> BacktestMismatch | None:
        actual_flags = PredictedFlags(
            level_up=transition.level_up,
            dead=transition.dead,
            win=transition.win,
        )
        terminal = transition.level_up or transition.dead or transition.win
        differences = (
            []
            if terminal
            else SynthesisHarness._grid_differences(
                predicted=prediction.grid,
                actual=transition.after.grid,
            )
        )
        if not differences and prediction.flags == actual_flags:
            return None
        return BacktestMismatch(
            transition_index=transition.index,
            action=transition.action,
            differing_cells=len(differences),
            differences=tuple(differences[:max_details]),
            predicted_flags=prediction.flags,
            actual_flags=actual_flags,
        )

    @staticmethod
    def _grid_differences(
        *,
        predicted: Grid,
        actual: Grid,
    ) -> list[GridDifference]:
        differences: list[GridDifference] = []
        height = max(len(predicted), len(actual))
        for row in range(height):
            predicted_row = predicted[row] if row < len(predicted) else ()
            actual_row = actual[row] if row < len(actual) else ()
            width = max(len(predicted_row), len(actual_row))
            for column in range(width):
                predicted_value = (
                    predicted_row[column]
                    if column < len(predicted_row)
                    else None
                )
                actual_value = (
                    actual_row[column] if column < len(actual_row) else None
                )
                if predicted_value != actual_value:
                    differences.append(
                        GridDifference(
                            row=row,
                            column=column,
                            predicted=predicted_value,
                            actual=actual_value,
                        )
                    )
        return differences

    @staticmethod
    def _smoke_actions(action_names: tuple[str, ...]) -> tuple[ArcAction, ...]:
        return tuple(
            ArcAction(action=name, x=0, y=0)
            if name == "ACTION6"
            else ArcAction(action=name)
            for name in action_names
        )
