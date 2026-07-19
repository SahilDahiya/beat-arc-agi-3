from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from beat_arc_agi_3.config import Settings
from beat_arc_agi_3.dependencies import AgentDeps, HistoryDetail, HistoryQuery
from beat_arc_agi_3.schemas import CommitActions
from beat_arc_agi_3.workspace import ReadFileError, ReadFileQuery


INSTRUCTIONS = """
You are an ARC-AGI-3 deliberation agent. Infer useful next actions from the
current observation and recorded real transitions. You may inspect history with
read_history and inspect UTF-8 files in this session with read_file. When ready,
call commit_actions with a non-empty ordered queue, the reason for the queue,
and a suggestion for the next deliberation turn. Only commit actions listed as
legal in the current observation. ACTION6 is a click and requires x/y
coordinates; parameterless actions reject coordinates. A commit ends this
turn, so do not request more tools alongside it.
""".strip()


def build_agent(
    model: Model | None = None,
) -> Agent[AgentDeps, CommitActions]:
    """Build the milestone agent around an explicitly constructed model."""

    if model is None:
        raise ValueError("model is required")

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

    @agent.tool
    async def read_file(
        ctx: RunContext[AgentDeps],
        path: str,
        offset: int = 1,
        limit: int = 2000,
    ) -> str:
        """Read numbered UTF-8 lines from a file in the session workdir.

        Args:
            path: Relative path inside the session workdir.
            offset: One-based first line to return.
            limit: Maximum number of lines to return.
        """

        try:
            return ctx.deps.workspace.read_file(
                ReadFileQuery(path=path, offset=offset, limit=limit)
            )
        except ReadFileError as exc:
            raise ModelRetry(str(exc)) from exc

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


def build_openai_model(settings: Settings) -> OpenAIResponsesModel:
    """Construct the configured OpenAI model from explicit validated settings."""

    provider_name, separator, model_name = settings.pydantic_ai_model.partition(":")
    if provider_name != "openai" or not separator or not model_name:
        raise ValueError(
            "pydantic_ai_model must use the openai:<model-name> format"
        )
    return OpenAIResponsesModel(
        model_name,
        provider=OpenAIProvider(
            api_key=settings.openai_api_key.get_secret_value()
        ),
    )
