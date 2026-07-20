import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.events import EventJournalEntry
from beat_arc_agi_3.schemas import GameObservation, Grid
from beat_arc_agi_3.session import Session
from beat_arc_agi_3.timeline import Transition


ObserverStatus = Literal["starting", "running", "completed", "failed", "interrupted"]
DiscoveryPhase = Literal[
    "setup",
    "observe",
    "synthesize",
    "verify",
    "act",
    "learn",
]
EventTone = Literal["neutral", "active", "success", "warning", "danger"]


OFFICIAL_COLOR_MAP: dict[int, str] = {
    0: "#FFFFFF",
    1: "#CCCCCC",
    2: "#999999",
    3: "#666666",
    4: "#333333",
    5: "#000000",
    6: "#E53AA3",
    7: "#FF7BCC",
    8: "#F93C31",
    9: "#1E93FF",
    10: "#88D8F1",
    11: "#FFDC00",
    12: "#FF851B",
    13: "#921231",
    14: "#4FCC30",
    15: "#A356D6",
}


class ObserverEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    seq: int = Field(ge=1)
    turn: int = Field(ge=0)
    timestamp: str
    event_type: str
    summary: str
    phase: DiscoveryPhase
    tone: EventTone
    details: tuple[tuple[str, str], ...]


class TransitionMarker(BaseModel):
    model_config = ConfigDict(frozen=True)

    position: int = Field(ge=0)
    label: str
    action: str | None
    levels_completed: int = Field(ge=0)
    prediction_status: Literal["exact", "mismatch", "unchecked"] | None
    level_up: bool = False
    dead: bool = False
    win: bool = False


