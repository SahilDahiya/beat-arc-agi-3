import asyncio
import hashlib
from pathlib import Path

import pytest
from arcengine import GameState
from pydantic_evals import Case, Dataset

from beat_arc_agi_3.evals.evaluators import (
    SessionEvidenceRegressionEvaluator,
    StageOutcomeEvaluator,
)
from beat_arc_agi_3.evals.ls20_evidence import (
    LS20_SESSION_EVIDENCE_EVAL_NAME,
    LS20_SUCCESS_SESSIONS,
    build_ls20_session_evidence_dataset,
)
from beat_arc_agi_3.evals.models import (
    StageEvalInput,
    StageEvalMetadata,
    StageEvidenceExpectation,
)
from beat_arc_agi_3.evals.session_outcome import (
    SessionStageTask,
    extract_stage_outcome,
)
from beat_arc_agi_3.evals.session_stage import (
    build_session_stage_dataset,
    report_passed,
)
from beat_arc_agi_3.events import (
    ActionCompletedEvent,
    RunFailedEvent,
    RunInterruptedEvent,
    ToolCompletedEvent,
    WorldModelSnapshottedEvent,
)
from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.session import Session, SessionCorruptionError
from beat_arc_agi_3.timeline import ModelPredictionRecord


def observation(levels_completed: int, value: int) -> GameObservation:
    return GameObservation(
        game_id="ls20-test",
        grid=((value,),),
        state=GameState.NOT_FINISHED,
        levels_completed=levels_completed,
        win_levels=7,
        available_actions=(1,),
    )


def create_session(
    root: Path,
    *,
    session_id: str,
    reaches_target: bool = True,
    include_target_action: bool = True,
    include_snapshot: bool = True,
    failure_before_target: str | None = None,
    failure_after_target: bool = False,
) -> Session:
    session = Session.create(
        sessions_root=root,
        session_id=session_id,
        game_id="ls20-test",
        model="openai-codex:gpt-5.5",
    )
    source = b"def init_state(entry_grid):\n    return {}\n"
    session.synthesis.model_path.write_bytes(source)
    revision = hashlib.sha256(source).hexdigest()
    action = ArcAction(action="ACTION1")
    session.timeline.initialize(observation(0, 0))
    first = session.timeline.append(
        action=action,
        after=observation(0, 1),
        model_revision=revision,
        prediction=ModelPredictionRecord(
            grid=((1,),), level_up=False, dead=False, win=False
        ),
    )
    session.events.append(
        turn=1,
        event=ToolCompletedEvent(
            summary="Read history",
            tool_call_id="history-1",
            tool_name="read_history",
            duration_ms=2,
        ),
    )
    session.events.append(
        turn=1,
        event=ActionCompletedEvent(
            summary="Completed first action",
            action_number=1,
            transition_index=first.index,
            action=action,
            model_revision=revision,
            prediction_status=first.prediction_status,
            state=first.after.state,
            levels_completed=first.after.levels_completed,
            level_up=first.level_up,
            dead=first.dead,
            win=first.win,
        ),
    )
    second = session.timeline.append(
        action=action,
        after=observation(1 if reaches_target else 0, 2),
        model_revision=revision,
        prediction=ModelPredictionRecord(
            grid=((1,),), level_up=False, dead=False, win=False
        ),
    )
    if failure_before_target == "failed":
        session.events.append(
            turn=2,
            event=RunFailedEvent(
                summary="Model protocol failed",
                error_type="UnexpectedModelBehavior",
                message="No structured output",
            ),
        )
    elif failure_before_target == "interrupted":
        session.events.append(
            turn=2,
            event=RunInterruptedEvent(
                summary="Operator interrupted run",
                error_type="KeyboardInterrupt",
                message="Interrupted",
            ),
        )
    if include_target_action:
        session.events.append(
            turn=2,
            event=ActionCompletedEvent(
                summary="Completed second action",
                action_number=2,
                transition_index=second.index,
                action=action,
                model_revision=revision,
                prediction_status=second.prediction_status,
                state=second.after.state,
                levels_completed=second.after.levels_completed,
                level_up=second.level_up,
                dead=second.dead,
                win=second.win,
            ),
        )
    if reaches_target and include_snapshot:
        snapshot = session.snapshot_world_model(
            cleared_level=0,
            revision=revision,
        )
        session.events.append(
            turn=2,
            event=WorldModelSnapshottedEvent(
                summary="Saved successful model",
                cleared_level=0,
                revision=revision,
                prediction_status=second.prediction_status,
                path=snapshot.relative_to(session.path).as_posix(),
            ),
        )
    if failure_after_target:
        session.events.append(
            turn=3,
            event=RunFailedEvent(
                summary="Later stage failed",
                error_type="LaterFailure",
                message="Failure after the evaluated stage",
            ),
        )
    return session


