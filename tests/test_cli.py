import re

from arc_agi import OperationMode
from arcengine import GameState

from beat_arc_agi_3 import __main__ as cli
from beat_arc_agi_3.loop import LoopResult
from beat_arc_agi_3.schemas import GameObservation


def test_run_command_builds_and_executes_process_config(
    monkeypatch, capsys
) -> None:
    settings = object()
    captured: dict[str, object] = {}
    result = LoopResult(
        stop_reason="max_actions",
        turns=1,
        actions=1,
        observation=GameObservation(
            game_id="ls20-version",
            grid=((0,),),
            state=GameState.NOT_FINISHED,
            levels_completed=0,
            win_levels=7,
            available_actions=(1,),
        ),
    )

    async def record_run_process(*, settings, config):
        captured["settings"] = settings
        captured["config"] = config
        return result

    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "run_process", record_run_process)

    exit_code = cli.main(
        [
            "run",
            "--game",
            "ls20",
            "--session",
            "ls20-experiment-001",
            "--mode",
            "online",
            "--max-turns",
            "10",
            "--max-actions",
            "30",
        ]
    )

    assert exit_code == 0
    assert captured["settings"] is settings
    config = captured["config"]
    assert config.game_id == "ls20"
    assert config.session_label == "ls20-experiment-001"
    assert re.fullmatch(
        r"\d{8}T\d{6}\.\d{6}Z-ls20-experiment-001",
        config.session_id,
    )
    assert config.operation_mode is OperationMode.ONLINE
    assert config.max_turns == 10
    assert config.max_actions == 30
    assert capsys.readouterr().out == (
        f"session={config.session_id} stop=max_actions turns=1 actions=1 "
        "state=NOT_FINISHED levels=0/7\n"
    )
