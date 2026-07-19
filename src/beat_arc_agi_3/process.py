from datetime import UTC
from typing import Annotated

from arc_agi import Arcade, OperationMode
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from beat_arc_agi_3.adapter import ArcGameAdapter
from beat_arc_agi_3.agent import build_agent, build_openai_model
from beat_arc_agi_3.config import Settings
from beat_arc_agi_3.loop import LoopPolicy, LoopResult, run_agent_loop
from beat_arc_agi_3.schemas import GameObservation
from beat_arc_agi_3.session import Session


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
        ),
    )
