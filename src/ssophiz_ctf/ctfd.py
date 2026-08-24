from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SubmissionResult:
    status: str
    message: str
    raw: dict[str, Any]


class CTFdClient:
    def __init__(self, base_url: str, token: str, timeout: int = 20):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("CTFd base_url must use http or https")
        if not token:
            raise ValueError("CTFd token is required")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "CTFdClient":
        token_env = config.get("token_env", "SSOPHIZ_CTFD_TOKEN")
        return cls(str(config.get("base_url", "")), os.getenv(token_env, ""))

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Token {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ssophiz-ctf-harness/0.1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"CTFd HTTP {exc.code}: {detail[:500]}") from exc

    def list_challenges(self) -> list[dict[str, Any]]:
        response = self._request("GET", "/api/v1/challenges")
        return list(response.get("data") or [])

    def get_challenge(self, challenge_id: int) -> dict[str, Any]:
        response = self._request("GET", f"/api/v1/challenges/{challenge_id}")
        data = response.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("CTFd returned no challenge data")
        return data

    def submit_flag(self, challenge_id: int, flag: str) -> SubmissionResult:
        response = self._request(
            "POST",
            "/api/v1/challenges/attempt",
            {"challenge_id": challenge_id, "submission": flag},
        )
        data = response.get("data") or {}
        status = str(data.get("status") or "error").lower()
        message = str(data.get("message") or response.get("errors") or "")
        normalized = "correct" if status == "correct" else "incorrect" if status == "incorrect" else "error"
        return SubmissionResult(normalized, message, response)

    def download_attachment(self, file_url: str, destination: str | Path) -> Path:
        """Download one CTFd-provided attachment, refusing cross-origin URLs."""
        base = urllib.parse.urlparse(self.base_url)
        resolved = urllib.parse.urlparse(urllib.parse.urljoin(f"{self.base_url}/", file_url))
        if resolved.scheme not in {"http", "https"} or resolved.netloc != base.netloc:
            raise ValueError("CTFd attachment must remain on the configured CTFd host")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            resolved.geturl(),
            headers={"Authorization": f"Token {self.token}", "User-Agent": "ssophiz-ctf-harness/0.1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                target.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"CTFd attachment HTTP {exc.code}: {detail[:500]}") from exc
        return target
