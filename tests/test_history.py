import asyncio
from pathlib import Path

from arcengine import FrameData, GameState

from beat_arc_agi_3.dependencies import HistoryQuery
from beat_arc_agi_3.history import TimelineHistoryReader
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
