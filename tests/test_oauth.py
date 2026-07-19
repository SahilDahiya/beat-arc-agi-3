import asyncio
import base64
import json
import os
import socket
from urllib.parse import parse_qs, urlparse

import pytest

from beat_arc_agi_3 import oauth_openai_codex
from beat_arc_agi_3.oauth_openai_codex import (
    OpenAICodexCredentials,
    OpenAICodexOAuthError,
    extract_account_id,
    resolve_openai_codex_credentials,
    start_openai_codex_login,
    wait_for_openai_codex_callback,
)


def access_token(account_id: str) -> str:
    payload = {
        "https://api.openai.com/auth": {
            "chatgpt_account_id": account_id,
        }
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"header.{encoded}.signature"


def test_login_start_builds_pkce_chatgpt_authorization_url() -> None:
    flow, start = start_openai_codex_login()

    parsed = urlparse(start.auth_url)
    query = parse_qs(parsed.query)
    assert parsed.geturl().startswith("https://auth.openai.com/oauth/authorize?")
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == [flow.state]
    assert query["codex_cli_simplified_flow"] == ["true"]
    assert query["originator"] == ["beat-arc-agi-3"]
    assert flow.verifier
    assert query["code_challenge"][0]


def test_extract_account_id_reads_the_openai_auth_claim() -> None:
    assert extract_account_id(access_token("acct-123")) == "acct-123"

    with pytest.raises(OpenAICodexOAuthError, match="invalid access token"):
        extract_account_id("not-a-jwt")


def test_wait_for_callback_validates_state_and_returns_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except PermissionError:
        pytest.skip("TCP loopback sockets are not permitted")
    sock.close()
    callback_host = "127.0.0.1"
    callback_port = 20_000 + (os.getpid() % 20_000)

    async def exchange(*, code: str, verifier: str) -> OpenAICodexCredentials:
        assert code == "code-123"
        assert verifier
        return OpenAICodexCredentials(
            access=access_token("acct-123"),
            refresh="refresh-token",
            expires=1_760_000_000_000,
            account_id="acct-123",
        )

    monkeypatch.setattr(oauth_openai_codex, "_exchange_authorization_code", exchange)
    monkeypatch.setattr(oauth_openai_codex, "CALLBACK_HOST", callback_host)
    monkeypatch.setattr(oauth_openai_codex, "CALLBACK_PORT", callback_port)
    monkeypatch.setattr(
        oauth_openai_codex,
        "REDIRECT_URI",
        f"http://{callback_host}:{callback_port}/auth/callback",
    )

    async def exercise() -> OpenAICodexCredentials:
        flow, _start = start_openai_codex_login()
        waiting = asyncio.create_task(
            wait_for_openai_codex_callback(flow, timeout_seconds=5)
        )
        await asyncio.sleep(0.05)
        reader, writer = await asyncio.open_connection(
            callback_host,
            callback_port,
        )
        writer.write(
            (
                "GET /auth/callback?code=code-123&state="
                f"{flow.state} HTTP/1.1\r\nHost: localhost\r\n\r\n"
            ).encode("ascii")
        )
        await writer.drain()
        response = await reader.readuntil(b"</html>")
        writer.close()
        await writer.wait_closed()
        assert b"Login complete" in response
        return await waiting

    assert asyncio.run(exercise()).account_id == "acct-123"


def test_resolve_credentials_refreshes_and_persists_expired_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expired = OpenAICodexCredentials(
        access="expired-access",
        refresh="refresh-token",
        expires=0,
        account_id="acct-123",
    )
    refreshed = expired.model_copy(
        update={"access": "fresh-access", "expires": 9_999_999_999_999}
    )
    saved: list[OpenAICodexCredentials] = []
    monkeypatch.setattr(
        oauth_openai_codex,
        "get_openai_codex_credentials",
        lambda: expired,
    )
    monkeypatch.setattr(
        oauth_openai_codex,
        "refresh_openai_codex_credentials",
        lambda credentials: refreshed,
    )
    monkeypatch.setattr(
        oauth_openai_codex,
        "set_openai_codex_credentials",
        saved.append,
    )

    assert resolve_openai_codex_credentials() == refreshed
    assert saved == [refreshed]


def test_resolve_credentials_fails_without_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oauth_openai_codex,
        "get_openai_codex_credentials",
        lambda: None,
    )

    with pytest.raises(OpenAICodexOAuthError, match="auth login"):
        resolve_openai_codex_credentials()
