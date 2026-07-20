import asyncio
from collections import Counter

from arcengine import GameAction

from beat_arc_agi_3.dependencies import HistoryDetail, HistoryQuery
from beat_arc_agi_3.grid_analysis import (
    render_grid_change_summary,
    summarize_grid_change,
)
from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.timeline import JsonlTimeline, Transition


MAX_HISTORY_OUTPUT_CHARS = 50_000


class TimelineHistoryReader:
    """Render validated timeline records for the agent's history tool."""

    def __init__(self, timeline: JsonlTimeline) -> None:
        self.timeline = timeline

    async def read(self, query: HistoryQuery) -> str:
        return await asyncio.to_thread(self._read_sync, query)

    def _read_sync(self, query: HistoryQuery) -> str:
        transitions = self.timeline.transitions()
        selected, selection_label, explicit_selector = self._select(
            transitions,
            query,
        )
        lines = [
            self._summary(transitions),
            f"{selection_label}; detail={query.detail}:",
        ]
        filters = self._render_filters(query)
        if filters:
            lines.append(f"filters: {filters}")
        if not selected:
            lines.append("No transitions selected.")
            return "\n".join(lines)

        entry_grids = self._entry_grids(transitions)
        prior_same_actions = self._prior_same_actions(transitions)
        prefix = "\n".join(lines)
        blocks = tuple(
            (
                transition.index,
                "\n".join(
                    self._render_transition(
                        transition,
                        query.detail,
                        entry_grid=entry_grids[
                            transition.after.levels_completed
                        ],
                        prior_same_action=prior_same_actions[transition.index],
                    )
                ),
            )
            for transition in selected
        )
        for index, block in blocks:
            if len(f"{prefix}\n{block}") > MAX_HISTORY_OUTPUT_CHARS:
                raise ValueError(
                    f"history transition #{index} exceeds the "
                    f"{MAX_HISTORY_OUTPUT_CHARS}-character output bound at "
                    f"detail={query.detail}; request detail=brief or full"
                )

        complete = "\n".join([prefix, *(block for _, block in blocks)])
        if len(complete) <= MAX_HISTORY_OUTPUT_CHARS:
            return complete
        if explicit_selector:
            raise ValueError(
                "explicit history selection exceeds the "
                f"{MAX_HISTORY_OUTPUT_CHARS}-character output bound; request "
                "fewer indices, a narrower range, or a less detailed view"
            )

        included: list[tuple[int, str]] = []
        for position in range(len(blocks) - 1, -1, -1):
            candidate = [blocks[position], *included]
            omitted = blocks[:position]
            output = self._render_capped_history(
                prefix=prefix,
                included=candidate,
                omitted=omitted,
                selected_count=len(blocks),
            )
            if len(output) > MAX_HISTORY_OUTPUT_CHARS:
                break
            included = candidate

        if not included:
            newest_index = blocks[-1][0]
            raise ValueError(
                f"history transition #{newest_index} exceeds the "
                f"{MAX_HISTORY_OUTPUT_CHARS}-character output bound at "
                f"detail={query.detail}; request detail=brief or full"
            )
        omitted = blocks[: len(blocks) - len(included)]
        return self._render_capped_history(
            prefix=prefix,
            included=included,
            omitted=omitted,
            selected_count=len(blocks),
        )

    @staticmethod
    def _render_capped_history(
        *,
        prefix: str,
        included: list[tuple[int, str]],
        omitted: tuple[tuple[int, str], ...],
        selected_count: int,
    ) -> str:
        omitted_indices = ", ".join(f"#{index}" for index, _ in omitted)
        notice = (
            f"(capped at {MAX_HISTORY_OUTPUT_CHARS} characters; rendered "
            f"{len(included)}/{selected_count} complete transitions; omitted "
            f"older selected transitions: {omitted_indices}. To inspect them, "
            "use an explicit narrower range or indices query to continue.)"
        )
        return "\n".join(
            [prefix, *(block for _, block in included), "", notice]
        )

    @classmethod
    def _select(
        cls,
        transitions: tuple[Transition, ...],
        query: HistoryQuery,
    ) -> tuple[tuple[Transition, ...], str, bool]:
        if query.indices is not None:
            selected = tuple(
                transitions[cls._resolve_index(index, len(transitions))]
                for index in query.indices
            )
            label = f"showing indices {list(query.indices)}"
            explicit_selector = True
        elif query.start is not None and query.end is not None:
            if query.end >= len(transitions):
                raise ValueError(
                    f"history range end {query.end} is out of range for "
                    f"{len(transitions)} transitions"
                )
            selected = transitions[query.start : query.end + 1]
            label = f"showing range #{query.start}..#{query.end}"
            explicit_selector = True
        else:
            selected = transitions
            label = (
                "showing filtered most-recent"
                if cls._has_filters(query)
                else "showing most-recent"
            )
            explicit_selector = False

        selected = tuple(
            transition
            for transition in selected
            if cls._matches(transition, query)
        )
        limit = query.limit
        if limit is None and query.indices is None and query.start is None:
            limit = 20
        if limit is not None:
            selected = selected[-limit:]
        if explicit_selector:
            return selected, f"{label} -> {len(selected)} steps", True
        return (
            selected,
            f"{label} {len(selected)} -> {len(selected)} steps",
            False,
        )

    @staticmethod
    def _resolve_index(index: int, count: int) -> int:
        resolved = count + index if index < 0 else index
        if resolved < 0 or resolved >= count:
            raise ValueError(
                f"history index {index} is out of range for {count} transitions"
            )
        return resolved

    @staticmethod
    def _has_filters(query: HistoryQuery) -> bool:
        return any(
            value is not None
            for value in (query.action, query.flags, query.prediction_status)
        )

    @staticmethod
    def _matches(transition: Transition, query: HistoryQuery) -> bool:
        action = GameAction.from_name(transition.action.action).value
        if query.action is not None and action != query.action:
            return False
        if (
            query.prediction_status is not None
            and transition.prediction_status != query.prediction_status
        ):
            return False
        if query.flags is None:
            return True
        return {
            "level_up": transition.level_up,
            "dead": transition.dead,
            "win": transition.win,
            "reset": action == 0,
            "mismatch": transition.prediction_status == "mismatch",
        }[query.flags]

    @staticmethod
    def _render_filters(query: HistoryQuery) -> str:
        return " ".join(
            item
            for item in (
                f"action={query.action}" if query.action is not None else "",
                f"flags={query.flags}" if query.flags is not None else "",
                (
                    f"prediction_status={query.prediction_status}"
                    if query.prediction_status is not None
                    else ""
                ),
            )
            if item
        )

    def _entry_grids(
        self, transitions: tuple[Transition, ...]
    ) -> dict[int, tuple[tuple[int, ...], ...]]:
        initial = self.timeline.initial_observation
        assert initial is not None
        entries = {initial.levels_completed: initial.grid}
        for transition in transitions:
            if transition.level_up:
                entries[transition.after.levels_completed] = transition.after.grid
        return entries

    @staticmethod
    def _prior_same_actions(
        transitions: tuple[Transition, ...],
    ) -> dict[int, tuple[int, ...]]:
        prior_by_action: dict[int, list[int]] = {}
        result: dict[int, tuple[int, ...]] = {}
        for transition in transitions:
            action = GameAction.from_name(transition.action.action).value
            prior = prior_by_action.setdefault(action, [])
            result[transition.index] = tuple(prior[-3:])
            prior.append(transition.index)
        return result

    @staticmethod
    def _summary(transitions: tuple[Transition, ...]) -> str:
        action_counts = Counter(
            GameAction.from_name(transition.action.action).value
            for transition in transitions
        )
        by_action = "{" + ", ".join(
            f"{action_id}:{action_counts[action_id]}"
            for action_id in sorted(action_counts)
        ) + "}"
        max_level = max(
            (
                max(
                    transition.before.levels_completed,
                    transition.after.levels_completed,
                )
                for transition in transitions
            ),
            default=0,
        )
        return (
            f"{len(transitions)} transitions total. Summary: "
            f"level_ups={sum(item.level_up for item in transitions)} "
            f"deaths={sum(item.dead for item in transitions)} "
            f"wins={sum(item.win for item in transitions)} "
            "model_mismatches="
            f"{sum(item.prediction_status == 'mismatch' for item in transitions)} "
            "unchecked="
            f"{sum(item.prediction_status == 'unchecked' for item in transitions)} "
            f"resets(action0)={action_counts[0]} "
            f"clicks(action6)={action_counts[6]}; "
            f"by-action={by_action}; max_level={max_level}"
        )

    def _render_transition(
        self,
        transition: Transition,
        detail: HistoryDetail,
        *,
        entry_grid: tuple[tuple[int, ...], ...],
        prior_same_action: tuple[int, ...],
    ) -> list[str]:
        transition_summary = summarize_grid_change(
            transition.before.grid,
            transition.after.grid,
        )
        entry_distance = summarize_grid_change(
            entry_grid,
            transition.after.grid,
            component_limit=0,
        ).changed_cells
        lines = [
            self._brief_line(transition),
            "  structure: "
            f"{render_grid_change_summary(transition_summary)}; "
            f"after_vs_level_entry={entry_distance} cells; "
            "prior_same_action=["
            + ", ".join(f"#{index}" for index in prior_same_action)
            + "]",
        ]
        if detail == "full":
            lines.extend(
                [
                    "before:",
                    self._render_final_frame(transition.before),
                    "after:",
                    self._render_final_frame(transition.after),
                ]
            )
        elif detail == "animation":
            if not transition.after.ticks:
                lines.append("(no animation ticks)")
            for index, grid in enumerate(transition.after.ticks):
                lines.extend(
                    [
                        f"animation tick {index}:",
                        self._render_grid(grid),
                    ]
                )
            lines.extend(
                ["after:", self._render_grid(transition.after.grid)]
            )
        return lines

    def _brief_line(self, transition: Transition) -> str:
        game_action = GameAction.from_name(transition.action.action)
        action_label = str(game_action.value)
        if game_action.is_complex():
            action_label += f"(x={transition.action.x},y={transition.action.y})"
        flags = [
            name
            for name, enabled in (
                ("level_up", transition.level_up),
                ("dead", transition.dead),
                ("win", transition.win),
            )
            if enabled
        ] or ["none"]
        return (
            f"#{transition.index} action={action_label}; "
            f"{self._changed_cells(transition.before, transition.after)}; "
            f"model={transition.prediction_status} "
            f"revision={transition.model_revision[:12]}; "
            f"state={transition.after.state.value}; "
            f"level={transition.after.levels_completed}; flags={flags}"
        )

    @classmethod
    def _changed_cells(
        cls, before: GameObservation, after: GameObservation
    ) -> str:
        if not before.grid or not after.grid:
            return "frame unavailable"
        before_grid = before.grid
        after_grid = after.grid
        if cls._shape(before_grid) != cls._shape(after_grid):
            return "frame shape changed"
        changed = sum(
            before_value != after_value
            for before_row, after_row in zip(before_grid, after_grid, strict=True)
            for before_value, after_value in zip(
                before_row, after_row, strict=True
            )
        )
        return f"{changed} cells changed"

    @classmethod
    def _render_final_frame(cls, observation: GameObservation) -> str:
        if not observation.grid:
            return "(no grid)"
        return cls._render_grid(observation.grid)

    @staticmethod
    def _shape(grid: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
        return (len(grid), *(len(row) for row in grid))

    @staticmethod
    def _render_grid(grid: tuple[tuple[int, ...], ...]) -> str:
        if not grid:
            return "shape=0x0\n(empty)"
        width = len(grid[0])
        if any(len(row) != width for row in grid):
            raise ValueError("cannot render a ragged ARC grid")
        rows = "\n".join(
            "".join(format(value, "x") for value in row) for row in grid
        )
        return f"shape={len(grid)}x{width}\n{rows}"
