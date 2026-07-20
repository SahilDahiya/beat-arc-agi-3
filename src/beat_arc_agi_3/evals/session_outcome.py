from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pydantic_evals import increment_eval_metric, set_eval_attribute

from beat_arc_agi_3.evals.models import StageEvalInput, StageEvalOutcome
from beat_arc_agi_3.events import (
    ActionCompletedEvent,
    EnvironmentRestartedEvent,
    EventJournalEntry,
    RunFailedEvent,
    RunInterruptedEvent,
    ToolCompletedEvent,
    WorldModelSnapshottedEvent,
)
from beat_arc_agi_3.session import Session
from beat_arc_agi_3.timeline import Transition


def extract_stage_outcome(
    session: Session,
    *,
    target_levels_completed: int,
) -> StageEvalOutcome:
    """Extract the first crossing of a level target from validated evidence."""

    if target_levels_completed < 1:
        raise ValueError("target_levels_completed must be positive")
    initial = session.timeline.initial_observation
    if initial is None:
        raise ValueError("cannot evaluate an uninitialized Session timeline")
    if target_levels_completed <= initial.levels_completed:
        raise ValueError(
            "target_levels_completed must be greater than the initial level"
        )

    transitions = session.timeline.transitions()
    target_transition = next(
        (
            transition
            for transition in transitions
            if transition.after.levels_completed >= target_levels_completed
        ),
        None,
    )
    entries = session.events.entries()
    target_action_entry = _find_target_action_entry(
        entries,
        target_transition=target_transition,
        target_levels_completed=target_levels_completed,
    )
    boundary_seq = (
        target_action_entry.seq if target_action_entry is not None else None
    )
    scoped_transitions = (
        transitions[: target_transition.index + 1]
        if target_transition is not None
        else transitions
    )
    scoped_entries = (
        tuple(entry for entry in entries if entry.seq <= boundary_seq)
        if boundary_seq is not None
        else entries
    )
    prediction_counts = Counter(
        transition.prediction_status for transition in scoped_transitions
    )
    tool_counts = Counter(
        entry.event.tool_name
        for entry in scoped_entries
        if isinstance(entry.event, ToolCompletedEvent)
    )
    snapshot_entry = _find_target_snapshot_entry(
        entries,
        target_transition=target_transition,
    )
    failure_entries = tuple(
        entry
        for entry in entries
        if isinstance(entry.event, (RunFailedEvent, RunInterruptedEvent))
    )
    failure_before_target = any(
        not _failure_was_recovered(
            entry,
            entries=entries,
            boundary_seq=boundary_seq,
        )
        for entry in failure_entries
        if boundary_seq is None or entry.seq < boundary_seq
    )
    post_target_failure = next(
        (
            entry.event.error_type
            for entry in failure_entries
            if boundary_seq is not None and entry.seq > boundary_seq
        ),
        None,
    )
    final = transitions[-1].after if transitions else initial

    return StageEvalOutcome(
        session_id=session.metadata.session_id,
        game_id=session.metadata.game_id,
        model=session.metadata.model,
        target_levels_completed=target_levels_completed,
        target_reached=target_transition is not None,
        initial_levels_completed=initial.levels_completed,
        final_levels_completed=final.levels_completed,
        target_transition_index=(
            target_transition.index if target_transition is not None else None
        ),
        actions_to_target=(
            target_transition.index + 1
            if target_transition is not None
            else None
        ),
        turns_to_target=(
            target_action_entry.turn
            if target_action_entry is not None
            else None
        ),
        duration_to_target_seconds=(
            max(
                0.0,
                (
                    target_action_entry.timestamp
                    - session.metadata.created_at
                ).total_seconds(),
            )
            if target_action_entry is not None
            else None
        ),
        prediction_exact=prediction_counts["exact"],
        prediction_mismatch=prediction_counts["mismatch"],
        prediction_unchecked=prediction_counts["unchecked"],
        tool_counts=dict(sorted(tool_counts.items())),
        target_action_event_found=target_action_entry is not None,
        target_snapshot_found=snapshot_entry is not None,
        target_snapshot_path=(
            snapshot_entry.event.path if snapshot_entry is not None else None
        ),
        failure_before_target=failure_before_target,
        post_target_run_failure=post_target_failure,
    )


def _find_target_action_entry(
    entries: tuple[EventJournalEntry, ...],
    *,
    target_transition: Transition | None,
    target_levels_completed: int,
) -> EventJournalEntry | None:
    if target_transition is None:
        return None
    return next(
        (
            entry
            for entry in entries
            if isinstance(entry.event, ActionCompletedEvent)
            and entry.event.transition_index == target_transition.index
            and entry.event.levels_completed >= target_levels_completed
            and entry.event.level_up
        ),
        None,
    )


def _failure_was_recovered(
    failure_entry: EventJournalEntry,
    *,
    entries: tuple[EventJournalEntry, ...],
    boundary_seq: int | None,
) -> bool:
    return any(
        isinstance(entry.event, EnvironmentRestartedEvent)
        and entry.seq > failure_entry.seq
        and (boundary_seq is None or entry.seq < boundary_seq)
        for entry in entries
    )


def _find_target_snapshot_entry(
    entries: tuple[EventJournalEntry, ...],
    *,
    target_transition: Transition | None,
) -> EventJournalEntry | None:
    if target_transition is None:
        return None
    return next(
        (
            entry
            for entry in entries
            if isinstance(entry.event, WorldModelSnapshottedEvent)
            and entry.event.cleared_level
            == target_transition.before.levels_completed
            and entry.event.revision == target_transition.model_revision
        ),
        None,
    )


@dataclass(frozen=True)
class SessionStageTask:
    """Pydantic Evals task that scores repository-local Session evidence."""

    sessions_root: Path

    def __call__(self, inputs: StageEvalInput) -> StageEvalOutcome:
        session = Session.open(
            sessions_root=self.sessions_root,
            session_id=inputs.session_id,
        )
        outcome = extract_stage_outcome(
            session,
            target_levels_completed=inputs.target_levels_completed,
        )
        _record_eval_facts(outcome)
        return outcome


def _record_eval_facts(outcome: StageEvalOutcome) -> None:
    set_eval_attribute("session_id", outcome.session_id)
    set_eval_attribute("game_id", outcome.game_id)
    set_eval_attribute("model", outcome.model)
    if outcome.target_snapshot_path is not None:
        set_eval_attribute(
            "target_snapshot_path", outcome.target_snapshot_path
        )
    increment_eval_metric(
        "final_levels_completed", outcome.final_levels_completed
    )
    increment_eval_metric("prediction_exact", outcome.prediction_exact)
    increment_eval_metric("prediction_mismatch", outcome.prediction_mismatch)
    increment_eval_metric("prediction_unchecked", outcome.prediction_unchecked)
    if outcome.actions_to_target is not None:
        increment_eval_metric("actions_to_target", outcome.actions_to_target)
    if outcome.turns_to_target is not None:
        increment_eval_metric("turns_to_target", outcome.turns_to_target)
    if outcome.duration_to_target_seconds is not None:
        increment_eval_metric(
            "duration_to_target_seconds",
            outcome.duration_to_target_seconds,
        )
    if outcome.prediction_accuracy is not None:
        increment_eval_metric(
            "prediction_accuracy", outcome.prediction_accuracy
        )
    for tool_name, count in outcome.tool_counts.items():
        increment_eval_metric(f"tool_calls.{tool_name}", count)
