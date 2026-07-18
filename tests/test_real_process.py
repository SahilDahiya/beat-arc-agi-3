import asyncio
import shutil
from datetime import UTC, datetime

import pytest
from arc_agi import OperationMode
from pydantic_ai.models import override_allow_model_requests

from beat_arc_agi_3.config import Settings
from beat_arc_agi_3.process import ProcessConfig, run_process
from beat_arc_agi_3.session import Session


@pytest.mark.paid_integration
def test_real_model_executes_one_action_in_real_arcade() -> None:
    """Required smoke test: one paid model turn and one real ARC action."""

    settings = Settings()
    config = ProcessConfig(
        game_id="ls20",
        session_label="paid-integration",
        started_at=datetime.now(UTC),
        operation_mode=OperationMode.ONLINE,
        max_turns=1,
        max_actions=1,
    )
    session_path = settings.sessions_root / config.session_id

    try:
        with override_allow_model_requests(True):
            result = asyncio.run(run_process(settings=settings, config=config))

        persisted = Session.open(
            sessions_root=settings.sessions_root,
            session_id=config.session_id,
        )
        assert result.actions == 1
        transitions = persisted.timeline.transitions()
        assert persisted.metadata.game_id.startswith("ls20-")
        assert len(transitions) == 1
        assert transitions[0].after.game_id == persisted.metadata.game_id
        assert persisted.conversation.messages()
    finally:
        if session_path.exists():
            shutil.rmtree(session_path)
