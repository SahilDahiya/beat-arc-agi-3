from pydantic_ai import Agent, UsageLimits

from beat_arc_agi_3.dependencies import AgentDeps
from beat_arc_agi_3.schemas import CommitActions


DELIBERATION_LIMITS = UsageLimits(request_limit=8, tool_calls_limit=8)


async def deliberate(
    agent: Agent[AgentDeps, CommitActions], deps: AgentDeps
) -> CommitActions:
    """Run one deliberation and return its queue without executing actions."""

    observation = deps.observation
    prompt = (
        "Choose the next action queue for this observation.\n"
        f"Legal actions: {observation.available_action_names}\n"
        f"Observation:\n{observation.model_dump_json(indent=2)}"
    )
    result = await agent.run(prompt, deps=deps, usage_limits=DELIBERATION_LIMITS)
    return result.output