def expectation_from(session: Session) -> StageEvidenceExpectation:
    outcome = extract_stage_outcome(session, target_levels_completed=1)
    return StageEvidenceExpectation.model_validate(
        outcome.model_dump(
            exclude={
                "session_id",
                "game_id",
                "model",
                "target_levels_completed",
                "duration_to_target_seconds",
            }
        )
    )


def test_extract_stage_outcome_is_scoped_to_first_target_level(
    tmp_path: Path,
) -> None:
    session = create_session(
        tmp_path,
        session_id="successful-stage-0",
        failure_after_target=True,
    )

    outcome = extract_stage_outcome(session, target_levels_completed=1)

    assert outcome.target_reached is True
    assert outcome.initial_levels_completed == 0
    assert outcome.final_levels_completed == 1
    assert outcome.target_transition_index == 1
    assert outcome.actions_to_target == 2
    assert outcome.turns_to_target == 2
    assert outcome.prediction_exact == 1
    assert outcome.prediction_mismatch == 1
    assert outcome.prediction_unchecked == 0
    assert outcome.tool_counts == {"read_history": 1}
    assert outcome.target_action_event_found is True
    assert outcome.target_snapshot_found is True
    assert outcome.failure_before_target is False
    assert outcome.post_target_run_failure == "LaterFailure"


def test_extract_stage_outcome_reports_target_not_reached(tmp_path: Path) -> None:
    session = create_session(
        tmp_path,
        session_id="target-not-reached",
        reaches_target=False,
        include_snapshot=False,
    )

    outcome = extract_stage_outcome(session, target_levels_completed=1)

    assert outcome.target_reached is False
    assert outcome.final_levels_completed == 0
    assert outcome.actions_to_target is None
    assert outcome.turns_to_target is None
    assert outcome.target_action_event_found is False
    assert outcome.target_snapshot_found is False


def test_extract_stage_outcome_detects_missing_target_action(tmp_path: Path) -> None:
    session = create_session(
        tmp_path,
        session_id="missing-target-action",
        include_target_action=False,
    )

    outcome = extract_stage_outcome(session, target_levels_completed=1)

    assert outcome.target_reached is True
    assert outcome.target_action_event_found is False
    assert outcome.target_snapshot_found is True
    assert outcome.stage_evidence_complete is False


def test_session_task_rejects_missing_snapshot_artifact(tmp_path: Path) -> None:
    session = create_session(
        tmp_path,
        session_id="missing-snapshot",
        include_snapshot=False,
    )

    with pytest.raises(SessionCorruptionError, match="snapshot evidence"):
        SessionStageTask(tmp_path)(
            StageEvalInput(
                session_id=session.metadata.session_id,
                target_levels_completed=1,
            )
        )


def test_session_task_rejects_corrupt_snapshot_artifact(tmp_path: Path) -> None:
    session = create_session(tmp_path, session_id="corrupt-snapshot")
    (session.path / "snapshots" / "cleared_level_0.py").write_text(
        "corrupt",
        encoding="utf-8",
    )

    with pytest.raises(SessionCorruptionError, match="revision mismatch"):
        SessionStageTask(tmp_path)(
            StageEvalInput(
                session_id=session.metadata.session_id,
                target_levels_completed=1,
            )
        )


