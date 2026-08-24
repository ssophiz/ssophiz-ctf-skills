from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import hmac
import http.cookiejar
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from itsdangerous import BadSignature, URLSafeSerializer, URLSafeTimedSerializer


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:  # binascii.Error differs across Python versions
        raise ValueError("invalid base64url value") from exc


def jwt_sign_hs256(payload: dict[str, Any], secret: str | bytes, headers: dict[str, Any] | None = None) -> str:
    """Create a compact HS256 JWT without accepting an attacker-selected algorithm."""

    header = {"typ": "JWT", "alg": "HS256"}
    if headers:
        forbidden = {str(key).lower() for key in headers} & {"alg", "jku", "jwk", "x5u"}
        if forbidden:
            raise ValueError("JWT headers cannot override trust or algorithm fields")
        header.update(headers)
    key = secret.encode() if isinstance(secret, str) else secret
    if not key:
        raise ValueError("JWT secret cannot be empty")
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(key, signing_input, hashlib.sha256).digest()
    return f"{signing_input.decode('ascii')}.{_b64url_encode(signature)}"


def jwt_decode(token: str, secret: str | bytes | None = None, *, verify_signature: bool = True) -> dict[str, Any]:
    """Decode a JWT and, by default, require an HS256 signature secret."""

    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        raise ValueError("JWT must have three non-empty compact segments")
    try:
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("JWT header and payload must be JSON") from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("JWT header and payload must be objects")
    if header.get("alg") != "HS256":
        raise ValueError("only HS256 JWTs are supported")
    if verify_signature:
        if secret is None:
            raise ValueError("a secret is required when signature verification is enabled")
        key = secret.encode() if isinstance(secret, str) else secret
        expected = hmac.new(key, f"{parts[0]}.{parts[1]}".encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(parts[2])):
            raise ValueError("JWT signature verification failed")
    return {"header": header, "payload": payload, "signature_verified": verify_signature}


def itsdangerous_dump(value: Any, secret: str, *, salt: str = "ssophiz-ctf", timed: bool = True) -> str:
    if not secret:
        raise ValueError("signing secret cannot be empty")
    serializer = URLSafeTimedSerializer(secret, salt=salt) if timed else URLSafeSerializer(secret, salt=salt)
    return serializer.dumps(value)


def itsdangerous_load(
    token: str,
    secret: str,
    *,
    salt: str = "ssophiz-ctf",
    timed: bool = True,
    max_age_seconds: int = 3600,
) -> Any:
    if not secret:
        raise ValueError("signing secret cannot be empty")
    if not 1 <= max_age_seconds <= 31 * 24 * 3600:
        raise ValueError("max_age_seconds is outside the supported range")
    serializer = URLSafeTimedSerializer(secret, salt=salt) if timed else URLSafeSerializer(secret, salt=salt)
    try:
        return serializer.loads(token, max_age=max_age_seconds) if timed else serializer.loads(token)
    except BadSignature as exc:
        raise ValueError("itsdangerous signature verification failed") from exc


def _origin(value: str) -> tuple[str | None, str, int]:
    candidate = value.strip()
    if not candidate:
        raise ValueError("empty endpoint is not a valid scope entry")
    parsed = urllib.parse.urlsplit(candidate if "://" in candidate else f"//{candidate}")
    if parsed.username or parsed.password:
        raise ValueError("scope endpoints cannot contain user information")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        raise ValueError(f"endpoint has no host: {value}")
    scheme = parsed.scheme.lower() or None
    if scheme not in {None, "http", "https"}:
        raise ValueError(f"unsupported endpoint scheme: {scheme}")
    port = parsed.port or (443 if scheme == "https" else 80)
    return scheme, host, port


@dataclass(frozen=True)
class TargetScope:
    endpoints: tuple[str, ...]
    enabled: bool = False

    def validate_url(self, url: str) -> str:
        if not self.enabled:
            raise PermissionError("external target operations are disabled for this task")
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError("target URL must be absolute HTTP(S)")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("target URL cannot contain credentials or a fragment")
        request_origin = _origin(url)
        for endpoint in self.endpoints:
            allowed_scheme, allowed_host, allowed_port = _origin(endpoint)
            scheme, host, port = request_origin
            if host == allowed_host and port == allowed_port and allowed_scheme in {None, scheme}:
                return urllib.parse.urlunsplit(parsed)
        raise PermissionError("target URL is outside the task endpoint allowlist")


