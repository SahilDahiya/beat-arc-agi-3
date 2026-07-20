from pathlib import Path

import pytest
from arcengine import FrameData, GameState

from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.strategy import (
    render_current_level_evidence,
    render_experiment_context,
    render_strategy_context,
)
from beat_arc_agi_3.events import (
    BacktestCompletedEvent,
    BfsCompletedEvent,
    EventJournal,
    TurnStartedEvent,
    WorldModelInstalledEvent,
)
from beat_arc_agi_3.timeline import JsonlTimeline, ModelPredictionRecord


def observation(
    value: int,
    *,
    levels_completed: int = 0,
    grid: list[list[int]] | None = None,
) -> GameObservation:
    return GameObservation.from_frame(
        FrameData(
            game_id="test-game",
            frame=[grid or [[value]]],
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


def test_strategy_context_grounds_the_initial_level_entry(tmp_path: Path) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(
        observation(
            0,
            grid=[
                [0, 0, 0],
                [0, 1, 0],
                [2, 2, 2],
            ],
        )
    )

    context = render_strategy_context(
        timeline,
        EventJournal.create(tmp_path / "events.jsonl", session_id="test"),
    )

    assert "Level-entry grounding protocol" in context
    assert "trigger=session_start; level=0/2" in context
    assert "entry grid shape=3x3; color counts=0:5,1:1,2:3" in context
    assert "geometric peripheral band width=1" in context
    assert "peripheral color counts=0:5,2:3" in context
    assert "interior color counts=1:1" in context
    assert "legal actions=ACTION1,ACTION2" in context
    assert "Observed facts" in context
    assert "Hypotheses" in context
    assert "Known unknowns" in context
    assert "Cheapest discriminating probe" in context
    assert "Temporary goal" in context
    assert "predicate, evidence, and falsifier" in context
    assert "Decision mode" in context
    assert "goal_search" in context
    assert "discriminating_experiment" in context
    assert "Harness experiment evidence" in context


def test_strategy_context_repeats_grounding_only_at_real_level_entry(
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

    events = EventJournal.create(
        tmp_path / "events.jsonl", session_id="test"
    )
    assert "Level-entry grounding protocol" not in render_strategy_context(
        timeline, events
    )

    timeline.append(
        action=ArcAction(action="ACTION2"),
        after=observation(2, levels_completed=1),
        model_revision="test-revision",
        prediction=prediction(2, level_up=True),
    )

    context = render_strategy_context(timeline, events)

    assert "Level-entry grounding protocol" in context
    assert "trigger=transition #1 level_up; level=1/2" in context


def test_current_level_evidence_separates_replay_green_from_online_support(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))
    timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(1, levels_completed=1),
        model_revision="revision-1",
        prediction=prediction(1, level_up=True),
    )
    timeline.append(
        action=ArcAction(action="ACTION6", x=4, y=5),
        after=observation(9, levels_completed=1),
        model_revision="revision-2",
        prediction=prediction(3),
    )
    events = EventJournal.create(
        tmp_path / "events.jsonl", session_id="test"
    )
    events.append(
        turn=2,
        event=TurnStartedEvent(
            summary="Turn 2",
            state=GameState.NOT_FINISHED,
            levels_completed=1,
            available_actions=("ACTION1", "ACTION2"),
        ),
    )
    events.append(
        turn=2,
        event=WorldModelInstalledEvent(
            summary="Installed revision 3",
            revision="revision-3",
        ),
    )
    events.append(
        turn=2,
        event=BacktestCompletedEvent(
            summary="Full replay green",
            revision="revision-3",
            status="green",
            timeline_transitions=2,
            exact_transitions=2,
        ),
    )
    events.append(
        turn=2,
        event=BfsCompletedEvent(
            summary="Search exhausted",
            revision="revision-3",
            target="is_goal",
            status="exhausted",
            max_depth=8,
            node_budget=100,
            expanded_nodes=100,
            distinct_states=70,
            depth=None,
            actions=(),
        ),
    )

    context = render_current_level_evidence(timeline, events)

    assert "Current-level evidence: level=1" in context
    assert "transitions=1; exact=0; mismatch=1; unchecked=0" in context
    assert "actions=ACTION6:1; ACTION6 coordinates=(4,5)" in context
    assert "active revision=revision-3; full replay=current-prefix-green" in context
    assert "active-revision online support exact=0; mismatch=0; unchecked=0" in context
    assert "no online transition support on the current level" in context
    assert "latest current-level mismatch=transition #1 revision revision-2" in context
    assert "BFS attempts=1; found=0; exhausted=1" in context


def test_current_level_evidence_reports_zero_at_session_and_level_entry(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))
    events = EventJournal.create(
        tmp_path / "events.jsonl", session_id="test"
    )

    initial = render_current_level_evidence(timeline, events)

    assert "Current-level evidence: level=0" in initial
    assert "transitions=0; exact=0; mismatch=0; unchecked=0" in initial

    timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(1, levels_completed=1),
        model_revision="revision-1",
        prediction=prediction(1, level_up=True),
    )

    entered = render_current_level_evidence(timeline, events)

    assert "Current-level evidence: level=1" in entered
    assert "transitions=0; exact=0; mismatch=0; unchecked=0" in entered


def test_current_level_evidence_keeps_death_and_reset_on_the_same_level(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    timeline.initialize(observation(0))
    game_over = GameObservation.from_frame(
        FrameData(
            game_id="test-game",
            frame=[[[9]]],
            state=GameState.GAME_OVER,
            levels_completed=0,
            win_levels=2,
            available_actions=[1, 2],
        )
    )
    timeline.append(
        action=ArcAction(action="ACTION1"),
        after=game_over,
        model_revision="revision-1",
        prediction=None,
    )
    timeline.append(
        action=ArcAction(action="RESET"),
        after=observation(0),
        model_revision="revision-1",
        prediction=None,
    )
    events = EventJournal.create(
        tmp_path / "events.jsonl", session_id="test"
    )

    context = render_current_level_evidence(timeline, events)

    assert "Current-level evidence: level=0" in context
    assert "transitions=2; exact=0; mismatch=0; unchecked=2" in context
    assert "actions=ACTION1:1,RESET:1" in context


def test_current_level_evidence_rejects_an_uninitialized_timeline(
    tmp_path: Path,
) -> None:
    timeline = JsonlTimeline.create(
        tmp_path / "timeline.jsonl",
        game_id="test-game",
    )
    events = EventJournal.create(
        tmp_path / "events.jsonl", session_id="test"
    )

    with pytest.raises(ValueError, match="initialized Timeline"):
        render_current_level_evidence(timeline, events)
