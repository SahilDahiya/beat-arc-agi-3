from collections import Counter, deque

from pydantic import BaseModel, ConfigDict, Field

from beat_arc_agi_3.schemas import Grid


class ChangeComponent(BaseModel):
    """One four-connected component of exact changed-cell coordinates."""

    model_config = ConfigDict(frozen=True)

    cells: int = Field(ge=1)
    top: int = Field(ge=0)
    left: int = Field(ge=0)
    bottom: int = Field(ge=0)
    right: int = Field(ge=0)
    touches_edge: bool


class ColorTransition(BaseModel):
    """Count of changed cells sharing one exact before/after value pair."""

    model_config = ConfigDict(frozen=True)

    before: int | None
    after: int | None
    cells: int = Field(ge=1)


class ColorCountChange(BaseModel):
    """One global color population whose count changed between grids."""

    model_config = ConfigDict(frozen=True)

    color: int = Field(ge=0, le=15)
    before: int = Field(ge=0)
    after: int = Field(ge=0)
    delta: int


class GridChangeSummary(BaseModel):
    """Bounded structural facts about the difference between two grids."""

    model_config = ConfigDict(frozen=True)

    changed_cells: int = Field(ge=0)
    component_count: int = Field(ge=0)
    components: tuple[ChangeComponent, ...]
    color_transitions: tuple[ColorTransition, ...]
    color_count_changes: tuple[ColorCountChange, ...]
    edge_changed_cells: int = Field(ge=0)
    peripheral_band_width: int = Field(ge=0)
    peripheral_changed_cells: int = Field(ge=0)
    interior_changed_cells: int = Field(ge=0)


def summarize_grid_change(
    before: Grid,
    after: Grid,
    *,
    component_limit: int = 12,
) -> GridChangeSummary:
    """Return deterministic spatial facts without assigning game semantics."""

    if component_limit < 0:
        raise ValueError("component_limit must be non-negative")

    height = max(len(before), len(after))
    width = max(
        max((len(row) for row in before), default=0),
        max((len(row) for row in after), default=0),
    )
    changes: dict[tuple[int, int], tuple[int | None, int | None]] = {}
    for row in range(height):
        before_row = before[row] if row < len(before) else ()
        after_row = after[row] if row < len(after) else ()
        row_width = max(len(before_row), len(after_row))
        for column in range(row_width):
            before_value = (
                before_row[column] if column < len(before_row) else None
            )
            after_value = (
                after_row[column] if column < len(after_row) else None
            )
            if before_value != after_value:
                changes[(row, column)] = (before_value, after_value)

    remaining = set(changes)
    components: list[ChangeComponent] = []
    edge_changed_cells = 0
    peripheral_band_width = (
        max(1, (min(height, width) + 9) // 10)
        if height > 0 and width > 0
        else 0
    )
    peripheral_changed_cells = sum(
        row < peripheral_band_width
        or column < peripheral_band_width
        or row >= height - peripheral_band_width
        or column >= width - peripheral_band_width
        for row, column in changes
    )
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        queue = deque([seed])
        coordinates: list[tuple[int, int]] = []
        while queue:
            row, column = queue.popleft()
            coordinates.append((row, column))
            for neighbor in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)

        rows = [item[0] for item in coordinates]
        columns = [item[1] for item in coordinates]
        edge_cells = sum(
            row == 0
            or column == 0
            or row == height - 1
            or column == width - 1
            for row, column in coordinates
        )
        edge_changed_cells += edge_cells
        components.append(
            ChangeComponent(
                cells=len(coordinates),
                top=min(rows),
                left=min(columns),
                bottom=max(rows),
                right=max(columns),
                touches_edge=edge_cells > 0,
            )
        )

    color_counts = Counter(changes.values())
    color_transitions = tuple(
        ColorTransition(before=pair[0], after=pair[1], cells=count)
        for pair, count in sorted(
            color_counts.items(),
            key=lambda item: (
                -1 if item[0][0] is None else item[0][0],
                -1 if item[0][1] is None else item[0][1],
            ),
        )
    )
    before_counts = Counter(value for row in before for value in row)
    after_counts = Counter(value for row in after for value in row)
    color_count_changes = tuple(
        ColorCountChange(
            color=color,
            before=before_counts[color],
            after=after_counts[color],
            delta=after_counts[color] - before_counts[color],
        )
        for color in sorted(before_counts.keys() | after_counts.keys())
        if before_counts[color] != after_counts[color]
    )
    return GridChangeSummary(
        changed_cells=len(changes),
        component_count=len(components),
        components=tuple(components[:component_limit]),
        color_transitions=color_transitions,
        color_count_changes=color_count_changes,
        edge_changed_cells=edge_changed_cells,
        peripheral_band_width=peripheral_band_width,
        peripheral_changed_cells=peripheral_changed_cells,
        interior_changed_cells=len(changes) - peripheral_changed_cells,
    )


def render_grid_change_summary(summary: GridChangeSummary) -> str:
    """Render a compact, stable form suitable for model-facing evidence."""

    boxes = [
        f"({item.top},{item.left})-({item.bottom},{item.right}):"
        f"{item.cells}{':edge' if item.touches_edge else ''}"
        for item in summary.components
    ]
    if len(summary.components) < summary.component_count:
        boxes.append(
            f"+{summary.component_count - len(summary.components)} more"
        )
    colors = [
        f"{_render_color(item.before)}->{_render_color(item.after)}:"
        f"{item.cells}"
        for item in summary.color_transitions
    ]
    color_counts = [
        f"{item.color}:{item.before}->{item.after}({item.delta:+d})"
        for item in summary.color_count_changes
    ]
    return (
        f"cells={summary.changed_cells} "
        f"components={summary.component_count} "
        f"bboxes=[{', '.join(boxes)}] "
        f"colors=[{', '.join(colors)}] "
        f"color_counts=[{', '.join(color_counts)}] "
        f"edge_changed={summary.edge_changed_cells} "
        f"peripheral_band={summary.peripheral_band_width} "
        f"peripheral_changed={summary.peripheral_changed_cells} "
        f"interior_changed={summary.interior_changed_cells}"
    )


def _render_color(value: int | None) -> str:
    return "missing" if value is None else str(value)
