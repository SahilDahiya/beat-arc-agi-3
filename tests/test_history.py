import asyncio
from pathlib import Path

import pytest
from arcengine import FrameData, GameState
from pydantic import ValidationError

from beat_arc_agi_3.dependencies import HistoryQuery
from beat_arc_agi_3.grid_analysis import summarize_grid_change
from beat_arc_agi_3.history import MAX_HISTORY_OUTPUT_CHARS, TimelineHistoryReader
from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.timeline import JsonlTimeline, ModelPredictionRecord


def observation(
    *values: int,
    state: GameState = GameState.NOT_FINISHED,
    levels_completed: int = 0,
) -> GameObservation:
    return GameObservation.from_frame(
        FrameData(
            game_id="test-game",
            frame=[[[value]] for value in values],
            state=state,
            levels_completed=levels_completed,
            win_levels=2,
            available_actions=[1, 6],
        )
    )


def simple_action() -> ArcAction:
    return ArcAction(action="ACTION1")


def click_action() -> ArcAction:
    return ArcAction(action="ACTION6", x=3, y=7)


def reset_action() -> ArcAction:
    return ArcAction(action="RESET")


def prediction(
    value: int,
    *,
    level_up: bool = False,
    win: bool = False,
) -> ModelPredictionRecord:
    return ModelPredictionRecord(
        grid=((value,),),
        level_up=level_up,
        dead=False,
        win=win,
    )


def populated_timeline(path: Path) -> JsonlTimeline:
    timeline = JsonlTimeline.create(path, game_id="test-game")
    start = observation(0)
    one = observation(1)
    two = observation(2, 3, levels_completed=1)
    end = observation(4, state=GameState.WIN, levels_completed=1)
    timeline.initialize(start)
    timeline.append(
        action=simple_action(),
        after=one,
        model_revision="test-revision",
        prediction=prediction(9),
    )
    timeline.append(
        action=click_action(),
        after=two,
        model_revision="test-revision",
        prediction=prediction(9, level_up=True),
    )
    timeline.append(
        action=simple_action(),
        after=end,
        model_revision="test-revision",
        prediction=prediction(4, win=True),
    )
    return timeline


def large_observation(
    value: int,
    *,
    ticks: tuple[tuple[tuple[int, ...], ...], ...] = (),
) -> GameObservation:
    grid = tuple(tuple(value for _ in range(64)) for _ in range(64))
    return GameObservation(
        game_id="test-game",
        grid=grid,
        ticks=ticks,
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        win_levels=2,
        available_actions=(1, 6),
    )


def large_timeline(path: Path, *, transitions: int = 8) -> JsonlTimeline:
    timeline = JsonlTimeline.create(path, game_id="test-game")
    timeline.initialize(large_observation(0))
    for index in range(transitions):
        timeline.append(
            action=simple_action(),
            after=large_observation((index + 1) % 16),
            model_revision="large-revision",
            prediction=None,
        )
    return timeline


def test_brief_history_summarizes_all_and_limits_selected_steps(
    tmp_path: Path,
) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(reader.read(HistoryQuery(detail="brief", limit=2)))

    assert "3 transitions total" in output
    assert "level_ups=1 deaths=0 wins=1" in output
    assert "model_mismatches=1 unchecked=0" in output
    assert "by-action={1:2, 6:1}" in output
    assert "showing most-recent 2 -> 2 steps" in output
    assert "#0 action=1" not in output
    assert (
        "#1 action=6(x=3,y=7); 1 cells changed; "
        "model=exact revision=test-revisi"
    ) in output
    assert (
        "#2 action=1; 1 cells changed; model=exact revision=test-revisi"
    ) in output


def test_full_history_renders_before_and_after_grids(tmp_path: Path) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(reader.read(HistoryQuery(detail="full", limit=1)))

    assert "#2 action=1" in output
    assert "before:\nshape=1x1\n3" in output
    assert "after:\nshape=1x1\n4" in output


def test_animation_history_preserves_intermediate_frames(tmp_path: Path) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(reader.read(HistoryQuery(detail="animation", limit=2)))

    assert "#1 action=6(x=3,y=7)" in output
    assert "animation tick 0:\nshape=1x1\n2" in output
    assert "after:\nshape=1x1\n3" in output


