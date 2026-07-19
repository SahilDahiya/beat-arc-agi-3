from pathlib import Path

from pydantic_evals import Case, Dataset
from pydantic_evals.reporting import EvaluationReport

from beat_arc_agi_3.evals.evaluators import StageOutcomeEvaluator
from beat_arc_agi_3.evals.models import (
    StageEvalInput,
    StageEvalMetadata,
    StageEvalOutcome,
)
from beat_arc_agi_3.evals.session_outcome import SessionStageTask


def build_session_stage_dataset(
    *,
    session_id: str,
    target_levels_completed: int,
) -> Dataset[StageEvalInput, StageEvalOutcome, StageEvalMetadata]:
    """Build one diagnostic stage eval over an arbitrary persisted Session."""

    return Dataset(
        name="session_stage_outcome_v1",
        cases=[
            Case(
                name=session_id,
                inputs=StageEvalInput(
                    session_id=session_id,
                    target_levels_completed=target_levels_completed,
                ),
            )
        ],
        evaluators=[StageOutcomeEvaluator()],
    )


async def run_session_stage_eval(
    *,
    sessions_root: Path,
    session_id: str,
    target_levels_completed: int,
) -> EvaluationReport[StageEvalInput, StageEvalOutcome, StageEvalMetadata]:
    """Score one existing Session without model or ARC calls."""

    dataset = build_session_stage_dataset(
        session_id=session_id,
        target_levels_completed=target_levels_completed,
    )
    return await dataset.evaluate(
        SessionStageTask(sessions_root),
        name=dataset.name,
        max_concurrency=1,
        progress=False,
    )


def report_passed(
    report: EvaluationReport[
        StageEvalInput,
        StageEvalOutcome,
        StageEvalMetadata,
    ],
) -> bool:
    """Return true only when every case ran and every assertion passed."""

    return (
        not report.failures
        and bool(report.cases)
        and all(
            result.value is True
            for case in report.cases
            for result in case.assertions.values()
        )
    )
