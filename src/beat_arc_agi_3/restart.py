from pathlib import Path

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.events import ActionCompletedEvent, ActionStartedEvent
from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.session import Session


class RestartError(RuntimeError):
    """Base failure for explicit replay-based Session restart."""


class RestartUnsafeError(RestartError):
    """Raised when parent evidence cannot prove a safe replay boundary."""


class ReplayDivergenceError(RestartError):
    """Raised when a fresh environment does not reproduce parent evidence."""


def replay_session(
    *,
    parent: Session,
    adapter: ArcGameAdapter,
    initial_observation: GameObservation,
) -> GameObservation:
    """Replay every confirmed parent action and require exact observations."""

    started = {
        (entry.event.action_number, entry.event.transition_index)
        for entry in parent.events.entries()
        if isinstance(entry.event, ActionStartedEvent)
    }
    completed = {
        (entry.event.action_number, entry.event.transition_index)
        for entry in parent.events.entries()
        if isinstance(entry.event, ActionCompletedEvent)
    }
    uncertain = started - completed
    if uncertain:
        action_number, transition_index = min(uncertain)
        raise RestartUnsafeError(
            "parent contains an uncertain ARC action: "
            f"action {action_number}, transition {transition_index} started "
            "without durable completion"
        )

    expected_initial = parent.timeline.initial_observation
    if expected_initial is None:
        raise RestartUnsafeError("parent Timeline has no initial observation")
    if initial_observation != expected_initial:
        raise ReplayDivergenceError(
            "fresh environment initial observation does not match parent"
        )

    current = initial_observation
    for transition in parent.timeline.transitions():
        if current != transition.before:
            raise RestartUnsafeError(
                f"parent Timeline is discontinuous at transition "
                f"{transition.index}"
            )
        current = adapter.apply(transition.action)
        if current != transition.after:
            raise ReplayDivergenceError(
                f"replay diverged at transition {transition.index} after "
                f"{transition.action.action}"
            )
    return current


def create_restarted_session(
    *,
    parent: Session,
    sessions_root: str | Path,
    session_id: str,
    model: str,
    checkpoint: GameObservation,
    operation_mode: str | None = None,
    environment_guid: str | None = None,
    scorecard_id: str | None = None,
) -> Session:
    """Create an atomic child Session after successful deterministic replay."""

    transitions = parent.timeline.transitions()
    expected = (
        transitions[-1].after
        if transitions
        else parent.timeline.initial_observation
    )
    if expected is None or checkpoint != expected:
        raise RestartUnsafeError(
            "replay checkpoint does not match the parent Timeline tail"
        )
    return Session.create(
        sessions_root=sessions_root,
        session_id=session_id,
        game_id=parent.metadata.game_id,
        model=model,
        restart_parent=parent,
        operation_mode=operation_mode,
        environment_guid=environment_guid,
        scorecard_id=scorecard_id,
    )
