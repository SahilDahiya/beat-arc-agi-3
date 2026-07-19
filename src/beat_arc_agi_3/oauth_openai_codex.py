from __future__ import annotations

import asyncio
import base64
import hashlib
import html
import json
import secrets
import time
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from beat_arc_agi_3.oauth_store import (
    OpenAICodexCredentials,
    get_openai_codex_credentials,
    set_openai_codex_credentials,
)


CLIENT_ID: Final[str] = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL: Final[str] = "https://auth.openai.com/oauth/authorize"
TOKEN_URL: Final[str] = "https://auth.openai.com/oauth/token"
REDIRECT_URI: str = "http://localhost:1455/auth/callback"
SCOPE: Final[str] = "openid profile email offline_access"
JWT_CLAIM_PATH: Final[str] = "https://api.openai.com/auth"
CALLBACK_HOST: str = "localhost"
CALLBACK_PORT: int = 1455
CALLBACK_PATH: Final[str] = "/auth/callback"
EXPIRY_SAFETY_MARGIN_MS: Final[int] = 5 * 60 * 1000


class OpenAICodexOAuthError(RuntimeError):
    """Raised when ChatGPT OAuth login or refresh fails."""


@dataclass(frozen=True)
class OpenAICodexLoginStart:
    auth_url: str


@dataclass(frozen=True)
class OpenAICodexLoginFlow:
    verifier: str
    state: str


def start_openai_codex_login() -> tuple[
    OpenAICodexLoginFlow,
    OpenAICodexLoginStart,
]:
    verifier = secrets.token_urlsafe(64)
    challenge = _create_pkce_challenge(verifier)
    state = secrets.token_hex(16)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "id_token_add_organizations": "true",
            "codex_cli_simplified_flow": "true",
            "originator": "beat-arc-agi-3",
        }
    )
    return (
        OpenAICodexLoginFlow(verifier=verifier, state=state),
        OpenAICodexLoginStart(auth_url=f"{AUTHORIZE_URL}?{query}"),
    )


async def wait_for_openai_codex_callback(
    flow: OpenAICodexLoginFlow,
    *,
    timeout_seconds: float = 300.0,
) -> OpenAICodexCredentials:
    result: asyncio.Future[OpenAICodexCredentials] = (
        asyncio.get_running_loop().create_future()
    )

    async def handle_client(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request_line = await reader.readline()
            try:
                method, target, _version = (
                    request_line.decode("ascii").strip().split(" ", 2)
                )
            except (UnicodeDecodeError, ValueError):
                await _write_http_response(writer, 400, "Invalid callback request.")
                return
            if method != "GET":
                await _write_http_response(writer, 405, "Method not allowed.")
                return
            parsed = urlparse(target)
            if parsed.path != CALLBACK_PATH:
                await _write_http_response(writer, 404, "Unknown callback path.")
                return
            while True:
                header_line = await reader.readline()
                if not header_line or header_line in (b"\r\n", b"\n"):
                    break
            query = parse_qs(parsed.query)
            code = query.get("code", [None])[0]
            state = query.get("state", [None])[0]
            if not isinstance(code, str) or not code:
                await _write_http_response(writer, 400, "Missing authorization code.")
                return
            if state != flow.state:
                await _write_http_response(writer, 400, "OAuth state mismatch.")
                return
            credentials = await _exchange_authorization_code(
                code=code,
                verifier=flow.verifier,
            )
            if not result.done():
                result.set_result(credentials)
            await _write_http_response(writer, 200, "Login complete. Return to the terminal.")
        except Exception as exc:
            if not result.done():
                result.set_exception(exc)
            try:
                await _write_http_response(writer, 500, "Login failed.")
            except Exception:
                pass
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(
        handle_client,
        host=CALLBACK_HOST,
        port=CALLBACK_PORT,
    )
    try:
        return await asyncio.wait_for(result, timeout=timeout_seconds)
    finally:
        server.close()
        await server.wait_closed()


def resolve_openai_codex_credentials() -> OpenAICodexCredentials:
    credentials = get_openai_codex_credentials()
    if credentials is None:
        raise OpenAICodexOAuthError(
            "ChatGPT subscription login required; run "
            "`uv run python -m beat_arc_agi_3 auth login`"
        )
    if credentials.expires > int(time.time() * 1000):
        return credentials
    refreshed = refresh_openai_codex_credentials(credentials)
    set_openai_codex_credentials(refreshed)
    return refreshed


def refresh_openai_codex_credentials(
    credentials: OpenAICodexCredentials,
) -> OpenAICodexCredentials:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            content=urlencode(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": credentials.refresh,
                    "client_id": CLIENT_ID,
                }
            ),
        )
    return _parse_token_response(response, operation="token refresh")


async def _exchange_authorization_code(
    *,
    code: str,
    verifier: str,
) -> OpenAICodexCredentials:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            content=urlencode(
                {
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "code": code,
                    "code_verifier": verifier,
                    "redirect_uri": REDIRECT_URI,
                }
            ),
        )
    return _parse_token_response(response, operation="token exchange")


def _parse_token_response(
    response: httpx.Response,
    *,
    operation: str,
) -> OpenAICodexCredentials:
    if response.status_code >= 400:
        raise OpenAICodexOAuthError(
            f"{operation} failed: HTTP {response.status_code}"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise OpenAICodexOAuthError(f"invalid {operation} response") from exc
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    if (
        not isinstance(access, str)
        or not access
        or not isinstance(refresh, str)
        or not refresh
        or not isinstance(expires_in, int)
        or expires_in <= 0
    ):
        raise OpenAICodexOAuthError(f"invalid {operation} response")
    return OpenAICodexCredentials(
        access=access,
        refresh=refresh,
        expires=(
            int(time.time() * 1000)
            + expires_in * 1000
            - EXPIRY_SAFETY_MARGIN_MS
        ),
        account_id=extract_account_id(access),
    )


def extract_account_id(access_token: str) -> str:
    parts = access_token.split(".")
    if len(parts) != 3:
        raise OpenAICodexOAuthError("invalid access token")
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload + padding)
        token_payload = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise OpenAICodexOAuthError("failed to decode access token") from exc
    auth_claim = token_payload.get(JWT_CLAIM_PATH)
    if not isinstance(auth_claim, dict):
        raise OpenAICodexOAuthError("missing OpenAI auth claim")
    account_id = auth_claim.get("chatgpt_account_id")
    if not isinstance(account_id, str) or not account_id:
        raise OpenAICodexOAuthError(
            "missing ChatGPT account id in access token"
        )
    return account_id


def _create_pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


async def _write_http_response(
    writer: asyncio.StreamWriter,
    status_code: int,
    message: str,
) -> None:
    reason = {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
    }[status_code]
    body = (
        "<!doctype html><html><body><p>"
        f"{html.escape(message)}"
        "</p></body></html>"
    ).encode("utf-8")
    writer.write(
        (
            f"HTTP/1.1 {status_code} {reason}\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("ascii")
        + body
    )
    await writer.drain()