def test_recent_full_history_keeps_newest_complete_transitions_within_bound(
    tmp_path: Path,
) -> None:
    reader = TimelineHistoryReader(large_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(reader.read(HistoryQuery(detail="full", limit=8)))

    assert len(output) <= MAX_HISTORY_OUTPUT_CHARS
    assert "#7 action=1" in output
    assert "#0 action=1" not in output
    assert "omitted older selected transitions:" in output
    assert "use an explicit narrower range or indices query to continue" in output
    assert output.count("before:\nshape=64x64") == output.count(
        "after:\nshape=64x64"
    )


def test_explicit_full_history_fails_instead_of_returning_partial_selection(
    tmp_path: Path,
) -> None:
    reader = TimelineHistoryReader(large_timeline(tmp_path / "timeline.jsonl"))

    with pytest.raises(
        ValueError,
        match="explicit history selection exceeds the 50000-character output bound",
    ):
        asyncio.run(
            reader.read(HistoryQuery(detail="full", start=0, end=7))
        )


def test_history_rejects_one_transition_larger_than_the_output_bound(
    tmp_path: Path,
) -> None:
    grids = tuple(
        tuple(tuple(value for _ in range(64)) for _ in range(64))
        for value in range(16)
    )
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(large_observation(0))
    timeline.append(
        action=simple_action(),
        after=large_observation(1, ticks=grids),
        model_revision="large-revision",
        prediction=None,
    )
    reader = TimelineHistoryReader(timeline)

    with pytest.raises(
        ValueError,
        match="transition #0 exceeds the 50000-character output bound",
    ):
        asyncio.run(
            reader.read(HistoryQuery(detail="animation", indices=(0,)))
        )


def test_empty_history_is_explicit(tmp_path: Path) -> None:
    reader = TimelineHistoryReader(
        JsonlTimeline.create(
            tmp_path / "timeline.jsonl", game_id="test-game"
        )
    )

    output = asyncio.run(reader.read(HistoryQuery()))

    assert "0 transitions total" in output
    assert output.endswith("No transitions selected.")


def test_history_labels_an_unchecked_action_without_a_prediction(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))
    timeline.append(
        action=simple_action(),
        after=observation(7),
        model_revision="unchecked-revision",
        prediction=None,
    )

    output = asyncio.run(
        TimelineHistoryReader(timeline).read(HistoryQuery(detail="brief"))
    )

    assert "model_mismatches=0 unchecked=1" in output
    assert "model=unchecked revision=unchecked-re" in output


def test_history_selects_exact_indices_including_negative_indices(
    tmp_path: Path,
) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(
        reader.read(HistoryQuery(detail="brief", indices=(0, -1)))
    )

    assert "showing indices [0, -1] -> 2 steps" in output
    assert "#0 action=1" in output
    assert "#1 action=6" not in output
    assert "#2 action=1" in output


def test_history_selects_an_inclusive_range_and_combines_filters(
    tmp_path: Path,
) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(
        reader.read(
            HistoryQuery(
                detail="brief",
                start=0,
                end=2,
                action=6,
                flags="level_up",
                prediction_status="exact",
            )
        )
    )

    assert "showing range #0..#2 -> 1 steps" in output
    assert "filters: action=6 flags=level_up prediction_status=exact" in output
    assert "#0 action=1" not in output
    assert "#1 action=6(x=3,y=7)" in output
    assert "#2 action=1" not in output


def test_history_filters_model_mismatches(tmp_path: Path) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(
        reader.read(
            HistoryQuery(detail="brief", prediction_status="mismatch")
        )
    )

    assert "showing filtered most-recent 1 -> 1 steps" in output
    assert "filters: prediction_status=mismatch" in output
    assert "#0 action=1" in output
    assert "#1 action=6" not in output


