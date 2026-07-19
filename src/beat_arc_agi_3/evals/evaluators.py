from dataclasses import dataclass

from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
)

from beat_arc_agi_3.evals.models import (
    StageEvalInput,
    StageEvalMetadata,
    StageEvalOutcome,
)


@dataclass
class SessionEvidenceRegressionEvaluator(
    Evaluator[
        StageEvalInput,
        StageEvalOutcome,
        StageEvalMetadata,
    ]
):
    """Compare extracted Session evidence with declared immutable facts."""

    def evaluate(
        self,
        ctx: EvaluatorContext[
            StageEvalInput,
            StageEvalOutcome,
            StageEvalMetadata,
        ],
    ) -> dict[str, EvaluationReason]:
        if ctx.metadata is None:
            raise ValueError("Session evidence regression requires metadata")
        expected = ctx.metadata.expected
        return {
            f"matches.{field}": EvaluationReason(
                getattr(ctx.output, field) == value,
                (
                    f"expected {value!r}; observed "
                    f"{getattr(ctx.output, field)!r}"
                ),
            )
            for field, value in expected.model_dump().items()
        }


@dataclass
class StageOutcomeEvaluator(
    Evaluator[
        StageEvalInput,
        StageEvalOutcome,
        StageEvalMetadata,
    ]
):
    """Score observable stage progress without constraining the policy."""

    def evaluate(
        self,
        ctx: EvaluatorContext[
            StageEvalInput,
            StageEvalOutcome,
            StageEvalMetadata,
        ],
    ) -> dict[str, EvaluationReason]:
        target = ctx.inputs.target_levels_completed
        reached = ctx.output.target_reached
        return {
            "target_reached": EvaluationReason(
                reached,
                (
                    f"target {target} was reached; final observed level was "
                    f"{ctx.output.final_levels_completed}"
                    if reached
                    else (
                        f"no crossing to target {target}; final observed "
                        f"level was {ctx.output.final_levels_completed}"
                    )
                ),
            ),
            "stage_evidence_complete": EvaluationReason(
                ctx.output.stage_evidence_complete,
                "requires matching Timeline, action event, and model snapshot",
            ),
            "no_failure_before_target": EvaluationReason(
                not ctx.output.failure_before_target,
                "run failure or interruption must not precede target evidence",
            ),
        }
