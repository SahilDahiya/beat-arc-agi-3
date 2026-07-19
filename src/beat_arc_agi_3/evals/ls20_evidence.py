from collections.abc import Sequence
from pathlib import Path

from pydantic_evals import Case, Dataset
from pydantic_evals.reporting import EvaluationReport

from beat_arc_agi_3.evals.evaluators import (
    SessionEvidenceRegressionEvaluator,
)
from beat_arc_agi_3.evals.models import (
    StageEvalInput,
    StageEvalMetadata,
    StageEvalOutcome,
    StageEvidenceExpectation,
)
from beat_arc_agi_3.evals.session_outcome import SessionStageTask


LS20_SESSION_EVIDENCE_EVAL_NAME = "ls20_session_evidence_regression_v1"
LS20_SUCCESS_SESSIONS = (
    "20260719T070540.523307Z-ls20-world-model-001",
    "20260719T165557.195241Z-ls20-world-model-001",
)

_LS20_SUCCESS_EXPECTATIONS = (
    StageEvidenceExpectation(
        target_reached=True,
        initial_levels_completed=0,
        final_levels_completed=1,
        target_transition_index=24,
        actions_to_target=25,
        turns_to_target=11,
        prediction_exact=16,
        prediction_mismatch=9,
        prediction_unchecked=0,
        tool_counts={
            "edit_file": 54,
            "read_file": 1,
            "read_history": 13,
            "run_backtest": 24,
            "run_python": 10,
            "write_file": 4,
        },
        target_action_event_found=True,
        target_snapshot_found=True,
        target_snapshot_path="snapshots/cleared_level_0.py",
        failure_before_target=False,
        post_target_run_failure=None,
    ),
    StageEvidenceExpectation(
        target_reached=True,
        initial_levels_completed=0,
        final_levels_completed=1,
        target_transition_index=24,
        actions_to_target=25,
        turns_to_target=11,
        prediction_exact=17,
        prediction_mismatch=8,
        prediction_unchecked=0,
        tool_counts={
            "edit_file": 9,
            "read_file": 9,
            "read_history": 11,
            "run_backtest": 14,
            "run_python": 2,
            "write_file": 15,
        },
        target_action_event_found=True,
        target_snapshot_found=True,
        target_snapshot_path="snapshots/cleared_level_0.py",
        failure_before_target=False,
        post_target_run_failure="UnexpectedModelBehavior",
    ),
)


def build_ls20_session_evidence_dataset(
    *,
    session_ids: Sequence[str] = LS20_SUCCESS_SESSIONS,
    expectations: Sequence[
        StageEvidenceExpectation
    ] = _LS20_SUCCESS_EXPECTATIONS,
) -> Dataset[StageEvalInput, StageEvalOutcome, StageEvalMetadata]:
    """Build the immutable regression over known LS20 Session evidence."""

    if len(session_ids) != len(expectations):
        raise ValueError("session_ids and expectations must have equal length")
    cases = [
        Case(
            name=f"ls20-session-evidence-{index}",
            inputs=StageEvalInput(
                session_id=session_id,
                target_levels_completed=1,
            ),
            metadata=StageEvalMetadata(
                provenance="historical_success",
                expected=expectation,
            ),
        )
        for index, (session_id, expectation) in enumerate(
            zip(session_ids, expectations, strict=True),
            start=1,
        )
    ]
    return Dataset(
        name=LS20_SESSION_EVIDENCE_EVAL_NAME,
        cases=cases,
        evaluators=[SessionEvidenceRegressionEvaluator()],
    )


async def run_ls20_session_evidence_regression(
    sessions_root: Path,
) -> EvaluationReport[StageEvalInput, StageEvalOutcome, StageEvalMetadata]:
    """Validate both known successful Sessions without external calls."""

    dataset = build_ls20_session_evidence_dataset()
    return await dataset.evaluate(
        SessionStageTask(sessions_root),
        name=dataset.name,
        max_concurrency=1,
        progress=False,
    )
