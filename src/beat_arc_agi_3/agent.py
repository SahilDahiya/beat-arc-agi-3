import asyncio
import inspect
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Literal, TypeVar

from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.models import Model
from pydantic_ai.providers.openai import OpenAIProvider

from beat_arc_agi_3.config import Settings
from beat_arc_agi_3.dependencies import (
    AgentDeps,
    HistoryDetail,
    HistoryFlag,
    HistoryQuery,
    PredictionStatus,
)
from beat_arc_agi_3.events import (
    BacktestCompletedEvent,
    BfsCompletedEvent,
    ToolCompletedEvent,
    ToolFailedEvent,
    ToolStartedEvent,
    WorldModelInstalledEvent,
)
from beat_arc_agi_3.oauth_openai_codex import (
    resolve_openai_codex_credentials,
)
from beat_arc_agi_3.openai_codex_model import OpenAICodexResponsesModel
from beat_arc_agi_3.schemas import CommitActions
from beat_arc_agi_3.synthesis import BacktestReport, BacktestRequiredError
from beat_arc_agi_3.tools.edit_file import EditFileError, EditFileQuery
from beat_arc_agi_3.tools.read_file import ReadFileError, ReadFileQuery
from beat_arc_agi_3.tools.run_backtest import (
    RunBacktestQuery,
    render_backtest_report,
)
from beat_arc_agi_3.tools.run_bfs import (
    ClickCandidate,
    RunBfsQuery,
    execute_run_bfs,
    render_bfs_report,
)
from beat_arc_agi_3.tools.run_python import (
    RunPythonError,
    RunPythonQuery,
    execute_run_python,
)
from beat_arc_agi_3.tools.write_file import WriteFileError, WriteFileQuery
from beat_arc_agi_3.world_model import WORLD_MODEL_FILENAME, WorldModelError


ToolResult = TypeVar("ToolResult")


async def _run_recorded_tool(
    ctx: RunContext[AgentDeps],
    *,
    tool_name: str,
    started_summary: str,
    completed_summary: str,
    operation: Callable[[], ToolResult | Awaitable[ToolResult]],
    on_success: Callable[[ToolResult], None] | None = None,
) -> ToolResult:
    """Execute one model tool between durable start and terminal events."""

    tool_call_id = ctx.tool_call_id
    if tool_call_id is None:
        raise RuntimeError(f"{tool_name} requires a Pydantic AI tool_call_id")
    ctx.deps.events.append(
        turn=ctx.deps.turn,
        event=ToolStartedEvent(
            summary=started_summary,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
        ),
    )
    started_at = perf_counter()
    try:
        pending = operation()
        result = await pending if inspect.isawaitable(pending) else pending
        if on_success is not None:
            on_success(result)
    except BaseException as exc:
        duration_ms = max(0, int((perf_counter() - started_at) * 1000))
        message = str(exc).strip() or type(exc).__name__
        ctx.deps.events.append(
            turn=ctx.deps.turn,
            event=ToolFailedEvent(
                summary=f"{tool_name} failed",
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                message=message[:2000],
            ),
        )
        raise
    duration_ms = max(0, int((perf_counter() - started_at) * 1000))
    ctx.deps.events.append(
        turn=ctx.deps.turn,
        event=ToolCompletedEvent(
            summary=completed_summary,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            duration_ms=duration_ms,
        ),
    )
    return result


