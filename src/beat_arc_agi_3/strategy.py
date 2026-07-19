from collections import Counter

from beat_arc_agi_3.events import EventJournal
from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.timeline import JsonlTimeline, Transition


RECENT_PREDICTION_WINDOW = 5
SHORT_CYCLE_MAX_LENGTH = 8


def _render_color_counts(values: list[int]) -> str:
    counts = Counter(values)
    if not counts:
        return "none"
    return ",".join(f"{color}:{counts[color]}" for color in sorted(counts))


def render_level_entry_context(timeline: JsonlTimeline) -> str | None:
    """Render factual grounding requirements only at a new level entry."""

    initial = timeline.initial_observation
    if initial is None:
        raise ValueError("level-entry context requires an initialized Timeline")

    transitions = timeline.transitions()
    if not transitions:
        observation = initial
        trigger = "session_start"
    elif transitions[-1].level_up:
        observation = transitions[-1].after
        trigger = f"transition #{transitions[-1].index} level_up"
    else:
        return None

    height = len(observation.grid)
    width = len(observation.grid[0]) if observation.grid else 0
    band_width = (
        max(1, (min(height, width) + 9) // 10)
        if height > 0 and width > 0
        else 0
    )
    all_values = [value for row in observation.grid for value in row]
    peripheral_values: list[int] = []
    interior_values: list[int] = []
    for row_index, row in enumerate(observation.grid):
        for column_index, value in enumerate(row):
            is_peripheral = (
                row_index < band_width
                or column_index < band_width
                or row_index >= height - band_width
                or column_index >= width - band_width
            )
            target = peripheral_values if is_peripheral else interior_values
            target.append(value)

    actions = ",".join(observation.legal_action_names) or "none"
    return "\n".join(
        [
            "Level-entry grounding protocol:",
            (
                f"- trigger={trigger}; level={observation.levels_completed}/"
                f"{observation.win_levels}"
            ),
            (
                f"- entry grid shape={height}x{width}; color counts="
                f"{_render_color_counts(all_values)}"
            ),
            (
                f"- geometric peripheral band width={band_width}; "
                "peripheral color counts="
                f"{_render_color_counts(peripheral_values)}; "
                f"interior color counts={_render_color_counts(interior_values)}"
            ),
            f"- legal actions={actions}",
            "Before committing a route, update notes.md with these testable "
            "structures:",
            (
                "- Observed facts: exact playfield/periphery geometry, color "
                "groups, prior action effects, and any demonstrated lattice "
                "or walkability constraints."
            ),
            (
                "- Hypotheses: explicitly tentative avatar/objects, action "
                "mapping, persistent or consumable resources, counters or "
                "meters, and target-like patterns."
            ),
            (
                "- Known unknowns: the missing evidence that blocks a "
                "supported plan."
            ),
            (
                "- Cheapest discriminating probe: an action or short known-safe "
                "prefix plus one uncertain final action, with expected result."
            ),
            (
                "- Temporary goal: record a predicate, evidence, and falsifier; "
                "encode the best-supported current form in is_goal. It is "
                "revisable, not a permanent truth."
            ),
            (
                "- Decision mode: record goal_search only when the temporary "
                "goal has supporting evidence, a falsifier, and a green "
                "executable predicate. Otherwise record "
                "discriminating_experiment and test the selected hypothesis "
                "against a competing hypothesis."
            ),
            (
                "Use run_python for exact structural inspection when useful. "
                "Do not assign semantic labels to colors or regions without "
                "transition evidence."
            ),
        ]
    )


def render_strategy_context(
    timeline: JsonlTimeline,
    events: EventJournal,
) -> str:
    """Render current deterministic strategy guidance for deliberation."""

    sections = [
        render_level_entry_context(timeline),
        render_current_level_evidence(timeline, events),
        render_experiment_context(timeline),
    ]
    return "\n\n".join(section for section in sections if section is not None)


def observation_signature(observation: GameObservation) -> tuple[object, ...]:
    """Return observable state while deliberately excluding animation ticks."""

    return (
        observation.grid,
        observation.state,
        observation.levels_completed,
        observation.win_levels,
        observation.available_actions,
    )


def render_current_level_evidence(
    timeline: JsonlTimeline,
    events: EventJournal,
) -> str:
    """Render bounded current-level support separately from replay trust."""

    initial = timeline.initial_observation
    if initial is None:
        raise ValueError(
            "current-level evidence requires an initialized Timeline"
        )
    transitions = timeline.transitions()
    current = transitions[-1].after if transitions else initial
    current_level = current.levels_completed
    level_transitions = tuple(
        transition
        for transition in transitions
        if transition.before.levels_completed == current_level
    )
    observations = [current]
    for transition in level_transitions:
        observations.extend((transition.before, transition.after))
    exact = sum(
        transition.prediction_status == "exact"
        for transition in level_transitions
    )
    mismatch = sum(
        transition.prediction_status == "mismatch"
        for transition in level_transitions
    )
    unchecked = sum(
        transition.prediction_status == "unchecked"
        for transition in level_transitions
    )
    action_counts = Counter(
        transition.action.action for transition in level_transitions
    )
    rendered_actions = (
        ",".join(
            f"{action}:{count}"
            for action, count in sorted(action_counts.items())
        )
        or "none"
    )
    click_coordinates = sorted(
        {
            (transition.action.x, transition.action.y)
            for transition in level_transitions
            if transition.action.action == "ACTION6"
        }
    )
    rendered_clicks = (
        ",".join(f"({x},{y})" for x, y in click_coordinates)
        if click_coordinates
        else "none"
    )

    entries = events.entries()
    installed = next(
        (
            entry.event
            for entry in reversed(entries)
            if entry.event.type == "world_model_installed"
        ),
        None,
    )
    active_revision = None if installed is None else installed.revision
    backtest = next(
        (
            entry.event
            for entry in reversed(entries)
            if entry.event.type == "backtest_completed"
            and entry.event.revision == active_revision
        ),
        None,
    )
    if active_revision is None:
        replay_status = "not-installed"
    elif backtest is None:
        replay_status = "not-backtested"
    elif backtest.status == "mismatch":
        replay_status = "mismatch"
    elif backtest.timeline_transitions != len(transitions):
        replay_status = "stale-prefix"
    else:
        replay_status = "current-prefix-green"
    active_support = tuple(
        transition
        for transition in level_transitions
        if transition.model_revision == active_revision
    )
    support_exact = sum(
        transition.prediction_status == "exact" for transition in active_support
    )
    support_mismatch = sum(
        transition.prediction_status == "mismatch"
        for transition in active_support
    )
    support_unchecked = sum(
        transition.prediction_status == "unchecked"
        for transition in active_support
    )
    latest_mismatch = next(
        (
            transition
            for transition in reversed(level_transitions)
            if transition.prediction_status == "mismatch"
        ),
        None,
    )
    turn_levels = {
        entry.turn: entry.event.levels_completed
        for entry in entries
        if entry.event.type == "turn_started"
    }
    bfs_events = tuple(
        entry.event
        for entry in entries
        if entry.event.type == "bfs_completed"
        and turn_levels.get(entry.turn) == current_level
    )

    lines = [
        f"Current-level evidence: level={current_level}",
        (
            f"- transitions={len(level_transitions)}; exact={exact}; "
            f"mismatch={mismatch}; unchecked={unchecked}; distinct "
            "observable states="
            f"{len({observation_signature(item) for item in observations})}"
        ),
        f"- actions={rendered_actions}; ACTION6 coordinates={rendered_clicks}",
        (
            "- active revision="
            f"{active_revision[:12] if active_revision else 'none'}; "
            f"full replay={replay_status}"
        ),
        (
            f"- active-revision online support exact={support_exact}; "
            f"mismatch={support_mismatch}; unchecked={support_unchecked}"
        ),
    ]
    if not active_support:
        lines.append(
            "- no online transition support on the current level for the "
            "active revision; replay-green is historical consistency only"
        )
    if latest_mismatch is not None:
        lines.append(
            "- latest current-level mismatch=transition "
            f"#{latest_mismatch.index} revision "
            f"{latest_mismatch.model_revision[:12]}"
        )
    lines.append(
        f"- BFS attempts={len(bfs_events)}; "
        f"found={sum(event.status == 'found' for event in bfs_events)}; "
        f"exhausted={sum(event.status == 'exhausted' for event in bfs_events)}"
    )
    return "\n".join(lines)


def _actions_without_level_progress(
    transitions: tuple[Transition, ...],
) -> int:
    count = 0
    for transition in reversed(transitions):
        if transition.level_up or transition.win:
            break
        count += 1
    return count


def _grid_difference(
    before: GameObservation,
    after: GameObservation,
) -> tuple[int, int] | None:
    if len(before.grid) != len(after.grid):
        return None
    if any(
        len(before_row) != len(after_row)
        for before_row, after_row in zip(
            before.grid,
            after.grid,
            strict=True,
        )
    ):
        return None
    cells = sum(len(row) for row in after.grid)
    differences = sum(
        before_value != after_value
        for before_row, after_row in zip(
            before.grid,
            after.grid,
            strict=True,
        )
        for before_value, after_value in zip(
            before_row,
            after_row,
            strict=True,
        )
    )
    return differences, cells


def render_experiment_context(timeline: JsonlTimeline) -> str:
    """Render compact, evidence-only strategy pressure for the next turn."""

    initial = timeline.initial_observation
    if initial is None:
        raise ValueError("experiment context requires an initialized Timeline")

    transitions = timeline.transitions()
    observations = (initial, *(item.after for item in transitions))
    current_signature = observation_signature(observations[-1])
    matching_indices = [
        index
        for index, observation in enumerate(observations)
        if observation_signature(observation) == current_signature
    ]
    revisit_distance = (
        len(observations) - 1 - matching_indices[-2]
        if len(matching_indices) > 1
        else None
    )
    current_index = len(observations) - 1
    nearest_candidates = []
    for index, observation in enumerate(observations[:-1]):
        distance = current_index - index
        if distance > SHORT_CYCLE_MAX_LENGTH:
            continue
        difference = _grid_difference(observation, observations[-1])
        if difference is not None:
            differing_cells, total_cells = difference
            nearest_candidates.append(
                (differing_cells, distance, total_cells)
            )
    nearest = min(nearest_candidates, default=None)

    exact = sum(item.prediction_status == "exact" for item in transitions)
    unchecked = sum(item.prediction_status == "unchecked" for item in transitions)
    certified = len(transitions) - unchecked
    recent = transitions[-RECENT_PREDICTION_WINDOW:]
    recent_certified = tuple(
        item for item in recent if item.prediction_status != "unchecked"
    )
    recent_mismatches = sum(
        item.prediction_status == "mismatch" for item in recent_certified
    )
    latest_mismatch = next(
        (
            item
            for item in reversed(transitions)
            if item.prediction_status == "mismatch"
        ),
        None,
    )

    lines = [
        "Harness experiment evidence:",
        (
            f"- transitions={len(transitions)}; online predictions "
            f"exact={exact}/{certified}; recent prediction "
            f"mismatches={recent_mismatches}/{len(recent_certified)}"
        ),
        f"- unchecked exploratory transitions={unchecked}",
        (
            "- actions without level progress="
            f"{_actions_without_level_progress(transitions)}; current "
            f"observable state visits={len(matching_indices)}"
        ),
    ]
    if transitions:
        lines.append(
            "- recent actions="
            + ",".join(
                item.action.action
                for item in transitions[-SHORT_CYCLE_MAX_LENGTH:]
            )
        )
    if nearest is not None:
        differing_cells, distance, total_cells = nearest
        lines.append(
            "- nearest recent prior observation differs="
            f"{differing_cells}/{total_cells} cells; action distance={distance}"
        )
    if (
        revisit_distance is not None
        and revisit_distance <= SHORT_CYCLE_MAX_LENGTH
    ):
        lines.append(
            f"- observable-state cycle length={revisit_distance}; repeating "
            "the same action path is not progress"
        )

    lines.extend(
        [
            "Decision requirements:",
            (
                "- A green backtest proves consistency with recorded history "
                "only, not that the mechanism or goal is correct."
            ),
        ]
    )
    if latest_mismatch is not None:
        lines.append(
            f"- transition #{latest_mismatch.index} is the latest "
            "counterexample. Inspect it at full detail and repair a general "
            "mechanism before acting. Do not patch by transition index or "
            "action occurrence count unless the evidence demonstrates a "
            "corresponding hidden state."
        )
    if len(matching_indices) > 1:
        lines.append(
            "- The current observable state has been revisited. Abandon an "
            "unsupported repeated route and test a competing explanation."
        )
    lines.append(
        "- If no evidence-backed goal-reaching plan exists, use a known-safe "
        "modeled prefix to reach the smallest discriminating experiment, put "
        "the uncertain action last, and state what its outcome will confirm "
        "or falsify."
    )
    return "\n".join(lines)
