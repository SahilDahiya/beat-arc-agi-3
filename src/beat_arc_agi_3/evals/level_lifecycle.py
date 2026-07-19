from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.events import EventJournalEntry
from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.session import Session
from beat_arc_agi_3.strategy import observation_signature
from beat_arc_agi_3.timeline import Transition


TOOL_PHASES = {
    "read_history": "grounding",
    "read_file": "grounding",
    "run_python": "grounding",
    "write_file": "synthesis",
    "edit_file": "synthesis",
    "run_backtest": "verification",
    "run_bfs": "search",
}


class RepairSpan(BaseModel):
    """A model mismatch and the next observed green backtest, if any."""

    model_config = ConfigDict(frozen=True)

    mismatch_transition_index: int = Field(ge=0)
    mismatch_turn: int = Field(ge=1)
    green_turn: int | None = Field(default=None, ge=1)
    event_steps_to_green: int | None = Field(default=None, ge=1)


class LevelLifecycle(BaseModel):
    """Deterministic evidence for actions that began on one ARC level."""

    model_config = ConfigDict(frozen=True)

    level: int = Field(ge=0)
    entry_transition_index: int | None = Field(default=None, ge=0)
    exit_transition_index: int | None = Field(default=None, ge=0)
    entry_turn: int | None = Field(default=None, ge=1)
    exit_turn: int | None = Field(default=None, ge=1)
    actions: int = Field(ge=0)
    turns: int = Field(ge=0)
    prediction_exact: int = Field(ge=0)
    prediction_mismatch: int = Field(ge=0)
    prediction_unchecked: int = Field(ge=0)
    action_counts: dict[str, int]
    action6_coordinates: tuple[tuple[int, int], ...]
    distinct_observations: int = Field(ge=1)
    world_model_installs: int = Field(ge=0)
    backtests_green: int = Field(ge=0)
    backtests_mismatch: int = Field(ge=0)
    repair_spans: tuple[RepairSpan, ...]
    bfs_attempts: int = Field(ge=0)
    bfs_found: int = Field(ge=0)
    bfs_exhausted: int = Field(ge=0)
    bfs_plan_depths: tuple[int, ...]
    commit_queue_sizes: tuple[int, ...]
    queue_cancellations: dict[str, int]
    deaths: int = Field(ge=0)
    resets: int = Field(ge=0)
    level_ups: int = Field(ge=0)
    wins: int = Field(ge=0)
    run_failures: int = Field(ge=0)
    run_interruptions: int = Field(ge=0)
    tool_counts: dict[str, int]
    tool_counts_by_phase: dict[str, int]


class LevelLifecycleReport(BaseModel):
    """Per-level process report extracted from one validated Session."""

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1)
    game_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    levels: tuple[LevelLifecycle, ...]


def _turn_levels(entries: tuple[EventJournalEntry, ...]) -> dict[int, int]:
    return {
        entry.turn: entry.event.levels_completed
        for entry in entries
        if entry.event.type == "turn_started"
    }


def _transition_turns(
    entries: tuple[EventJournalEntry, ...],
) -> dict[int, int]:
    return {
        entry.event.transition_index: entry.turn
        for entry in entries
        if entry.event.type == "action_completed"
    }


def _level_entries(
    entries: tuple[EventJournalEntry, ...],
    turn_levels: dict[int, int],
    level: int,
) -> tuple[EventJournalEntry, ...]:
    return tuple(
        entry
        for entry in entries
        if turn_levels.get(entry.turn) == level
    )


def _repair_spans(
    transitions: tuple[Transition, ...],
    entries: tuple[EventJournalEntry, ...],
) -> tuple[RepairSpan, ...]:
    action_entries = {
        entry.event.transition_index: entry
        for entry in entries
        if entry.event.type == "action_completed"
    }
    green_entries = tuple(
        entry
        for entry in entries
        if entry.event.type == "backtest_completed"
        and entry.event.status == "green"
    )
    spans = []
    for transition in transitions:
        if transition.prediction_status != "mismatch":
            continue
        mismatch_entry = action_entries.get(transition.index)
        if mismatch_entry is None:
            continue
        green = next(
            (entry for entry in green_entries if entry.seq > mismatch_entry.seq),
            None,
        )
        spans.append(
            RepairSpan(
                mismatch_transition_index=transition.index,
                mismatch_turn=mismatch_entry.turn,
                green_turn=None if green is None else green.turn,
                event_steps_to_green=(
                    None if green is None else green.seq - mismatch_entry.seq
                ),
            )
        )
    return tuple(spans)


