from arcengine import GameState
from pydantic_ai import ModelRequest

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.events import ActionCompletedEvent, ActionStartedEvent
from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.session import Session


class RestartError(RuntimeError):
    """Base failure for explicit replay-based environment restart."""


class RestartUnsafeError(RestartError):
    """Raised when Session evidence cannot prove a safe replay boundary."""


class ReplayDivergenceError(RestartError):
    """Raised when a fresh environment does not reproduce Session evidence."""


def resumes_pending_deliberation(session: Session) -> bool:
    """Return whether restart should continue a saved model request."""

    last_started = 0
    last_commit = 0
    for entry in session.events.entries():
        if entry.event.type == "deliberation_started":
            last_started = entry.seq
        elif entry.event.type == "commit_accepted":
            last_commit = entry.seq
    pending = last_started > last_commit
    if not pending:
        return False
    messages = session.conversation.messages()
    if (
        not messages
        or not isinstance(messages[-1], ModelRequest)
        or messages[-1].state != "complete"
    ):
        raise RestartUnsafeError(
            "pending deliberation has no provider-valid request checkpoint"
        )
    return True


def replay_session(
    *,
    session: Session,
    adapter: ArcGameAdapter,
    initial_observation: GameObservation,
) -> GameObservation:
    """Replay confirmed Session actions and require exact observations."""

    transitions = session.timeline.transitions()
    tail = (
        transitions[-1].after
        if transitions
        else session.timeline.initial_observation
    )
    if tail is not None and tail.state is GameState.WIN:
        raise RestartUnsafeError("Session is already in WIN state")

    started = {
        entry.event.transition_index
        for entry in session.events.entries()
        if isinstance(entry.event, ActionStartedEvent)
    }
    completed = {
        entry.event.transition_index
        for entry in session.events.entries()
        if isinstance(entry.event, ActionCompletedEvent)
    }
    uncertain = started - completed
    if uncertain:
        transition_index = min(uncertain)
        raise RestartUnsafeError(
            "Session contains an uncertain ARC action: transition "
            f"{transition_index} started without durable completion"
        )

    expected_initial = session.timeline.initial_observation
    if expected_initial is None:
        raise RestartUnsafeError("Session Timeline has no initial observation")
    if initial_observation != expected_initial:
        raise ReplayDivergenceError(
            "fresh environment initial observation does not match Session"
        )

    current = initial_observation
    for transition in transitions:
        if current != transition.before:
            raise RestartUnsafeError(
                f"Session Timeline is discontinuous at transition "
                f"{transition.index}"
            )
        current = adapter.apply(transition.action)
        if current != transition.after:
            raise ReplayDivergenceError(
                f"replay diverged at transition {transition.index} after "
                f"{transition.action.action}"
            )
    return current
