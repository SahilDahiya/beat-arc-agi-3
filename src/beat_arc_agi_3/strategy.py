from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.timeline import JsonlTimeline, Transition


RECENT_PREDICTION_WINDOW = 5
SHORT_CYCLE_MAX_LENGTH = 8


def _observation_signature(observation: GameObservation) -> tuple[object, ...]:
    """Return observable state while deliberately excluding animation ticks."""

    return (
        observation.grid,
        observation.state,
        observation.levels_completed,
        observation.win_levels,
        observation.available_actions,
    )


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
    current_signature = _observation_signature(observations[-1])
    matching_indices = [
        index
        for index, observation in enumerate(observations)
        if _observation_signature(observation) == current_signature
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
        "- If no evidence-backed goal-reaching plan exists, commit the "
        "smallest discriminating experiment and state what its outcome will "
        "confirm or falsify."
    )
    return "\n".join(lines)
