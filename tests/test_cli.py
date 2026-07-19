import re
from types import SimpleNamespace

from arc_agi import OperationMode
from arcengine import GameState

from beat_arc_agi_3 import __main__ as cli
from beat_arc_agi_3.loop import LoopResult
from beat_arc_agi_3.oauth_store import OpenAICodexCredentials
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
    assert config.max_turns is None
    assert config.max_actions is None
    assert capsys.readouterr().out == (
        f"session={config.session_id} stop=max_actions turns=1 actions=1 "
        "state=NOT_FINISHED levels=0/7\n"
    )


def test_auth_login_waits_for_callback_and_saves_credentials(
    monkeypatch,
    capsys,
) -> None:
    flow = object()
    credentials = OpenAICodexCredentials(
        access="oauth-access",
        refresh="oauth-refresh",
        expires=1_760_000_000_000,
        account_id="acct-123",
    )
    saved: list[OpenAICodexCredentials] = []

    monkeypatch.setattr(
        cli,
        "start_openai_codex_login",
        lambda: (
            flow,
            SimpleNamespace(auth_url="https://auth.example.test/login"),
        ),
    )

    async def wait_for_callback(received_flow):
        assert received_flow is flow
        return credentials

    monkeypatch.setattr(cli, "wait_for_openai_codex_callback", wait_for_callback)
    monkeypatch.setattr(cli, "set_openai_codex_credentials", saved.append)

    assert cli.main(["auth", "login"]) == 0
    assert saved == [credentials]
    assert capsys.readouterr().out == (
        "Open this URL in your browser:\n"
        "https://auth.example.test/login\n"
        "Waiting for the OAuth callback on http://localhost:1455...\n"
        "OAuth login saved for ChatGPT account acct-123.\n"
    )


def test_auth_status_and_logout_do_not_expose_tokens(monkeypatch, capsys) -> None:
    credentials = OpenAICodexCredentials(
        access="oauth-access",
        refresh="oauth-refresh",
        expires=1_760_000_000_000,
        account_id="acct-123",
    )
    monkeypatch.setattr(
        cli,
        "get_openai_codex_credentials",
        lambda: credentials,
    )
    cleared = False

    def clear() -> None:
        nonlocal cleared
        cleared = True

    monkeypatch.setattr(cli, "clear_openai_codex_credentials", clear)

    assert cli.main(["auth", "status"]) == 0
    assert capsys.readouterr().out == (
        "openai-codex: logged in as acct-123; expires=1760000000000\n"
    )
    assert cli.main(["auth", "logout"]) == 0
    assert cleared is True
    assert capsys.readouterr().out == "openai-codex: logged out\n"


def test_eval_command_runs_the_free_ls20_evidence_regression(
    monkeypatch,
) -> None:
    sessions_root = object()
    report = SimpleNamespace(print=lambda **kwargs: None)
    captured: list[object] = []

    async def run_regression(received_sessions_root):
        captured.append(received_sessions_root)
        return report

    monkeypatch.setattr(
        cli,
        "Settings",
        lambda: SimpleNamespace(sessions_root=sessions_root),
    )
    monkeypatch.setattr(
        cli,
        "run_ls20_session_evidence_regression",
        run_regression,
    )
    monkeypatch.setattr(cli, "report_passed", lambda received: received is report)

    assert cli.main(["eval", "ls20-session-evidence"]) == 0
    assert captured == [sessions_root]


def test_eval_session_command_scores_one_persisted_session(monkeypatch) -> None:
    sessions_root = object()
    report = SimpleNamespace(print=lambda **kwargs: None)
    captured: list[object] = []

    async def run_session_eval(**kwargs):
        captured.append(kwargs)
        return report

    monkeypatch.setattr(
        cli,
        "Settings",
        lambda: SimpleNamespace(sessions_root=sessions_root),
    )
    monkeypatch.setattr(cli, "run_session_stage_eval", run_session_eval)
    monkeypatch.setattr(cli, "report_passed", lambda received: received is report)

    assert cli.main(
        [
            "eval",
            "session",
            "--session",
            "new-live-session",
            "--target-level",
            "1",
        ]
    ) == 0
    assert captured == [
        {
            "sessions_root": sessions_root,
            "session_id": "new-live-session",
            "target_levels_completed": 1,
        }
    ]
