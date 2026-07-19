from pathlib import Path

from arcengine import FrameData, GameState

from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.strategy import render_experiment_context
from beat_arc_agi_3.timeline import JsonlTimeline, ModelPredictionRecord


def observation(value: int, *, levels_completed: int = 0) -> GameObservation:
    return GameObservation.from_frame(
        FrameData(
            game_id="test-game",
            frame=[[[value]]],
            state=GameState.NOT_FINISHED,
            levels_completed=levels_completed,
            win_levels=2,
            available_actions=[1, 2],
        )
    )


def prediction(
    value: int,
    *,
    level_up: bool = False,
) -> ModelPredictionRecord:
    return ModelPredictionRecord(
        grid=((value,),),
        level_up=level_up,
        dead=False,
        win=False,
    )


def test_experiment_context_exposes_counterexample_and_observable_cycle(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))
    timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(1),
        model_revision="test-revision",
        prediction=prediction(1),
    )
    timeline.append(
        action=ArcAction(action="ACTION2"),
        after=observation(0),
        model_revision="test-revision",
        prediction=prediction(9),
    )

    context = render_experiment_context(timeline)

    assert "online predictions exact=1/2" in context
    assert "recent prediction mismatches=1/2" in context
    assert "actions without level progress=2" in context
    assert "current observable state visits=2" in context
    assert "recent actions=ACTION1,ACTION2" in context
    assert "nearest recent prior observation differs=0/1 cells" in context
    assert "action distance=2" in context
    assert "observable-state cycle length=2" in context
    assert "transition #1 is the latest counterexample" in context
    assert "Do not patch by transition index or action occurrence count" in context
    assert "use a known-safe modeled prefix" in context
    assert "put the uncertain action last" in context


def test_experiment_context_resets_stagnation_after_level_progress(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))
    timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(1),
        model_revision="test-revision",
        prediction=prediction(1),
    )
    timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(2, levels_completed=1),
        model_revision="test-revision",
        prediction=prediction(2, level_up=True),
    )

    context = render_experiment_context(timeline)

    assert "online predictions exact=2/2" in context
    assert "actions without level progress=0" in context
    assert "current observable state visits=1" in context
    assert "observable-state cycle" not in context


def test_unchecked_action_is_not_counted_as_a_failed_model_prediction(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))
    timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(9),
        model_revision="test-revision",
        prediction=None,
    )

    context = render_experiment_context(timeline)

    assert "online predictions exact=0/0" in context
    assert "unchecked exploratory transitions=1" in context
