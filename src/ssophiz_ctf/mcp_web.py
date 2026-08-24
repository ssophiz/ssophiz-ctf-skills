from __future__ import annotations

import json
import os
import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from .mcp_common import current_store
from .web import (
    ScopedWebSession,
    TargetScope,
    itsdangerous_dump,
    itsdangerous_load,
    jwt_decode,
    jwt_sign_hs256,
    probe_ffmpeg_hls_gates,
    run_bounded_race,
    target_operations_enabled,
)


mcp = FastMCP(
    "SSophiz CTF Web",
    instructions=(
        "Web helpers for authorized task contracts. Local token/media tools do not access targets. "
        "HTTP tools require task opt-in plus SSOPHIZ_ENABLE_TARGETS=1 and enforce the task endpoint allowlist."
    ),
)


def _task_scope(task_id: str) -> tuple[Any, TargetScope]:
    store = current_store()
    try:
        task = store.get_task(task_id)
    finally:
        store.close()
    scope = TargetScope(tuple(task.endpoints), target_operations_enabled(task.allow_target_operations))
    return task, scope


def _permit_method(method: str, confirm_state_change: bool) -> None:
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return
    if not confirm_state_change or os.getenv("SSOPHIZ_ENABLE_TARGET_MUTATION") != "1":
        raise PermissionError(
            "state-changing target requests require confirm_state_change=true and SSOPHIZ_ENABLE_TARGET_MUTATION=1"
        )


@mcp.tool()
def decode_jwt_unverified(token: str) -> dict[str, Any]:
    """Inspect HS256 JWT fields without claiming the signature is valid."""
    return jwt_decode(token, verify_signature=False)


@mcp.tool()
def verify_jwt_hs256(token: str, secret: str) -> dict[str, Any]:
    """Verify and decode an HS256 JWT with an explicitly supplied challenge secret."""
    return jwt_decode(token, secret, verify_signature=True)


@mcp.tool()
def sign_jwt_hs256(payload_json: str, secret: str) -> dict[str, str]:
    """Sign a JSON-object payload with HS256 and a supplied challenge secret."""
    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise ValueError("JWT payload must be a JSON object")
    return {"token": jwt_sign_hs256(payload, secret)}


@mcp.tool()
def sign_itsdangerous(value_json: str, secret: str, salt: str = "ssophiz-ctf", timed: bool = True) -> dict[str, str]:
    """Create a URL-safe itsdangerous value for a supplied challenge secret."""
    return {"token": itsdangerous_dump(json.loads(value_json), secret, salt=salt, timed=timed)}


@mcp.tool()
def verify_itsdangerous(
    token: str,
    secret: str,
    salt: str = "ssophiz-ctf",
    timed: bool = True,
    max_age_seconds: int = 3600,
) -> dict[str, Any]:
    """Verify and load a URL-safe itsdangerous value."""
    return {
        "value": itsdangerous_load(
            token,
            secret,
            salt=salt,
            timed=timed,
            max_age_seconds=max_age_seconds,
        )
    }


@mcp.tool()
def run_web_session(
    task_id: str,
    requests: list[dict[str, Any]],
    retries: int = 2,
    timeout_seconds: float = 10,
    confirm_state_change: bool = False,
) -> list[dict[str, Any]]:
    """Run up to 12 cookie-sharing requests against allowlisted task endpoints."""
    if not 1 <= len(requests) <= 12:
        raise ValueError("requests must contain between 1 and 12 steps")
    _, scope = _task_scope(task_id)
    session = ScopedWebSession(scope, retries=retries)
    results: list[dict[str, Any]] = []
    for item in requests:
        method = str(item.get("method") or "GET").upper()
        _permit_method(method, confirm_state_change)
        raw_body = item.get("body")
        body = None if raw_body is None else str(raw_body).encode("utf-8")
        headers = item.get("headers") or {}
        if not isinstance(headers, dict):
            raise ValueError("request headers must be an object")
        response = session.request(
            method,
            str(item.get("url") or ""),
            headers={str(key): str(value) for key, value in headers.items()},
            body=body,
            timeout_seconds=timeout_seconds,
        )
        results.append(response.to_dict())
    return results


@mcp.tool()
def run_http_race(
    task_id: str,
    method: str,
    url: str,
    body: str = "",
    headers: dict[str, str] | None = None,
    attempts: int = 8,
    workers: int = 4,
    timeout_seconds: float = 10,
    confirm_state_change: bool = False,
) -> dict[str, Any]:
    """Run a bounded request burst against one allowlisted task URL."""
    normalized_method = method.upper()
    _permit_method(normalized_method, confirm_state_change)
    _, scope = _task_scope(task_id)

    def action(index: int, deadline: float) -> dict[str, Any]:
        remaining = max(0.1, min(5.0, deadline - time.monotonic()))
        session = ScopedWebSession(scope, retries=0)
        return session.request(
            normalized_method,
            url,
            headers=headers or {},
            body=body.encode("utf-8") if body else None,
            timeout_seconds=remaining,
            max_response_bytes=256 * 1024,
        ).to_dict(max_text_chars=2000)

    return run_bounded_race(
        action,
        attempts=attempts,
        workers=workers,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
def probe_local_ffmpeg_hls(task_id: str, cases: list[str] | None = None, timeout_seconds: int = 5) -> dict[str, Any]:
    """Probe fixed HLS protocol gates using only a generated dummy file in the task workspace."""
    store = current_store()
    try:
        workspace = store.get_task(task_id).workspace
    finally:
        store.close()
    return probe_ffmpeg_hls_gates(workspace, cases=cases, timeout_seconds=timeout_seconds)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