def _extract_level(
    *,
    level: int,
    initial: GameObservation,
    all_transitions: tuple[Transition, ...],
    all_entries: tuple[EventJournalEntry, ...],
    turn_levels: dict[int, int],
    transition_turns: dict[int, int],
) -> LevelLifecycle:
    transitions = tuple(
        transition
        for transition in all_transitions
        if transition.before.levels_completed == level
    )
    entries = _level_entries(all_entries, turn_levels, level)
    entry_transition = next(
        (
            transition
            for transition in all_transitions
            if transition.after.levels_completed == level
            and transition.before.levels_completed < level
        ),
        None,
    )
    exit_transition = next(
        (
            transition
            for transition in transitions
            if transition.level_up or transition.win
        ),
        None,
    )
    observations = []
    if initial.levels_completed == level:
        observations.append(initial)
    if entry_transition is not None:
        observations.append(entry_transition.after)
    for transition in transitions:
        observations.extend((transition.before, transition.after))
    if not observations:
        raise ValueError(f"level {level} has no observable evidence")

    tool_counts = Counter(
        entry.event.tool_name
        for entry in entries
        if entry.event.type == "tool_completed"
    )
    phase_counts: Counter[str] = Counter()
    for tool_name, count in tool_counts.items():
        phase_counts[TOOL_PHASES[tool_name]] += count
    bfs_events = tuple(
        entry.event for entry in entries if entry.event.type == "bfs_completed"
    )
    queue_events = tuple(
        entry.event
        for entry in entries
        if entry.event.type == "queue_cancelled"
    )
    backtests = tuple(
        entry.event
        for entry in entries
        if entry.event.type == "backtest_completed"
    )
    clicks = sorted(
        {
            (transition.action.x, transition.action.y)
            for transition in transitions
            if transition.action.action == "ACTION6"
        }
    )
    assert all(x is not None and y is not None for x, y in clicks)

    return LevelLifecycle(
        level=level,
        entry_transition_index=(
            None if entry_transition is None else entry_transition.index
        ),
        exit_transition_index=(
            None if exit_transition is None else exit_transition.index
        ),
        entry_turn=(
            min(
                (
                    turn
                    for turn, item in turn_levels.items()
                    if item == level
                ),
                default=None,
            )
        ),
        exit_turn=(
            None
            if exit_transition is None
            else transition_turns.get(exit_transition.index)
        ),
        actions=len(transitions),
        turns=len({entry.turn for entry in entries if entry.turn > 0}),
        prediction_exact=sum(
            transition.prediction_status == "exact"
            for transition in transitions
        ),
        prediction_mismatch=sum(
            transition.prediction_status == "mismatch"
            for transition in transitions
        ),
        prediction_unchecked=sum(
            transition.prediction_status == "unchecked"
            for transition in transitions
        ),
        action_counts=dict(
            sorted(Counter(item.action.action for item in transitions).items())
        ),
        action6_coordinates=tuple((int(x), int(y)) for x, y in clicks),
        distinct_observations=len(
            {observation_signature(observation) for observation in observations}
        ),
        world_model_installs=sum(
            entry.event.type == "world_model_installed" for entry in entries
        ),
        backtests_green=sum(event.status == "green" for event in backtests),
        backtests_mismatch=sum(
            event.status == "mismatch" for event in backtests
        ),
        repair_spans=_repair_spans(transitions, entries),
        bfs_attempts=len(bfs_events),
        bfs_found=sum(event.status == "found" for event in bfs_events),
        bfs_exhausted=sum(event.status == "exhausted" for event in bfs_events),
        bfs_plan_depths=tuple(
            event.depth
            for event in bfs_events
            if event.status == "found" and event.depth is not None
        ),
        commit_queue_sizes=tuple(
            len(entry.event.actions)
            for entry in entries
            if entry.event.type == "commit_accepted"
        ),
        queue_cancellations=dict(
            sorted(Counter(event.reason for event in queue_events).items())
        ),
        deaths=sum(transition.dead for transition in transitions),
        resets=sum(
            transition.action.action == "RESET" for transition in transitions
        ),
        level_ups=sum(transition.level_up for transition in transitions),
        wins=sum(transition.win for transition in transitions),
        run_failures=sum(entry.event.type == "run_failed" for entry in entries),
        run_interruptions=sum(
            entry.event.type == "run_interrupted" for entry in entries
        ),
        tool_counts=dict(sorted(tool_counts.items())),
        tool_counts_by_phase=dict(sorted(phase_counts.items())),
    )


def extract_level_lifecycle(session: Session) -> LevelLifecycleReport:
    """Extract deterministic per-level process evidence from one Session."""

    initial = session.timeline.initial_observation
    if initial is None:
        raise ValueError("cannot report an uninitialized Session timeline")
    transitions = session.timeline.transitions()
    entries = session.events.entries()
    turn_levels = _turn_levels(entries)
    transition_turns = _transition_turns(entries)
    observed_levels = {
        initial.levels_completed,
        *(transition.before.levels_completed for transition in transitions),
        *(transition.after.levels_completed for transition in transitions),
    }
    levels = tuple(
        _extract_level(
            level=level,
            initial=initial,
            all_transitions=transitions,
            all_entries=entries,
            turn_levels=turn_levels,
            transition_turns=transition_turns,
        )
        for level in sorted(observed_levels)
    )
    return LevelLifecycleReport(
        session_id=session.metadata.session_id,
        game_id=session.metadata.game_id,
        model=session.metadata.model,
        levels=levels,
    )
