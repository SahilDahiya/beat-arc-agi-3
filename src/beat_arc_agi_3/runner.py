from typing import Protocol, Sequence

from pydantic_ai import Agent, ModelMessage, UsageLimits

from beat_arc_agi_3.dependencies import AgentDeps
from beat_arc_agi_3.schemas import CommitActions, GameObservation


DELIBERATION_LIMITS = UsageLimits(request_limit=8, tool_calls_limit=8)


class Conversation(Protocol):
    """Session-owned model messages used across deliberation turns."""

    def messages(self) -> tuple[ModelMessage, ...]: ...

    def append(self, messages: Sequence[ModelMessage]) -> None: ...


def render_observation(observation: GameObservation) -> str:
    """Render one observation without JSON punctuation or animation duplication."""

    if observation.grid:
        width = len(observation.grid[0])
        rows = "\n".join(
            "".join(format(value, "x") for value in row)
            for row in observation.grid
        )
        grid = f"shape={len(observation.grid)}x{width}\n{rows}"
    else:
        grid = "shape=0x0\n(empty)"
    return (
        f"State: {observation.state.value} | "
        f"level {observation.levels_completed}/{observation.win_levels}\n"
        f"Legal actions: {list(observation.available_actions)}\n"
        f"Grid:\n{grid}"
    )


async def deliberate(
    agent: Agent[AgentDeps, CommitActions],
    deps: AgentDeps,
    conversation: Conversation,
    *,
    turn_context: str | None = None,
) -> CommitActions:
    """Run and durably extend one session conversation before returning a queue."""

    observation = deps.observation
    prompt_parts = ["Choose the next action queue for this observation."]
    if turn_context:
        prompt_parts.append(turn_context)
    prompt_parts.append(render_observation(observation))
    result = await agent.run(
        "\n".join(prompt_parts),
        deps=deps,
        message_history=conversation.messages(),
        usage_limits=DELIBERATION_LIMITS,
    )
    conversation.append(
        result.new_messages(
            output_tool_return_content=(
                "Action queue accepted by the harness. Next turn should: "
                f"{result.output.suggestion}"
            )
        )
    )
    return result.output
