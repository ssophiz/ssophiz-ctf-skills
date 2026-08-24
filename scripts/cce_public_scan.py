"""Low-rate, unauthenticated CCE landing-page scanner via Chrome CDP.

This intentionally visits only a short allow-list of public paths.  It does
not log in, enumerate users, brute-force, fuzz, or submit flags.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

import requests
import websocket


PUBLIC_PATHS = ("/", "/login", "/register", "/robots.txt", "/api/v1/challenges")


def wait_for_devtools(port: int, timeout: float = 20.0) -> dict:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/json/version"
    while time.monotonic() < deadline:
        try:
            return requests.get(url, timeout=1, proxies={"http": None, "https": None}).json()
        except (requests.RequestException, ValueError):
            time.sleep(0.2)
    raise TimeoutError("Chrome DevTools did not become ready")


def choose_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def send_command(ws, command_id: int, method: str, params: dict | None = None) -> None:
    ws.send(json.dumps({"id": command_id, "method": method, "params": params or {}}))


def wait_for_response(ws, command_id: int, timeout: float = 15.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            message = json.loads(ws.recv())
        except websocket.WebSocketTimeoutException:
            continue
        if message.get("id") == command_id:
            if "error" in message:
                raise RuntimeError(message["error"])
            return message.get("result", {})
    raise TimeoutError(f"CDP command {command_id} timed out")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://challenge.cce.kr")
    parser.add_argument("--proxy", default="http://192.168.49.1:8282")
    parser.add_argument(
        "--chrome",
        default=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    )
    args = parser.parse_args()

    port = choose_port()
    profile = Path.cwd() / "analysis" / f"cce-public-chrome-{port}"
    profile.mkdir(parents=True, exist_ok=True)
    command = [
        args.chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--ignore-certificate-errors",
        "--remote-allow-origins=*",
        f"--remote-debugging-port={port}",
        f"--proxy-server={args.proxy}",
        f"--user-data-dir={profile}",
        "about:blank",
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_devtools(port)
        tab = requests.put(
            f"http://127.0.0.1:{port}/json/new?{quote('about:blank', safe=':/')}",
            timeout=3,
            proxies={"http": None, "https": None},
        ).json()
        ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=1)
        try:
            next_id = 1
            for method in ("Page.enable", "Network.enable", "Runtime.enable"):
                send_command(ws, next_id, method)
                wait_for_response(ws, next_id)
                next_id += 1

            findings = []
            for path in PUBLIC_PATHS:
                url = args.base.rstrip("/") + path
                send_command(ws, next_id, "Page.navigate", {"url": url})
                wait_for_response(ws, next_id)
                next_id += 1
                time.sleep(1.5)
                expression = """JSON.stringify({
                  url: location.href,
                  title: document.title,
                  body: (document.body ? document.body.innerText : '').slice(0, 6000),
                  links: Array.from(document.querySelectorAll('a')).slice(0,100)
                    .map(a => ({text:(a.innerText||'').trim(), href:a.href}))
                })"""
                send_command(
                    ws,
                    next_id,
                    "Runtime.evaluate",
                    {"expression": expression, "returnByValue": True},
                )
                result = wait_for_response(ws, next_id)
                next_id += 1
                value = result.get("result", {}).get("value", "{}")
                findings.append({"requested": url, **json.loads(value)})
            print(json.dumps(findings, ensure_ascii=False, indent=2))
        finally:
            ws.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