INSTRUCTIONS = """
You are an ARC-AGI-3 deliberation agent. Infer useful next actions from the
current observation and recorded real transitions. You may inspect history with
read_history and analyze read-only Session evidence with run_python. Prefer
exact indices, bounded ranges, and action/flag/prediction filters when repairing
a mechanism. Treat history component boxes, color-count changes, geometric
peripheral-band counts, level-entry distance, and prior same-action indices as
structural facts rather than semantic labels. Use
read_file, write_file, and edit_file for durable UTF-8 working material inside
this session. notes.md is your canonical living scientific scratchpad. Maintain
and prune it every turn under Confirmed mechanics, Current level, Level-entry
grounding, Temporary goal, Decision mode, Hypotheses to test, Confirmed facts,
and Current plan. Within Level-entry grounding, keep these explicit:
- Observed facts
- Hypotheses
- Known unknowns
- Cheapest discriminating probe
When the harness shows the level-entry protocol, complete these structures
before committing a route, and re-run this protocol after every observed
level_up. Under Temporary goal, record the selected hypothesis, a competing
hypothesis, predicate, evidence, and falsifier. Keep it revisable and encode
its best-supported current form in is_goal. Under Decision mode, explicitly
choose goal_search or discriminating_experiment and record why. Do not
treat is_goal returning False everywhere as final; if positive goal evidence is
insufficient, record what evidence is missing and choose the cheapest probe
that could supply it. Never promote a hypothesis to a fact without real
transition evidence. Prefer exact, narrow edits once a file exists.
Before committing, create world_model_v5.py. It must define exactly
these stateful interfaces: init_state(entry_grid), predict(state, grid, action,
x=None, y=None) returning (predicted_grid, {"level_up": bool, "dead": bool,
"win": bool}, next_state), and is_goal(state, grid) returning bool. Model state
must be JSON-serializable. predicted_grid must be a rectangular nested list of
integer color values from 0 through 15 with the observation's shape; never
return hexadecimal strings. After every model revision, call run_backtest and
repair the earliest mismatch until the current revision is green whenever the
existing evidence is sufficient.
Treat a green backtest as finite historical consistency, never proof that the
mechanism, representation, or goal is correct. Prefer general object and latent
state rules. Do not overfit with transition-index or action-occurrence special
cases unless the recorded evidence demonstrates that hidden state. Keep
observations separate from hypotheses, actively falsify unsupported goal and
affordance assumptions, and use the harness experiment evidence in each turn.
Before committing a long action sequence, distinguish the playable region from
persistent HUD, status, inventory, or progress indicators and encode that
separation in the model when the evidence supports it.
Use run_bfs only on that green revision when model-space search is useful; its
returned plan is valid only for the revision named in the result. Choose
goal_search only when the temporary goal has evidence, a falsifier, and a green
executable is_goal predicate. Otherwise choose discriminating_experiment and
commit a bounded probe that separates the selected hypothesis from its nearest
competitor. BFS EXHAUSTED refutes reachability only under that exact revision,
predicate, action candidates, depth, and node budget; it is not proof that the
real level has no solution.
When ready, call commit_actions with a non-empty ordered queue, the reason for
the queue, and a suggestion for the next deliberation turn. A green current
revision permits a prediction-guarded multi-action queue. Use known modeled
behavior to reach an informative frontier efficiently, place the least certain
action last, and let the harness discard the remaining suffix on the first
prediction mismatch. If the installed model is not green, commit exactly one
unchecked discriminating action and state its expected observation and
falsifier in reason. Only commit actions listed as legal in the current
observation. ACTION6 is a click and requires x/y coordinates; parameterless
actions reject coordinates. A commit ends this turn, so do not request more
tools alongside it.
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
        limit: int | None = None,
        indices: list[int] | None = None,
        start: int | None = None,
        end: int | None = None,
        action: int | None = None,
        flags: HistoryFlag | None = None,
        prediction_status: PredictionStatus | None = None,
    ) -> str:
        """Read selected real transitions with factual structural summaries.

        Args:
            detail: Brief facts, full before/after grids, or animation ticks.
            limit: Maximum selected transitions; defaults to 20 for recent or
                filtered queries. Explicit indices and ranges are otherwise
                returned completely, up to the contract bound.
            indices: Exact zero-based indices; negative indices count backward.
            start: Inclusive first transition index for a range.
            end: Inclusive last transition index for a range.
            action: Numeric ARC action filter from 0 through 7.
            flags: Terminal, reset, or mismatch fact to require.
            prediction_status: Exact, mismatch, or unchecked prediction filter.
        """

        try:
            query = HistoryQuery(
                detail=detail,
                limit=limit,
                indices=None if indices is None else tuple(indices),
                start=start,
                end=end,
                action=action,
                flags=flags,
                prediction_status=prediction_status,
            )
            return await _run_recorded_tool(
                ctx,
                tool_name="read_history",
                started_summary=f"Reading selected {detail} history",
                completed_summary=f"Read selected {detail} history",
                operation=lambda: ctx.deps.history.read(query),
            )
        except ValueError as exc:
            raise ModelRetry(str(exc)) from exc

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
            return await _run_recorded_tool(
                ctx,
                tool_name="read_file",
                started_summary=f"Reading {path}",
                completed_summary=f"Read {path}",
                operation=lambda: ctx.deps.workspace.read_file(
                    ReadFileQuery(path=path, offset=offset, limit=limit)
                ),
            )
        except ReadFileError as exc:
            raise ModelRetry(str(exc)) from exc

    @agent.tool
    async def write_file(
        ctx: RunContext[AgentDeps],
        path: str,
        content: str,
    ) -> str:
        """Create or completely replace a UTF-8 session file.

        Args:
            path: Relative path inside the session workdir.
            content: Complete replacement text for the file.
        """

        def record_world_model_install(_result: str) -> None:
            if path != WORLD_MODEL_FILENAME:
                return
            revision = ctx.deps.synthesis.model_revision()
            ctx.deps.events.append(
                turn=ctx.deps.turn,
                event=WorldModelInstalledEvent(
                    summary=(
                        f"Installed world_model_v5.py revision "
                        f"{revision[:12]}"
                    ),
                    revision=revision,
                ),
            )

        try:
            return await _run_recorded_tool(
                ctx,
                tool_name="write_file",
                started_summary=f"Writing {path}",
                completed_summary=f"Wrote {path}",
                operation=lambda: ctx.deps.workspace.write_file(
                    WriteFileQuery(path=path, content=content)
                ),
                on_success=record_world_model_install,
            )
        except WriteFileError as exc:
            raise ModelRetry(str(exc)) from exc

    @agent.tool
    async def edit_file(
        ctx: RunContext[AgentDeps],
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        """Replace exact text in a UTF-8 session file.

        Args:
            path: Relative path inside the session workdir.
            old_string: Exact text, including whitespace, to replace.
            new_string: Replacement text.
            replace_all: Replace every match instead of requiring uniqueness.
        """

        def record_world_model_install(_result: str) -> None:
            if path != WORLD_MODEL_FILENAME:
                return
            revision = ctx.deps.synthesis.model_revision()
            ctx.deps.events.append(
                turn=ctx.deps.turn,
                event=WorldModelInstalledEvent(
                    summary=(
                        f"Installed world_model_v5.py revision "
                        f"{revision[:12]}"
                    ),
                    revision=revision,
                ),
            )

        try:
            return await _run_recorded_tool(
                ctx,
                tool_name="edit_file",
                started_summary=f"Editing {path}",
                completed_summary=f"Edited {path}",
                operation=lambda: ctx.deps.workspace.edit_file(
                    EditFileQuery(
                        path=path,
                        old_string=old_string,
                        new_string=new_string,
                        replace_all=replace_all,
                    )
                ),
                on_success=record_world_model_install,
            )
        except EditFileError as exc:
            raise ModelRetry(str(exc)) from exc

    @agent.tool
    async def run_backtest(
        ctx: RunContext[AgentDeps],
        max_details: int = 1,
    ) -> str:
        """Replay real Timeline transitions through the installed world model.

        Args:
            max_details: Maximum exact cell differences to show for the first
                mismatch. Zero still reports counts and terminal flags.
        """

        query = RunBacktestQuery(max_details=max_details)

        def record_backtest(report: BacktestReport) -> None:
            ctx.deps.events.append(
                turn=ctx.deps.turn,
                event=BacktestCompletedEvent(
                    summary=(
                        f"Backtest {report.status} for revision "
                        f"{report.revision[:12]}: "
                        f"{report.exact_transitions}/"
                        f"{report.timeline_transitions} exact"
                    ),
                    revision=report.revision,
                    status=report.status,
                    timeline_transitions=report.timeline_transitions,
                    exact_transitions=report.exact_transitions,
                ),
            )

        try:
            report = await _run_recorded_tool(
                ctx,
                tool_name="run_backtest",
                started_summary="Backtesting world_model_v5.py",
                completed_summary="Backtest completed",
                operation=lambda: asyncio.to_thread(
                    ctx.deps.synthesis.run_backtest,
                    max_details=query.max_details,
                ),
                on_success=record_backtest,
            )
        except (BacktestRequiredError, WorldModelError, ValueError) as exc:
            raise ModelRetry(str(exc)) from exc
        return render_backtest_report(report)

    @agent.tool
    async def run_python(
        ctx: RunContext[AgentDeps],
        code: str,
        timeout_seconds: int = 10,
    ) -> str:
        """Run Python analysis in a read-only, networkless Session sandbox.

        Args:
            code: Complete Python source to execute.
            timeout_seconds: Hard execution timeout from 1 through 60 seconds.
        """

        query = RunPythonQuery(
            code=code,
            timeout_seconds=timeout_seconds,
        )
        try:
            return await _run_recorded_tool(
                ctx,
                tool_name="run_python",
                started_summary=(
                    f"Running sandboxed Python with {timeout_seconds}s timeout"
                ),
                completed_summary="Sandboxed Python completed",
                operation=lambda: asyncio.to_thread(
                    execute_run_python,
                    ctx.deps.workspace,
                    query,
                ),
            )
        except RunPythonError as exc:
            raise ModelRetry(str(exc)) from exc

    @agent.tool
    async def run_bfs(
        ctx: RunContext[AgentDeps],
        target: Literal["is_goal", "level_up", "win"] = "is_goal",
        max_depth: int = 24,
        node_budget: int = 100_000,
        click_candidates: list[ClickCandidate] | None = None,
        timeout_seconds: int = 60,
    ) -> str:
        """Search the current green model for a bounded goal-reaching plan.

        Args:
            target: Modeled success predicate to seek.
            max_depth: Maximum action count in a candidate plan.
            node_budget: Maximum modeled states to expand.
            click_candidates: Coordinates to consider when ACTION6 is legal.
            timeout_seconds: Hard search timeout from 1 through 600 seconds.
        """

        query = RunBfsQuery(
            target=target,
            max_depth=max_depth,
            node_budget=node_budget,
            click_candidates=tuple(click_candidates or ()),
            timeout_seconds=timeout_seconds,
        )

        def record_bfs(report) -> None:
            ctx.deps.events.append(
                turn=ctx.deps.turn,
                event=BfsCompletedEvent(
                    summary=(
                        f"BFS {report.status} for {report.target} on revision "
                        f"{report.revision[:12]}"
                    ),
                    revision=report.revision,
                    target=report.target,
                    status=report.status,
                    max_depth=query.max_depth,
                    node_budget=query.node_budget,
                    expanded_nodes=report.expanded_nodes,
                    distinct_states=report.distinct_states,
                    depth=report.depth,
                    actions=report.actions,
                ),
            )
        try:
            report = await _run_recorded_tool(
                ctx,
                tool_name="run_bfs",
                started_summary=(
                    f"Searching model for {target}, depth {max_depth}, "
                    f"budget {node_budget}"
                ),
                completed_summary=f"Model search for {target} completed",
                operation=lambda: asyncio.to_thread(
                    execute_run_bfs,
                    ctx.deps.synthesis,
                    query,
                ),
                on_success=record_bfs,
            )
        except (BacktestRequiredError, WorldModelError, ValueError) as exc:
            raise ModelRetry(str(exc)) from exc
        return render_bfs_report(report)

    @agent.output_validator
    async def validate_commit(
        ctx: RunContext[AgentDeps], output: CommitActions
    ) -> CommitActions:
        legal = set(ctx.deps.observation.legal_action_names)
        unavailable = sorted(
            {action.action for action in output.actions if action.action not in legal}
        )
        if unavailable:
            raise ModelRetry(
                f"Committed unavailable actions {unavailable}; "
                f"legal actions are {sorted(legal)}"
            )
        try:
            ctx.deps.synthesis.inspect_model()
        except WorldModelError as exc:
            raise ModelRetry(str(exc)) from exc
        try:
            ctx.deps.synthesis.require_green()
        except BacktestRequiredError as exc:
            if len(output.actions) != 1:
                raise ModelRetry(
                    "The current world model is untrusted, so commit exactly "
                    "one unchecked action or repair and backtest the model "
                    f"before committing a queue: {exc}"
                ) from exc
        else:
            try:
                ctx.deps.synthesis.preflight_actions(output.actions)
            except (BacktestRequiredError, WorldModelError) as exc:
                raise ModelRetry(
                    f"Committed actions failed world-model preflight: {exc}"
                ) from exc
        return output

    return agent


def build_openai_model(settings: Settings) -> OpenAICodexResponsesModel:
    """Construct the configured subscription-backed OpenAI model."""

    provider_name, separator, model_name = settings.pydantic_ai_model.partition(":")
    if provider_name != "openai-codex" or not separator or not model_name:
        raise ValueError(
            "pydantic_ai_model must use the "
            "openai-codex:<model-name> format"
        )
    credentials = resolve_openai_codex_credentials()
    return OpenAICodexResponsesModel(
        model_name,
        provider=OpenAIProvider(
            openai_client=AsyncOpenAI(
                base_url="https://chatgpt.com/backend-api/codex",
                api_key=credentials.access,
                default_headers={
                    "chatgpt-account-id": credentials.account_id,
                    "originator": "beat-arc-agi-3",
                    "OpenAI-Beta": "responses=experimental",
                },
            )
        ),
        settings={"openai_store": False},
    )
