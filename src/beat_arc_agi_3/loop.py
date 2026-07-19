import asyncio
from typing import Literal

from arcengine import GameState
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.dependencies import AgentDeps
from beat_arc_agi_3.events import (
    ActionCompletedEvent,
    ActionStartedEvent,
    PredictionMismatchEvent,
    QueueCancelledEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunInterruptedEvent,
    TurnCompletedEvent,
    TurnStartedEvent,
)
from beat_arc_agi_3.history import TimelineHistoryReader
from beat_arc_agi_3.runner import deliberate
from beat_arc_agi_3.schemas import CommitActions, GameObservation
from beat_arc_agi_3.session import Session
from beat_arc_agi_3.strategy import render_experiment_context


StopReason = Literal["win", "max_actions", "max_turns", "no_legal_actions"]


class LoopPolicy(BaseModel):
    """Explicit bounds for one ARC agent process."""

    model_config = ConfigDict(frozen=True)

    max_turns: int = Field(ge=1)
    max_actions: int = Field(ge=1)


class LoopResult(BaseModel):
    """Terminal accounting for one bounded loop run."""

    model_config = ConfigDict(frozen=True)

    stop_reason: StopReason
    turns: int = Field(ge=0)
    actions: int = Field(ge=0)
    observation: GameObservation