@dataclass(frozen=True)
class WebResponse:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes
    attempts: int

    def to_dict(self, max_text_chars: int = 20_000) -> dict[str, Any]:
        return {
            "url": self.url,
            "status": self.status,
            "headers": self.headers,
            "body": self.body.decode("utf-8", errors="replace")[:max_text_chars],
            "body_bytes": len(self.body),
            "attempts": self.attempts,
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class ScopedWebSession:
    """Cookie-aware bounded HTTP client locked to an explicit target scope."""

    def __init__(self, scope: TargetScope, *, retries: int = 2, backoff_seconds: float = 0.1):
        if not 0 <= retries <= 4:
            raise ValueError("retries must be between 0 and 4")
        if not 0 <= backoff_seconds <= 2:
            raise ValueError("backoff_seconds must be between 0 and 2")
        self.scope = scope
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(self.cookies),
            _NoRedirect(),
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        timeout_seconds: float = 10,
        max_response_bytes: int = 2 * 1024 * 1024,
    ) -> WebResponse:
        target = self.scope.validate_url(url)
        normalized_method = method.upper()
        if normalized_method not in {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("unsupported HTTP method")
        if not 0.1 <= timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 0.1 and 30")
        if not 1 <= max_response_bytes <= 8 * 1024 * 1024:
            raise ValueError("max_response_bytes is outside the supported range")
        safe_headers = {str(key): str(value) for key, value in (headers or {}).items()}
        forbidden_headers = {"host", "forwarded", "x-forwarded-host"}
        if {key.lower() for key in safe_headers} & forbidden_headers:
            raise ValueError("routing headers cannot override the scope-checked target URL")
        for attempt in range(1, self.retries + 2):
            request = urllib.request.Request(target, data=body, headers=safe_headers, method=normalized_method)
            try:
                with self.opener.open(request, timeout=timeout_seconds) as response:
                    content = response.read(max_response_bytes + 1)
                    status = int(response.status)
                    response_headers = dict(response.headers.items())
            except urllib.error.HTTPError as exc:
                content = exc.read(max_response_bytes + 1)
                status = int(exc.code)
                response_headers = dict(exc.headers.items())
            if len(content) > max_response_bytes:
                raise ValueError("HTTP response exceeded max_response_bytes")
            if status not in {502, 503, 504} or attempt > self.retries:
                return WebResponse(target, status, response_headers, content, attempt)
            time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        raise RuntimeError("unreachable retry state")


@dataclass(frozen=True)
class RaceAttempt:
    index: int
    status: str
    elapsed_seconds: float
    result: str = ""
    error: str = ""


def run_bounded_race(
    action: Callable[[int, float], Any],
    *,
    attempts: int = 8,
    workers: int = 4,
    timeout_seconds: float = 10,
    stop_when: Callable[[Any], bool] | None = None,
) -> dict[str, Any]:
    """Run a concurrency burst with hard submission/worker/wall-clock bounds.

    ``action`` receives its attempt index and an absolute monotonic deadline and
    must use that deadline to bound any I/O it performs.
    """

    if not 1 <= attempts <= 128:
        raise ValueError("attempts must be between 1 and 128")
    if not 1 <= workers <= min(32, attempts):
        raise ValueError("workers must be between 1 and min(32, attempts)")
    if not 0.1 <= timeout_seconds <= 30:
        raise ValueError("timeout_seconds must be between 0.1 and 30")
    started = time.monotonic()
    deadline = started + timeout_seconds
    gate = threading.Barrier(workers)
    stopped = threading.Event()

    def invoke(index: int) -> RaceAttempt:
        attempt_started = time.monotonic()
        if stopped.is_set():
            return RaceAttempt(index, "cancelled", 0)
        try:
            if index < workers:
                gate.wait(timeout=max(0.01, deadline - time.monotonic()))
            value = action(index, deadline)
            if stop_when is not None and stop_when(value):
                stopped.set()
            return RaceAttempt(index, "completed", time.monotonic() - attempt_started, repr(value)[:2000])
        except Exception as exc:
            return RaceAttempt(index, "error", time.monotonic() - attempt_started, error=f"{type(exc).__name__}: {exc}")

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ssophiz-race")
    futures = {executor.submit(invoke, index): index for index in range(attempts)}
    done, pending = concurrent.futures.wait(futures, timeout=timeout_seconds)
    records = [future.result() for future in done]
    for future in pending:
        future.cancel()
        records.append(RaceAttempt(futures[future], "timed_out", timeout_seconds))
    executor.shutdown(wait=False, cancel_futures=True)
    records.sort(key=lambda item: item.index)
    return {
        "attempts": [asdict(record) for record in records],
        "elapsed_seconds": min(time.monotonic() - started, timeout_seconds),
        "completed": sum(record.status == "completed" for record in records),
        "errors": sum(record.status == "error" for record in records),
        "timed_out": sum(record.status == "timed_out" for record in records),
        "stopped_early": stopped.is_set(),
    }


def build_ffmpeg_hls_probe_cases(dummy_uri: str) -> dict[str, str]:
    """Build a fixed local-only HLS protocol-gate matrix for a dummy fixture."""

    common = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n"
    return {
        "relative-segment": f"{common}#EXTINF:1,\ndummy.bin\n#EXT-X-ENDLIST\n",
        "file-segment": f"{common}#EXTINF:1,\n{dummy_uri}\n#EXT-X-ENDLIST\n",
        "cache-segment": f"{common}#EXTINF:1,\ncache:{dummy_uri}\n#EXT-X-ENDLIST\n",
        "concatf-segment": f"{common}#EXTINF:1,\nconcatf:{dummy_uri}\n#EXT-X-ENDLIST\n",
        "subfile-segment": f"{common}#EXTINF:1,\nsubfile,,start,0,end,16,,:{dummy_uri}\n#EXT-X-ENDLIST\n",
        "ext-x-map": f'{common}#EXT-X-MAP:URI="{dummy_uri}"\n#EXTINF:1,\ndummy.bin\n#EXT-X-ENDLIST\n',
        "byterange": f"{common}#EXT-X-BYTERANGE:16@0\n#EXTINF:1,\n{dummy_uri}\n#EXT-X-ENDLIST\n",
    }


def probe_ffmpeg_hls_gates(
    workspace: str | Path,
    *,
    cases: list[str] | None = None,
    timeout_seconds: int = 5,
) -> dict[str, Any]:
    """Run fixed HLS gate probes against a generated dummy file inside a workspace."""

    root = Path(workspace).resolve()
    if not root.is_dir():
        raise FileNotFoundError(workspace)
    if not 1 <= timeout_seconds <= 10:
        raise ValueError("timeout_seconds must be between 1 and 10")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"available": False, "reason": "ffmpeg is not installed", "results": []}
    with tempfile.TemporaryDirectory(prefix="ffmpeg-hls-probe-", dir=root) as temporary:
        probe_root = Path(temporary).resolve()
        dummy = probe_root / "dummy.bin"
        dummy.write_bytes(b"SSOPHIZ_LOCAL_GATE_PROBE\n")
        matrix = build_ffmpeg_hls_probe_cases(dummy.as_uri())
        selected = cases or list(matrix)
        if len(selected) > len(matrix) or len(set(selected)) != len(selected) or any(name not in matrix for name in selected):
            raise ValueError("unknown or duplicate ffmpeg probe case")
        results: list[dict[str, Any]] = []
        for name in selected:
            playlist = probe_root / f"{name}.m3u8"
            playlist.write_text(matrix[name], encoding="utf-8")
            try:
                completed = subprocess.run(
                    [ffmpeg, "-nostdin", "-v", "error", "-i", str(playlist), "-f", "null", "-"],
                    text=True,
                    errors="replace",
                    capture_output=True,
                    check=False,
                    timeout=timeout_seconds,
                    cwd=probe_root,
                )
                stderr = completed.stderr[-4000:]
                results.append(
                    {
                        "case": name,
                        "exit_code": completed.returncode,
                        "protocol_blocked": "not on whitelist" in stderr.lower(),
                        "fixture_reached": dummy.name.lower() in stderr.lower() or completed.returncode == 0,
                        "stderr": stderr,
                    }
                )
            except subprocess.TimeoutExpired:
                results.append({"case": name, "exit_code": 124, "protocol_blocked": False, "fixture_reached": False, "stderr": "timeout"})
        return {
            "available": True,
            "ffmpeg": ffmpeg,
            "dummy_fixture": "generated inside the task workspace",
            "results": results,
        }


def target_operations_enabled(task_enabled: bool) -> bool:
    """Require both a task-contract opt-in and a process-level operator gate."""

    return task_enabled and os.getenv("SSOPHIZ_ENABLE_TARGETS") == "1"