@pytest.mark.parametrize("failure_kind", ["failed", "interrupted"])
def test_extract_stage_outcome_detects_failure_before_target(
    tmp_path: Path,
    failure_kind: str,
) -> None:
    session = create_session(
        tmp_path,
        session_id=f"failure-before-target-{failure_kind}",
        failure_before_target=failure_kind,
    )

    outcome = extract_stage_outcome(session, target_levels_completed=1)

    assert outcome.target_reached is True
    assert outcome.failure_before_target is True


def test_stage_outcome_eval_reports_assertions_and_metrics(
    tmp_path: Path,
) -> None:
    session = create_session(tmp_path, session_id="stage-outcome")
    dataset = build_session_stage_dataset(
        session_id=session.metadata.session_id,
        target_levels_completed=1,
    )

    report = asyncio.run(
        dataset.evaluate(
            SessionStageTask(tmp_path),
            name=dataset.name,
            max_concurrency=1,
            progress=False,
        )
    )

    assert report.name == "session_stage_outcome_v1"
    assert len(report.cases) == 1
    case = report.cases[0]
    assert {name: result.value for name, result in case.assertions.items()} == {
        "target_reached": True,
        "stage_evidence_complete": True,
        "no_failure_before_target": True,
    }
    assert case.metrics["actions_to_target"] == 2
    assert case.metrics["turns_to_target"] == 2
    assert case.metrics["prediction_accuracy"] == 0.5
    assert case.metrics["tool_calls.read_history"] == 1
    assert case.attributes["session_id"] == session.metadata.session_id
    assert report_passed(report) is True


def test_evidence_regression_accepts_expected_failure_and_rejects_success(
    tmp_path: Path,
) -> None:
    failed = create_session(
        tmp_path,
        session_id="expected-failure",
        reaches_target=False,
        include_snapshot=False,
    )
    successful = create_session(tmp_path, session_id="unexpected-success")
    expected = expectation_from(failed)
    dataset = Dataset(
        name="negative-evidence-fixture",
        cases=[
            Case(
                inputs=StageEvalInput(
                    session_id=failed.metadata.session_id,
                    target_levels_completed=1,
                ),
                metadata=StageEvalMetadata(
                    provenance="synthetic_negative",
                    expected=expected,
                ),
            )
        ],
        evaluators=[SessionEvidenceRegressionEvaluator()],
    )

    matching = asyncio.run(
        dataset.evaluate(
            SessionStageTask(tmp_path),
            name=dataset.name,
            max_concurrency=1,
            progress=False,
        )
    )
    successful_outcome = extract_stage_outcome(
        successful,
        target_levels_completed=1,
    )
    always_success = asyncio.run(
        dataset.evaluate(
            lambda _inputs: successful_outcome,
            name=dataset.name,
            max_concurrency=1,
            progress=False,
        )
    )

    assert report_passed(matching) is True
    assert report_passed(always_success) is False


def test_historical_eval_declares_exact_facts_for_both_successes() -> None:
    dataset = build_ls20_session_evidence_dataset()

    assert dataset.name == LS20_SESSION_EVIDENCE_EVAL_NAME
    assert tuple(case.inputs.session_id for case in dataset.cases) == (
        LS20_SUCCESS_SESSIONS
    )
    assert [case.metadata.expected.actions_to_target for case in dataset.cases] == [
        25,
        25,
    ]
    assert [case.metadata.expected.turns_to_target for case in dataset.cases] == [
        11,
        11,
    ]
    assert [
        case.metadata.expected.post_target_run_failure for case in dataset.cases
    ] == [None, "UnexpectedModelBehavior"]
    assert all(case.expected_output is None for case in dataset.cases)
    assert len(dataset.evaluators) == 1
    assert isinstance(dataset.evaluators[0], SessionEvidenceRegressionEvaluator)
    session_dataset = build_session_stage_dataset(
        session_id="session",
        target_levels_completed=1,
    )
    assert isinstance(session_dataset.evaluators[0], StageOutcomeEvaluator)
