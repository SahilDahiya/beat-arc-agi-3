from pathlib import Path

from arcengine import GameState

from beat_arc_agi_3.evals.level_lifecycle import extract_level_lifecycle
from beat_arc_agi_3.events import (
    ActionCompletedEvent,
    BacktestCompletedEvent,
    BfsCompletedEvent,
    CommitAcceptedEvent,
    QueueCancelledEvent,
    ToolCompletedEvent,
    TurnStartedEvent,
    WorldModelInstalledEvent,
)
from beat_arc_agi_3.schemas import ArcAction, GameObservation
from beat_arc_agi_3.session import Session
from beat_arc_agi_3.timeline import ModelPredictionRecord


def observation(
    level: int,
    value: int,
    *,
    state: GameState = GameState.NOT_FINISHED,
) -> GameObservation:
    return GameObservation(
        game_id="test-game",
        grid=((value,),),
        state=state,
        levels_completed=level,
        win_levels=2,
        available_actions=(1, 6),
    )


def prediction(value: int, *, level_up: bool = False) -> ModelPredictionRecord:
    return ModelPredictionRecord(
        grid=((value,),),
        level_up=level_up,
        dead=False,
        win=False,
    )


def append_action_event(session: Session, *, turn: int, transition_index: int) -> None:
    transition = session.timeline.transitions()[transition_index]
    session.events.append(
        turn=turn,
        event=ActionCompletedEvent(
            summary=f"Completed transition {transition_index}",
            action_number=transition_index + 1,
            transition_index=transition_index,
            action=transition.action,
            model_revision=transition.model_revision,
            prediction_status=transition.prediction_status,
            state=transition.after.state,
            levels_completed=transition.after.levels_completed,
            level_up=transition.level_up,
            dead=transition.dead,
            win=transition.win,
        ),
    )


def test_level_lifecycle_reports_stage_scoped_synthesis_evidence(
    tmp_path: Path,
) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="lifecycle",
        game_id="test-game",
        model="test:model",
    )
    session.timeline.initialize(observation(0, 0))

    session.events.append(
        turn=1,
        event=TurnStartedEvent(
            summary="Turn 1",
            state=GameState.NOT_FINISHED,
            levels_completed=0,
            available_actions=("ACTION1", "ACTION6"),
        ),
    )
    first = session.timeline.append(
        action=ArcAction(action="ACTION6", x=2, y=3),
        after=observation(0, 1),
        model_revision="revision-1",
        prediction=prediction(9),
    )
    append_action_event(session, turn=1, transition_index=first.index)
    session.events.append(
        turn=1,
        event=CommitAcceptedEvent(
            summary="Accepted exploratory queue",
            actions=(
                ArcAction(action="ACTION6", x=2, y=3),
                ArcAction(action="ACTION1"),
                ArcAction(action="ACTION1"),
            ),
            reason="Probe then continue",
            suggestion="Inspect the probe",
        ),
    )
    session.events.append(
        turn=1,
        event=QueueCancelledEvent(
            summary="Prediction mismatch",
            reason="prediction_mismatch",
            committed_actions=3,
            executed_actions=1,
        ),
    )

    session.events.append(
        turn=2,
        event=TurnStartedEvent(
            summary="Turn 2",
            state=GameState.NOT_FINISHED,
            levels_completed=0,
            available_actions=("ACTION1", "ACTION6"),
        ),
    )
    session.events.append(
        turn=2,
        event=WorldModelInstalledEvent(
            summary="Installed repaired model",
            revision="revision-2",
        ),
    )
    session.events.append(
        turn=2,
        event=BacktestCompletedEvent(
            summary="Backtest green",
            revision="revision-2",
            status="green",
            timeline_transitions=1,
            exact_transitions=1,
        ),
    )
    session.events.append(
        turn=2,
        event=BfsCompletedEvent(
            summary="BFS found level-up",
            revision="revision-2",
            target="level_up",
            status="found",
            max_depth=8,
            node_budget=100,
            expanded_nodes=6,
            distinct_states=5,
            depth=1,
            actions=(ArcAction(action="ACTION1"),),
        ),
    )
    session.events.append(
        turn=2,
        event=ToolCompletedEvent(
            summary="Read history",
            tool_call_id="read-1",
            tool_name="read_history",
            duration_ms=4,
        ),
    )
    second = session.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(1, 2),
        model_revision="revision-2",
        prediction=prediction(2, level_up=True),
    )
    append_action_event(session, turn=2, transition_index=second.index)

    session.events.append(
        turn=3,
        event=TurnStartedEvent(
            summary="Turn 3",
            state=GameState.NOT_FINISHED,
            levels_completed=1,
            available_actions=("ACTION1", "ACTION6"),
        ),
    )
    third = session.timeline.append(
        action=ArcAction(action="ACTION1"),
        after=observation(1, 3),
        model_revision="revision-2",
        prediction=prediction(3),
    )
    append_action_event(session, turn=3, transition_index=third.index)

    report = extract_level_lifecycle(session)

    assert report.session_id == "lifecycle"
    assert [level.level for level in report.levels] == [0, 1]
    level_zero = report.levels[0]
    assert level_zero.entry_transition_index is None
    assert level_zero.exit_transition_index == 1
    assert level_zero.entry_turn == 1
    assert level_zero.exit_turn == 2
    assert level_zero.actions == 2
    assert level_zero.turns == 2
    assert level_zero.prediction_exact == 1
    assert level_zero.prediction_mismatch == 1
    assert level_zero.action_counts == {"ACTION1": 1, "ACTION6": 1}
    assert level_zero.action6_coordinates == ((2, 3),)
    assert level_zero.distinct_observations == 3
    assert level_zero.world_model_installs == 1
    assert level_zero.backtests_green == 1
    assert level_zero.bfs_attempts == 1
    assert level_zero.bfs_found == 1
    assert level_zero.bfs_plan_depths == (1,)
    assert level_zero.commit_queue_sizes == (3,)
    assert level_zero.queue_cancellations == {"prediction_mismatch": 1}
    assert level_zero.level_ups == 1
    assert level_zero.tool_counts == {"read_history": 1}
    assert level_zero.tool_counts_by_phase == {"grounding": 1}
    assert len(level_zero.repair_spans) == 1
    assert level_zero.repair_spans[0].mismatch_transition_index == 0
    assert level_zero.repair_spans[0].green_turn == 2

    level_one = report.levels[1]
    assert level_one.entry_transition_index == 1
    assert level_one.exit_transition_index is None
    assert level_one.actions == 1
    assert level_one.prediction_exact == 1


def test_level_lifecycle_includes_an_observed_level_before_any_action(
    tmp_path: Path,
) -> None:
    session = Session.create(
        sessions_root=tmp_path,
        session_id="empty-level",
        game_id="test-game",
        model="test:model",
    )
    session.timeline.initialize(observation(0, 7))

    report = extract_level_lifecycle(session)

    assert len(report.levels) == 1
    level = report.levels[0]
    assert level.level == 0
    assert level.actions == 0
    assert level.turns == 0
    assert level.distinct_observations == 1