def test_history_filters_reset_and_death_facts(tmp_path: Path) -> None:
    reset_timeline = JsonlTimeline.create(
        tmp_path / "reset.jsonl", game_id="test-game"
    )
    reset_timeline.initialize(observation(0))
    reset_timeline.append(
        action=reset_action(),
        after=observation(0),
        model_revision="reset-revision",
        prediction=None,
    )
    reset_output = asyncio.run(
        TimelineHistoryReader(reset_timeline).read(
            HistoryQuery(detail="brief", flags="reset")
        )
    )

    dead_timeline = JsonlTimeline.create(
        tmp_path / "dead.jsonl", game_id="test-game"
    )
    dead_timeline.initialize(observation(0))
    dead_timeline.append(
        action=simple_action(),
        after=observation(9, state=GameState.GAME_OVER),
        model_revision="dead-revision",
        prediction=None,
    )
    dead_output = asyncio.run(
        TimelineHistoryReader(dead_timeline).read(
            HistoryQuery(detail="brief", flags="dead")
        )
    )

    assert "filters: flags=reset" in reset_output
    assert "#0 action=0" in reset_output
    assert "filters: flags=dead" in dead_output
    assert "flags=['dead']" in dead_output


def test_empty_filtered_history_echoes_the_selection(tmp_path: Path) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(
        reader.read(HistoryQuery(detail="brief", action=7))
    )

    assert "showing filtered most-recent 0 -> 0 steps" in output
    assert "filters: action=7" in output
    assert output.endswith("No transitions selected.")


def test_history_query_rejects_ambiguous_or_invalid_selectors() -> None:
    with pytest.raises(ValidationError, match="indices cannot be combined"):
        HistoryQuery(indices=(0,), start=0, end=1)
    with pytest.raises(ValidationError, match="start and end must be provided together"):
        HistoryQuery(start=0)
    with pytest.raises(ValidationError, match="end must be greater than or equal to start"):
        HistoryQuery(start=2, end=1)


def test_history_fails_hard_for_an_out_of_range_exact_index(
    tmp_path: Path,
) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    with pytest.raises(ValueError, match="history index 3 is out of range"):
        asyncio.run(reader.read(HistoryQuery(indices=(3,))))


def test_structural_change_summary_reports_components_colors_and_edges() -> None:
    before = (
        (0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0),
    )
    after = (
        (0, 0, 0, 0, 0),
        (0, 2, 2, 0, 0),
        (0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0),
        (0, 0, 0, 0, 3),
    )

    summary = summarize_grid_change(before, after)

    assert summary.changed_cells == 3
    assert summary.component_count == 2
    assert [item.model_dump() for item in summary.components] == [
        {
            "cells": 2,
            "top": 1,
            "left": 1,
            "bottom": 1,
            "right": 2,
            "touches_edge": False,
        },
        {
            "cells": 1,
            "top": 4,
            "left": 4,
            "bottom": 4,
            "right": 4,
            "touches_edge": True,
        },
    ]
    assert [item.model_dump() for item in summary.color_transitions] == [
        {"before": 0, "after": 2, "cells": 2},
        {"before": 0, "after": 3, "cells": 1},
    ]
    assert [item.model_dump() for item in summary.color_count_changes] == [
        {"color": 0, "before": 25, "after": 22, "delta": -3},
        {"color": 2, "before": 0, "after": 2, "delta": 2},
        {"color": 3, "before": 0, "after": 1, "delta": 1},
    ]
    assert summary.edge_changed_cells == 1
    assert summary.peripheral_band_width == 1
    assert summary.peripheral_changed_cells == 1
    assert summary.interior_changed_cells == 2


def test_brief_history_includes_structural_and_level_entry_distance(
    tmp_path: Path,
) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(
        reader.read(HistoryQuery(detail="brief", indices=(1,)))
    )

    assert "structure: cells=1 components=1" in output
    assert "bboxes=[(0,0)-(0,0):1:edge]" in output
    assert "colors=[1->3:1]" in output
    assert "color_counts=[1:1->0(-1), 3:0->1(+1)]" in output
    assert "edge_changed=1" in output
    assert "peripheral_band=1 peripheral_changed=1 interior_changed=0" in output
    assert "after_vs_level_entry=0 cells" in output
    assert "prior_same_action=[]" in output


def test_history_points_to_prior_transitions_with_the_same_action(
    tmp_path: Path,
) -> None:
    reader = TimelineHistoryReader(populated_timeline(tmp_path / "timeline.jsonl"))

    output = asyncio.run(
        reader.read(HistoryQuery(detail="brief", indices=(2,)))
    )

    assert "prior_same_action=[#0]" in output
