from datetime import UTC
from typing import Annotated

from arc_agi import Arcade, OperationMode
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.agent import build_agent, build_openai_model
from beat_arc_agi_3.config import Settings
from beat_arc_agi_3.events import (
    EnvironmentReplayFailedEvent,
    EnvironmentReplayStartedEvent,
    EnvironmentRestartedEvent,
)
from beat_arc_agi_3.loop import (
    LoopPolicy,
    LoopRestartContext,
    LoopResult,
    run_agent_loop,
)
from beat_arc_agi_3.restart import (
    replay_session,
    resumes_pending_deliberation,
)
from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.session import Session, SessionId


SessionLabel = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=104,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    ),
]


class ProcessConfig(BaseModel):
    """Identity, environment, and optional private caps for one run."""

    model_config = ConfigDict(frozen=True)

    game_id: str = Field(min_length=1)
    session_label: SessionLabel
    started_at: AwareDatetime
    operation_mode: OperationMode
    max_turns: int | None = Field(default=None, ge=1)
    max_actions: int | None = Field(default=None, ge=1)
    max_deliberation_retries: int = Field(default=3, ge=0)
    retry_base_delay_seconds: float = Field(default=2.0, ge=0)

    @property
    def session_id(self) -> str:
        timestamp = self.started_at.astimezone(UTC).strftime(
            "%Y%m%dT%H%M%S.%fZ"
        )
        return f"{timestamp}-{self.session_label}"


async def run_process(*, settings: Settings, config: ProcessConfig) -> LoopResult:
    """Build every runtime dependency and execute one new ARC session."""

    arcade = Arcade(
        arc_api_key=settings.arc_api_key.get_secret_value(),
        operation_mode=config.operation_mode,
    )
    environment = arcade.make(config.game_id)
    if environment is None:
        raise RuntimeError(
            f"Arcade could not create environment {config.game_id!r} "
            f"in {config.operation_mode.value!r} mode"
        )

    initial_frame = environment.observation_space
    if initial_frame is None:
        raise RuntimeError(
            f"Arcade environment {environment.info.game_id!r} has no initial "
            "observation after creation"
        )
    initial_observation = GameObservation.from_frame(initial_frame)

    session = Session.create(
        sessions_root=settings.sessions_root,
        session_id=config.session_id,
        game_id=environment.info.game_id,
        model=settings.pydantic_ai_model,
        operation_mode=config.operation_mode.value,
        environment_guid=initial_frame.guid,
        scorecard_id=environment.scorecard_id,
    )
    model = build_openai_model(settings)
    agent = build_agent(model)
    return await run_agent_loop(
        agent=agent,
        adapter=ArcGameAdapter(environment),
        initial_observation=initial_observation,
        session=session,
        policy=LoopPolicy(
            max_turns=config.max_turns,
            max_actions=config.max_actions,
            max_deliberation_retries=config.max_deliberation_retries,
            retry_base_delay_seconds=config.retry_base_delay_seconds,
        ),
    )


class RestartProcessConfig(BaseModel):
    """Existing Session identity, environment, and private restart bounds."""

    model_config = ConfigDict(frozen=True)

    session_id: SessionId
    operation_mode: OperationMode
    max_turns: int | None = Field(default=None, ge=1)
    max_actions: int | None = Field(default=None, ge=1)
    max_deliberation_retries: int = Field(default=3, ge=0)
    retry_base_delay_seconds: float = Field(default=2.0, ge=0)


async def restart_process(
    *,
    settings: Settings,
    config: RestartProcessConfig,
) -> LoopResult:
    """Rebuild environment state and continue the same durable Session."""

    agent = build_agent(build_openai_model(settings))
    session = Session.open(
        sessions_root=settings.sessions_root,
        session_id=config.session_id,
    )
    if session.metadata.model != settings.pydantic_ai_model:
        raise ValueError(
            f"Session model {session.metadata.model!r} does not match "
            f"configured model {settings.pydantic_ai_model!r}"
        )
    resume_pending = resumes_pending_deliberation(session)
    arcade = Arcade(
        arc_api_key=settings.arc_api_key.get_secret_value(),
        operation_mode=config.operation_mode,
    )
    environment = arcade.make(session.metadata.game_id)
    if environment is None:
        raise RuntimeError(
            f"Arcade could not create environment {session.metadata.game_id!r} "
            f"in {config.operation_mode.value!r} mode"
        )
    initial_frame = environment.observation_space
    if initial_frame is None:
        raise RuntimeError(
            f"Arcade environment {environment.info.game_id!r} has no initial "
            "observation after creation"
        )
    adapter = ArcGameAdapter(environment)
    prior_events = session.events.entries()
    attempt = 2 + sum(
        entry.event.type == "environment_replay_started"
        for entry in prior_events
    )
    event_turn = max((entry.turn for entry in prior_events), default=0)
    session.events.append(
        turn=event_turn,
        event=EnvironmentReplayStartedEvent(
            summary=(
                f"Environment attempt {attempt} started deterministic replay"
            ),
            attempt=attempt,
            operation_mode=config.operation_mode.value,
            environment_guid=initial_frame.guid,
            scorecard_id=environment.scorecard_id,
            expected_transitions=len(session.timeline.transitions()),
        ),
    )
    try:
        checkpoint = replay_session(
            session=session,
            adapter=adapter,
            initial_observation=GameObservation.from_frame(initial_frame),
        )
    except Exception as exc:
        message = str(exc).strip() or type(exc).__name__
        session.events.append(
            turn=event_turn,
            event=EnvironmentReplayFailedEvent(
                summary=f"Environment attempt {attempt} replay failed",
                attempt=attempt,
                error_type=type(exc).__name__,
                message=message[:2000],
            ),
        )
        raise
    session.events.append(
        turn=event_turn,
        event=EnvironmentRestartedEvent(
            summary=(
                f"Environment attempt {attempt} reproduced "
                f"{len(session.timeline.transitions())} transition(s)"
            ),
            attempt=attempt,
            operation_mode=config.operation_mode.value,
            environment_guid=initial_frame.guid,
            scorecard_id=environment.scorecard_id,
            replayed_transitions=len(session.timeline.transitions()),
            checkpoint_state=checkpoint.state,
            checkpoint_levels_completed=checkpoint.levels_completed,
            resumes_pending_deliberation=resume_pending,
        ),
    )
    return await run_agent_loop(
        agent=agent,
        adapter=adapter,
        initial_observation=checkpoint,
        session=session,
        policy=LoopPolicy(
            max_turns=config.max_turns,
            max_actions=config.max_actions,
            max_deliberation_retries=config.max_deliberation_retries,
            retry_base_delay_seconds=config.retry_base_delay_seconds,
        ),
        restart=LoopRestartContext(
            environment_attempt=attempt,
            replayed_transitions=len(session.timeline.transitions()),
            resumes_pending_deliberation=resume_pending,
        ),
    )