class SessionView(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    game_id: str
    model: str
    created_at: str
    status: ObserverStatus
    current_position: int = Field(ge=-1)
    transition_count: int = Field(ge=0)
    event_count: int = Field(ge=1)
    latest_event_seq: int = Field(ge=1)
    latest_turn: int = Field(ge=0)
    current_observation: GameObservation | None
    latest_revision: str | None
    latest_commit_reason: str | None
    latest_commit_suggestion: str | None
    transitions: tuple[TransitionMarker, ...]
    events: tuple[ObserverEvent, ...]


class TransitionView(BaseModel):
    model_config = ConfigDict(frozen=True)

    position: int = Field(ge=0)
    current_position: int = Field(ge=0)
    title: str
    action_label: str
    observation: GameObservation
    before: GameObservation | None
    transition: Transition | None
    changed_cells: int = Field(ge=0)
    is_live: bool
    markers: tuple[TransitionMarker, ...]


def _phase(entry: EventJournalEntry) -> DiscoveryPhase:
    event = entry.event
    event_type = event.type
    if event_type in {
        "session_started",
        "environment_replay_started",
        "environment_replay_failed",
        "environment_restarted",
        "run_completed",
        "run_failed",
        "run_interrupted",
    }:
        return "setup"
    if event_type in {
        "turn_started",
        "deliberation_started",
        "deliberation_checkpointed",
        "deliberation_attempt_failed",
    }:
        return "observe"
    if event_type in {"world_model_installed"}:
        return "synthesize"
    if event_type in {"backtest_completed", "bfs_completed"}:
        return "verify"
    if event_type in {
        "commit_accepted",
        "action_started",
        "action_completed",
        "queue_cancelled",
        "turn_completed",
    }:
        if event_type == "action_completed" and (
            event.level_up or event.dead or event.win
        ):
            return "learn"
        return "act"
    if event_type in {"prediction_mismatch", "world_model_snapshotted"}:
        return "learn"
    if event_type in {"tool_started", "tool_completed", "tool_failed"}:
        tool_name = event.tool_name
        if tool_name in {"write_file", "edit_file"}:
            return "synthesize"
        if tool_name in {"run_backtest", "run_bfs", "run_python"}:
            return "verify"
        return "observe"
    raise ValueError(f"unmapped observer event type: {event_type}")


def _tone(entry: EventJournalEntry) -> EventTone:
    event = entry.event
    if event.type in {
        "environment_replay_failed",
        "tool_failed",
        "run_failed",
        "run_interrupted",
    }:
        return "danger"
    if event.type in {
        "prediction_mismatch",
        "queue_cancelled",
        "deliberation_attempt_failed",
    }:
        return "warning"
    if event.type == "backtest_completed":
        return "success" if event.status == "green" else "warning"
    if event.type == "bfs_completed":
        return "success" if event.status == "found" else "warning"
    if event.type == "action_completed":
        if event.level_up or event.win:
            return "success"
        if event.prediction_status == "mismatch" or event.dead:
            return "warning"
    if event.type in {
        "world_model_installed",
        "world_model_snapshotted",
        "environment_restarted",
    }:
        return "success"
    if event.type in {"turn_started", "tool_started", "action_started"}:
        return "active"
    return "neutral"


def _details(entry: EventJournalEntry) -> tuple[tuple[str, str], ...]:
    payload = entry.event.model_dump(mode="json")
    details = []
    for key, value in payload.items():
        if key in {"type", "summary", "message", "reason", "suggestion"}:
            continue
        if value is None or value is False or value == []:
            continue
        rendered = (
            value
            if isinstance(value, str)
            else json.dumps(value, separators=(",", ":"), ensure_ascii=True)
        )
        details.append((key.replace("_", " "), str(rendered)))
    return tuple(details[:6])


def _project_event(entry: EventJournalEntry) -> ObserverEvent:
    return ObserverEvent(
        seq=entry.seq,
        turn=entry.turn,
        timestamp=entry.timestamp.isoformat(),
        event_type=entry.event.type,
        summary=entry.event.summary,
        phase=_phase(entry),
        tone=_tone(entry),
        details=_details(entry),
    )


def _status(entries: tuple[EventJournalEntry, ...]) -> ObserverStatus:
    latest = entries[-1].event.type
    if latest == "run_completed":
        return "completed"
    if latest == "run_failed":
        return "failed"
    if latest == "run_interrupted":
        return "interrupted"
    if latest == "session_started":
        return "starting"
    return "running"


def _action_label(transition: Transition) -> str:
    action = transition.action
    if action.x is None and action.y is None:
        return action.action
    return f"{action.action} ({action.x}, {action.y})"


def _transition_markers(session: Session) -> tuple[TransitionMarker, ...]:
    initial = session.timeline.initial_observation
    markers: list[TransitionMarker] = []
    if initial is not None:
        markers.append(
            TransitionMarker(
                position=0,
                label="Entry",
                action=None,
                levels_completed=initial.levels_completed,
                prediction_status=None,
            )
        )
    for transition in session.timeline.transitions():
        markers.append(
            TransitionMarker(
                position=transition.index + 1,
                label=f"#{transition.index + 1}",
                action=_action_label(transition),
                levels_completed=transition.after.levels_completed,
                prediction_status=transition.prediction_status,
                level_up=transition.level_up,
                dead=transition.dead,
                win=transition.win,
            )
        )
    return tuple(markers)


def build_session_view(session: Session, *, event_limit: int = 80) -> SessionView:
    if event_limit < 1:
        raise ValueError("event_limit must be positive")
    entries = session.events.entries()
    transitions = session.timeline.transitions()
    initial = session.timeline.initial_observation
    current = transitions[-1].after if transitions else initial
    latest_revision = None
    latest_commit_reason = None
    latest_commit_suggestion = None
    for entry in entries:
        event = entry.event
        if event.type == "world_model_installed":
            latest_revision = event.revision
        elif event.type == "commit_accepted":
            latest_commit_reason = event.reason
            latest_commit_suggestion = event.suggestion
    if latest_revision is None and transitions:
        latest_revision = transitions[-1].model_revision
    return SessionView(
        session_id=session.metadata.session_id,
        game_id=session.metadata.game_id,
        model=session.metadata.model,
        created_at=session.metadata.created_at.isoformat(),
        status=_status(entries),
        current_position=len(transitions) if initial is not None else -1,
        transition_count=len(transitions),
        event_count=len(entries),
        latest_event_seq=entries[-1].seq,
        latest_turn=max(entry.turn for entry in entries),
        current_observation=current,
        latest_revision=latest_revision,
        latest_commit_reason=latest_commit_reason,
        latest_commit_suggestion=latest_commit_suggestion,
        transitions=_transition_markers(session),
        events=tuple(_project_event(entry) for entry in entries[-event_limit:]),
    )


def build_transition_view(
    session: Session,
    *,
    position: int | None = None,
) -> TransitionView:
    initial = session.timeline.initial_observation
    if initial is None:
        raise ValueError("Session Timeline has no initial observation")
    transitions = session.timeline.transitions()
    current_position = len(transitions)
    selected = current_position if position is None else position
    if selected < 0 or selected > current_position:
        raise ValueError(
            f"position must be between 0 and {current_position}, got {selected}"
        )
    if selected == 0:
        return TransitionView(
            position=0,
            current_position=current_position,
            title="Initial observation",
            action_label="RESET / entry",
            observation=initial,
            before=None,
            transition=None,
            changed_cells=0,
            is_live=selected == current_position,
            markers=_transition_markers(session),
        )
    transition = transitions[selected - 1]
    changed_cells = sum(
        before != after
        for before_row, after_row in zip(
            transition.before.grid, transition.after.grid, strict=True
        )
        for before, after in zip(before_row, after_row, strict=True)
    )
    return TransitionView(
        position=selected,
        current_position=current_position,
        title=f"Transition {transition.index}",
        action_label=_action_label(transition),
        observation=transition.after,
        before=transition.before,
        transition=transition,
        changed_cells=changed_cells,
        is_live=selected == current_position,
        markers=_transition_markers(session),
    )


def render_grid_svg(
    grid: Grid,
    *,
    changed_from: Grid | None = None,
) -> str:
    if not grid or not grid[0]:
        raise ValueError("cannot render an empty ARC grid")
    height = len(grid)
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError("cannot render a ragged ARC grid")
    if changed_from is not None and (
        len(changed_from) != height
        or any(len(row) != width for row in changed_from)
    ):
        raise ValueError("difference grid shape does not match rendered grid")
    rectangles = []
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            if value not in OFFICIAL_COLOR_MAP:
                raise ValueError(f"ARC color index is outside 0..15: {value}")
            changed = changed_from is None or changed_from[y][x] != value
            color = OFFICIAL_COLOR_MAP[value] if changed else "#171A20"
            rectangles.append(
                f'<rect x="{x}" y="{y}" width="1" height="1" fill="{color}"/>'
            )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        'shape-rendering="crispEdges" role="img" '
        f'aria-label="ARC grid, {width} by {height}">'
        + "".join(rectangles)
        + "</svg>"
    )


def render_sse_update(seq: int) -> str:
    if seq < 1:
        raise ValueError("SSE event sequence must be positive")
    return f"id: {seq}\nevent: session-update\ndata: {seq}\n\n"
