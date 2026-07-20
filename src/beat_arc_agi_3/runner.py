import asyncio
from typing import Protocol, Sequence

from httpx import TransportError
from openai import APIError
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import (
    Agent,
    ModelMessage,
    ModelRequest,
    UsageLimits,
    capture_run_messages,
)

from beat_arc_agi_3.dependencies import AgentDeps
from beat_arc_agi_3.events import (
    CommitAcceptedEvent,
    DeliberationAttemptFailedEvent,
    DeliberationCheckpointedEvent,
    DeliberationStartedEvent,
)
from beat_arc_agi_3.schemas import CommitActions, GameObservation


NO_SDK_USAGE_LIMITS = UsageLimits(
    request_limit=None,
    tool_calls_limit=None,
    input_tokens_limit=None,
    output_tokens_limit=None,
    total_tokens_limit=None,
)


class Conversation(Protocol):
    """Session-owned model messages used across deliberation turns."""

    def messages(self) -> tuple[ModelMessage, ...]: ...

    def context_messages(self) -> tuple[ModelMessage, ...]: ...

    def append(self, messages: Sequence[ModelMessage]) -> None: ...


class DeliberationRetryPolicy(BaseModel):
    """Harness-owned retry bounds that are never shown to the agent."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(default=3, ge=0)
    base_delay_seconds: float = Field(default=2.0, ge=0)

    @property
    def max_attempts(self) -> int:
        return self.max_retries + 1

    def delay_for_retry(self, attempt: int) -> float:
        return self.base_delay_seconds * (2 ** (attempt - 1))


def _is_retryable_model_error(exc: Exception) -> bool:
    if isinstance(exc, TransportError):
        return True
    if not isinstance(exc, APIError):
        return False

    body = exc.body
    body_text = str(body).lower() if body is not None else ""
    message = str(exc).lower()
    non_retryable_markers = (
        "insufficient_quota",
        "insufficient quota",
        "billing",
        "usage limit",
        "invalid_api_key",
        "authentication",
        "permission",
    )
    if any(
        marker in body_text or marker in message
        for marker in non_retryable_markers
    ):
        return False
    status_code = getattr(exc, "status_code", None)
    if status_code in {408, 409, 429, 500, 502, 503, 504, 524}:
        return True
    if isinstance(body, dict):
        values = {
            str(body.get("type", "")).lower(),
            str(body.get("code", "")).lower(),
        }
        if values & {
            "server_error",
            "stream_error",
            "stream_failed",
            "timeout",
        }:
            return True
    return any(
        marker in message
        for marker in (
            "you can retry your request",
            "connection error",
            "connection reset",
            "stream failed",
            "timed out",
            "timeout",
        )
    )


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
    legal_actions = ", ".join(observation.legal_action_names) or "none"
    advertised_actions = ", ".join(observation.available_action_names) or "none"
    advertised = ""
    if observation.legal_action_names != observation.available_action_names:
        advertised = f"\nARC-advertised actions: {advertised_actions}"
    return (
        f"State: {observation.state.value} | "
        f"level {observation.levels_completed}/{observation.win_levels}\n"
        f"Legal actions: {legal_actions}{advertised}\n"
        f"Grid:\n{grid}"
    )


async def deliberate(
    agent: Agent[AgentDeps, CommitActions],
    deps: AgentDeps,
    conversation: Conversation,
    *,
    turn_context: str | None = None,
    retry_policy: DeliberationRetryPolicy | None = None,
    resume_from_checkpoint: bool = False,
) -> CommitActions:
    """Run and durably extend one session conversation before returning a queue."""

    observation = deps.observation
    durable_messages = conversation.messages()
    context_messages = conversation.context_messages()
    prompt_parts = ["Choose the next action queue for this observation."]
    if turn_context:
        prompt_parts.append(turn_context)
    if not durable_messages:
        prompt_parts.extend(
            [
                "Your notes (notes.md; initial session checkpoint):",
                deps.workspace.read_text("notes.md"),
            ]
        )
    prompt_parts.append(render_observation(observation))
    deps.events.append(
        turn=deps.turn,
        event=DeliberationStartedEvent(
            summary=f"Deliberating over turn {deps.turn} observation"
        ),
    )
    policy = retry_policy or DeliberationRetryPolicy()
    prompt = "\n".join(prompt_parts)
    if resume_from_checkpoint:
        if (
            not context_messages
            or not isinstance(context_messages[-1], ModelRequest)
            or context_messages[-1].state != "complete"
        ):
            raise ValueError(
                "pending deliberation resume requires a complete trailing "
                "ModelRequest checkpoint"
            )
    deliberation_durable_start = len(conversation.messages())
    attempt = 0
    while True:
        attempt += 1
        context_messages = conversation.context_messages()
        captured_baseline = len(context_messages)
        durable_before_attempt = len(conversation.messages())
        checkpointed_new = 0

        def checkpoint(captured: list[ModelMessage]) -> None:
            nonlocal checkpointed_new
            new_messages = captured[captured_baseline + checkpointed_new :]
            complete_count = 0
            for index, message in enumerate(new_messages, start=1):
                if message.state != "complete":
                    break
                if isinstance(message, ModelRequest):
                    complete_count = index
            if complete_count == 0:
                return
            batch = new_messages[:complete_count]
            conversation.append(batch)
            checkpointed_new += complete_count
            deps.events.append(
                turn=deps.turn,
                event=DeliberationCheckpointedEvent(
                    summary=(
                        f"Persisted {complete_count} provider-valid "
                        f"message(s) on attempt {attempt}"
                    ),
                    attempt=attempt,
                    messages_added=complete_count,
                    total_messages=len(conversation.messages()),
                ),
            )

        captured: list[ModelMessage] = []
        try:
            with capture_run_messages() as captured:
                async with agent.iter(
                    (
                        None
                        if resume_from_checkpoint
                        or len(conversation.messages())
                        > deliberation_durable_start
                        else prompt
                    ),
                    deps=deps,
                    message_history=context_messages,
                    usage_limits=NO_SDK_USAGE_LIMITS,
                ) as agent_run:
                    async for _ in agent_run:
                        checkpoint(captured)
                    checkpoint(captured)
                    result = agent_run.result
                    if result is None:
                        raise RuntimeError(
                            "agent run ended without a deliberation result"
                        )
        except (KeyboardInterrupt, asyncio.CancelledError):
            checkpoint(captured)
            raise
        except Exception as exc:
            checkpoint(captured)
            retryable = _is_retryable_model_error(exc)
            will_retry = retryable and attempt < policy.max_attempts
            delay = policy.delay_for_retry(attempt) if will_retry else 0.0
            message = str(exc).strip() or type(exc).__name__
            deps.events.append(
                turn=deps.turn,
                event=DeliberationAttemptFailedEvent(
                    summary=(
                        f"Deliberation attempt {attempt} failed; "
                        + ("retrying" if will_retry else "not retrying")
                    ),
                    attempt=attempt,
                    max_attempts=policy.max_attempts,
                    will_retry=will_retry,
                    delay_seconds=delay,
                    error_type=type(exc).__name__,
                    message=message[:2000],
                ),
            )
            if not will_retry:
                raise
            await asyncio.sleep(delay)
            continue

        all_messages = result.all_messages(
            output_tool_return_content=(
                "Action queue accepted by the harness. Next turn should: "
                f"{result.output.suggestion}"
            )
        )
        produced_messages = all_messages[captured_baseline:]
        already_persisted = len(conversation.messages()) - durable_before_attempt
        remaining = produced_messages[already_persisted:]
        if remaining:
            conversation.append(remaining)
            deps.events.append(
                turn=deps.turn,
                event=DeliberationCheckpointedEvent(
                    summary=(
                        f"Persisted {len(remaining)} provider-valid "
                        f"message(s) on attempt {attempt}"
                    ),
                    attempt=attempt,
                    messages_added=len(remaining),
                    total_messages=len(conversation.messages()),
                ),
            )
        break
    action_names = ", ".join(action.action for action in result.output.actions)
    deps.events.append(
        turn=deps.turn,
        event=CommitAcceptedEvent(
            summary=f"Accepted {len(result.output.actions)} action(s): {action_names}",
            actions=result.output.actions,
            reason=result.output.reason,
            suggestion=result.output.suggestion,
        ),
    )
    return result.output
