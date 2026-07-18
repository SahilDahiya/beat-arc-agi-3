from typing import Literal

from arcengine import GameState
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.dependencies import AgentDeps
from beat_arc_agi_3.history import TimelineHistoryReader
from beat_arc_agi_3.runner import deliberate
from beat_arc_agi_3.schemas import CommitActions, GameObservation
from beat_arc_agi_3.session import Session


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
    actions_taken = 0
    turn_context = "This is the initial observation for the session."
    history = TimelineHistoryReader(session.timeline)

    while True:
        if current.state is GameState.WIN:
            return LoopResult(
                stop_reason="win",
                turns=turns,
                actions=actions_taken,
                observation=current,
            )
        if actions_taken >= policy.max_actions:
            return LoopResult(
                stop_reason="max_actions",
                turns=turns,
                actions=actions_taken,
                observation=current,
            )
        if turns >= policy.max_turns:
            return LoopResult(
                stop_reason="max_turns",
                turns=turns,
                actions=actions_taken,
                observation=current,
            )
        if not current.available_actions:
            return LoopResult(
                stop_reason="no_legal_actions",
                turns=turns,
                actions=actions_taken,
                observation=current,
            )

        commit = await deliberate(
            agent,
            AgentDeps(observation=current, history=history),
            session.conversation,
            turn_context=turn_context,
        )
        turns += 1
        committed_count = len(commit.actions)
        executed_count = 0
        queue_stop = "the committed queue completed"
        turn_start = current

        for action in commit.actions:
            if actions_taken >= policy.max_actions:
                return LoopResult(
                    stop_reason="max_actions",
                    turns=turns,
                    actions=actions_taken,
                    observation=current,
                )
            if action.action not in adapter.available_actions:
                queue_stop = (
                    f"{action.action} was no longer legal; remaining actions "
                    "were dropped"
                )
                break

            after = adapter.apply(action)
            transition = session.timeline.append(action=action, after=after)
            current = after
            executed_count += 1
            actions_taken += 1

            if transition.win:
                return LoopResult(
                    stop_reason="win",
                    turns=turns,
                    actions=actions_taken,
                    observation=current,
                )
            if transition.level_up:
                queue_stop = (
                    "a level was completed; remaining actions were dropped"
                )
                break
            if transition.dead:
                queue_stop = (
                    "the game entered GAME_OVER; remaining actions were dropped"
                )
                break

        turn_context = (
            f"Previous commit queued {committed_count} action(s) and executed "
            f"{executed_count}; stopped because {queue_stop}. "
            f"Level {turn_start.levels_completed}→{current.levels_completed}; "
            f"state {turn_start.state.value}→{current.state.value}. "
            f"The previous intent was: {commit.reason}"
        )
