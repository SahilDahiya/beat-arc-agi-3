import asyncio
from collections import Counter

from arcengine import GameAction

from beat_arc_agi_3.dependencies import HistoryDetail, HistoryQuery
from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.timeline import JsonlTimeline, Transition


class TimelineHistoryReader:
    """Render validated timeline records for the agent's history tool."""

    def __init__(self, timeline: JsonlTimeline) -> None:
        self.timeline = timeline

    async def read(self, query: HistoryQuery) -> str:
        return await asyncio.to_thread(self._read_sync, query)

    def _read_sync(self, query: HistoryQuery) -> str:
        transitions = self.timeline.transitions()
        selected = transitions[-query.limit :]
        lines = [self._summary(transitions)]
        if not selected:
            lines.append("No transitions selected.")
            return "\n".join(lines)

        lines.append(
            f"showing most-recent {len(selected)} -> {len(selected)} steps; "
            f"detail={query.detail}:"
        )
        for transition in selected:
            lines.extend(self._render_transition(transition, query.detail))
        return "\n".join(lines)

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
        self, transition: Transition, detail: HistoryDetail
    ) -> list[str]:
        lines = [self._brief_line(transition)]
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