async def run_agent_loop(
    *,
    agent: Agent[AgentDeps, CommitActions],
    adapter: ArcGameAdapter,
    initial_observation: GameObservation,
    session: Session,
    policy: LoopPolicy,
) -> LoopResult:
    """Observe, deliberate, execute, and record under explicit process bounds."""

    if session.timeline.initial_observation is not None:
        raise ValueError("agent loop requires a new, uninitialized session")
    if session.conversation.messages():
        raise ValueError("agent loop requires an empty session conversation")

    current = initial_observation
    if current.game_id != session.metadata.game_id:
        raise ValueError(
            f"environment game {current.game_id} does not match "
            f"session game {session.metadata.game_id}"
        )
    session.timeline.initialize(current)

    turns = 0
    active_turn = 0
    actions_taken = 0
    turn_context = (
        "This is the initial observation for the session.\n"
        f"{render_experiment_context(session.timeline)}"
    )
    history = TimelineHistoryReader(session.timeline)

    def complete(stop_reason: StopReason) -> LoopResult:
        session.events.append(
            turn=turns,
            event=RunCompletedEvent(
                summary=(
                    f"Run stopped: {stop_reason}; {turns} turn(s), "
                    f"{actions_taken} action(s)"
                ),
                stop_reason=stop_reason,
                turns=turns,
                actions=actions_taken,
                state=current.state,
                levels_completed=current.levels_completed,
                win_levels=current.win_levels,
            ),
        )
        return LoopResult(
            stop_reason=stop_reason,
            turns=turns,
            actions=actions_taken,
            observation=current,
        )

    try:
        while True:
            if current.state is GameState.WIN:
                return complete("win")
            if actions_taken >= policy.max_actions:
                return complete("max_actions")
            if turns >= policy.max_turns:
                return complete("max_turns")
            if not current.available_actions:
                return complete("no_legal_actions")

            turn_number = turns + 1
            active_turn = turn_number
            session.events.append(
                turn=turn_number,
                event=TurnStartedEvent(
                    summary=(
                        f"Turn {turn_number} started at level "
                        f"{current.levels_completed} in {current.state.value}"
                    ),
                    state=current.state,
                    levels_completed=current.levels_completed,
                    available_actions=current.available_action_names,
                ),
            )
            commit = await deliberate(
                agent,
                AgentDeps(
                    observation=current,
                    history=history,
                    workspace=session.workspace,
                    synthesis=session.synthesis,
                    events=session.events,
                    turn=turn_number,
                ),
                session.conversation,
                turn_context=turn_context,
            )
            turns = turn_number
            committed_count = len(commit.actions)
            executed_count = 0
            queue_stop = "the committed queue completed"
            queue_cancel_reason: (
                Literal[
                    "max_actions",
                    "illegal_action",
                    "prediction_mismatch",
                    "level_up",
                    "game_over",
                    "win",
                ]
                | None
            ) = None
            turn_start = current

            for action in commit.actions:
                if actions_taken >= policy.max_actions:
                    queue_stop = "the action budget was exhausted"
                    queue_cancel_reason = "max_actions"
                    break
                if action.action not in adapter.available_actions:
                    queue_stop = (
                        f"{action.action} was no longer legal; remaining "
                        "actions were dropped"
                    )
                    queue_cancel_reason = "illegal_action"
                    break

                pending_prediction = session.synthesis.predict_action(action)
                transition_index = len(session.timeline.transitions())
                action_number = actions_taken + 1
                session.events.append(
                    turn=turns,
                    event=ActionStartedEvent(
                        summary=(
                            f"Executing action {action_number}: "
                            f"{action.action}"
                        ),
                        action_number=action_number,
                        transition_index=transition_index,
                        action=action,
                        prediction_revision=pending_prediction.revision,
                    ),
                )
                after = adapter.apply(action)
                transition = session.timeline.append(
                    action=action,
                    after=after,
                    prediction=pending_prediction.record,
                )
                prediction_matched = session.synthesis.observe(
                    pending_prediction,
                    transition,
                )
                current = after
                executed_count += 1
                actions_taken += 1
                session.events.append(
                    turn=turns,
                    event=ActionCompletedEvent(
                        summary=(
                            f"Action {action_number} completed as transition "
                            f"{transition.index}; prediction "
                            f"{'exact' if prediction_matched else 'mismatched'}"
                        ),
                        action_number=action_number,
                        transition_index=transition.index,
                        action=action,
                        prediction_revision=pending_prediction.revision,
                        prediction_exact=prediction_matched,
                        state=current.state,
                        levels_completed=current.levels_completed,
                        level_up=transition.level_up,
                        dead=transition.dead,
                        win=transition.win,
                    ),
                )

                if transition.win:
                    queue_stop = "the game reached WIN"
                    queue_cancel_reason = "win"
                    break
                if not prediction_matched:
                    session.events.append(
                        turn=turns,
                        event=PredictionMismatchEvent(
                            summary=(
                                f"World model revision "
                                f"{pending_prediction.revision[:12]} "
                                f"mispredicted transition {transition.index}"
                            ),
                            transition_index=transition.index,
                            revision=pending_prediction.revision,
                        ),
                    )
                    queue_stop = (
                        f"world model revision "
                        f"{pending_prediction.revision[:12]} mispredicted "
                        f"transition {transition.index}; remaining actions "
                        "were dropped"
                    )
                    queue_cancel_reason = "prediction_mismatch"
                    break
                if transition.level_up:
                    queue_stop = (
                        "a level was completed; remaining actions were dropped"
                    )
                    queue_cancel_reason = "level_up"
                    break
                if transition.dead:
                    queue_stop = (
                        "the game entered GAME_OVER; remaining actions were "
                        "dropped"
                    )
                    queue_cancel_reason = "game_over"
                    break

            if queue_cancel_reason is not None:
                session.events.append(
                    turn=turns,
                    event=QueueCancelledEvent(
                        summary=f"Committed queue stopped: {queue_stop}",
                        reason=queue_cancel_reason,
                        committed_actions=committed_count,
                        executed_actions=executed_count,
                    ),
                )
            session.events.append(
                turn=turns,
                event=TurnCompletedEvent(
                    summary=(
                        f"Turn {turns} completed: executed {executed_count}/"
                        f"{committed_count} committed action(s)"
                    ),
                    committed_actions=committed_count,
                    executed_actions=executed_count,
                    queue_stop=queue_stop,
                ),
            )

            turn_context = (
                f"Previous commit queued {committed_count} action(s) and "
                f"executed {executed_count}; stopped because {queue_stop}. "
                f"Level {turn_start.levels_completed}→"
                f"{current.levels_completed}; state "
                f"{turn_start.state.value}→{current.state.value}. "
                f"The previous intent was: {commit.reason}"
                f"\n{render_experiment_context(session.timeline)}"
            )
    except (KeyboardInterrupt, asyncio.CancelledError) as exc:
        message = str(exc).strip() or "run interrupted"
        session.events.append(
            turn=active_turn,
            event=RunInterruptedEvent(
                summary="Run interrupted",
                error_type=type(exc).__name__,
                message=message,
            ),
        )
        raise
    except Exception as exc:
        message = str(exc).strip() or type(exc).__name__
        session.events.append(
            turn=active_turn,
            event=RunFailedEvent(
                summary=f"Run failed: {type(exc).__name__}",
                error_type=type(exc).__name__,
                message=message[:2000],
            ),
        )
        raise
