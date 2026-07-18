from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.models import Model

from beat_arc_agi_3.dependencies import AgentDeps, HistoryDetail, HistoryQuery
from beat_arc_agi_3.schemas import CommitActions


INSTRUCTIONS = """
You are an ARC-AGI-3 deliberation agent. Infer useful next actions from the
current observation and recorded real transitions. You may inspect history with
read_history. When ready, call commit_actions with a non-empty ordered queue,
the reason for the queue, and a suggestion for the next deliberation turn.
Only commit actions listed as legal in the current observation. ACTION6 is a
click and requires x/y coordinates; parameterless actions reject coordinates.
A commit ends this turn, so do not request more tools alongside it.
""".strip()


def build_agent(model: Model | str | None = None) -> Agent[AgentDeps, CommitActions]:
    """Build the milestone agent around an injected or configured model."""

    agent: Agent[AgentDeps, CommitActions] = Agent(
        model,
        deps_type=AgentDeps,
        output_type=ToolOutput(CommitActions, name="commit_actions"),
        instructions=INSTRUCTIONS,
        end_strategy="early",
        retries=2,
    )

    @agent.tool
    async def read_history(
        ctx: RunContext[AgentDeps],
        detail: HistoryDetail = "brief",
        limit: int = 20,
    ) -> str:
        """Read recent real transitions at the requested level of detail."""

        query = HistoryQuery(detail=detail, limit=limit)
        return await ctx.deps.history.read(query)

    @agent.output_validator
    async def validate_commit(
        ctx: RunContext[AgentDeps], output: CommitActions
    ) -> CommitActions:
        legal = set(ctx.deps.observation.available_action_names)
        unavailable = sorted(
            {action.action for action in output.actions if action.action not in legal}
        )
        if unavailable:
            raise ModelRetry(
                f"Committed unavailable actions {unavailable}; "
                f"legal actions are {sorted(legal)}"
            )
        return output

    return agent
