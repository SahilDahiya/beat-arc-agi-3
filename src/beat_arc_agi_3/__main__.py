import argparse
import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime

from arc_agi import OperationMode

from beat_arc_agi_3.config import Settings
from beat_arc_agi_3.oauth_openai_codex import (
    start_openai_codex_login,
    wait_for_openai_codex_callback,
)
from beat_arc_agi_3.oauth_store import (
    clear_openai_codex_credentials,
    get_openai_codex_credentials,
    set_openai_codex_credentials,
)
from beat_arc_agi_3.process import ProcessConfig, run_process


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m beat_arc_agi_3")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="start one new ARC session")
    run_parser.add_argument("--game", required=True)
    run_parser.add_argument("--session", required=True)
    run_parser.add_argument(
        "--mode",
        required=True,
        choices=[mode.value for mode in OperationMode],
    )
    run_parser.add_argument("--max-turns", required=True, type=int)
    run_parser.add_argument("--max-actions", required=True, type=int)

    auth_parser = subparsers.add_parser(
        "auth",
        help="manage ChatGPT subscription OAuth",
    )
    auth_subparsers = auth_parser.add_subparsers(
        dest="auth_command",
        required=True,
    )
    auth_subparsers.add_parser("login", help="log in with ChatGPT")
    auth_subparsers.add_parser("status", help="show OAuth login status")
    auth_subparsers.add_parser("logout", help="remove saved OAuth login")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "auth":
        if args.auth_command == "login":
            flow, start = start_openai_codex_login()
            print("Open this URL in your browser:")
            print(start.auth_url)
            print(
                "Waiting for the OAuth callback on "
                "http://localhost:1455..."
            )
            credentials = asyncio.run(wait_for_openai_codex_callback(flow))
            set_openai_codex_credentials(credentials)
            print(
                "OAuth login saved for ChatGPT account "
                f"{credentials.account_id}."
            )
            return 0
        if args.auth_command == "status":
            credentials = get_openai_codex_credentials()
            if credentials is None:
                print("openai-codex: logged out")
            else:
                print(
                    "openai-codex: logged in as "
                    f"{credentials.account_id}; expires={credentials.expires}"
                )
            return 0
        if args.auth_command == "logout":
            clear_openai_codex_credentials()
            print("openai-codex: logged out")
            return 0
        raise RuntimeError(f"unsupported auth command: {args.auth_command}")

    if args.command != "run":
        raise RuntimeError(f"unsupported command: {args.command}")

    config = ProcessConfig(
        game_id=args.game,
        session_label=args.session,
        started_at=datetime.now(UTC),
        operation_mode=OperationMode(args.mode),
        max_turns=args.max_turns,
        max_actions=args.max_actions,
    )
    result = asyncio.run(run_process(settings=Settings(), config=config))
    observation = result.observation
    print(
        f"session={config.session_id} stop={result.stop_reason} "
        f"turns={result.turns} actions={result.actions} "
        f"state={observation.state.value} "
        f"levels={observation.levels_completed}/{observation.win_levels}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
