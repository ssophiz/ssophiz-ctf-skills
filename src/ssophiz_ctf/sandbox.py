from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_.-]+")


def safe_workspace_path(root: str | Path, relative: str) -> Path:
    root_path = Path(root).resolve()
    candidate = (root_path / relative).resolve()
    if not candidate.is_relative_to(root_path):
        raise ValueError("Path escapes the worker workspace")
    return candidate


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, object]:
        return {"exit_code": self.exit_code, "stdout": self.stdout, "stderr": self.stderr}


class DockerSandbox:
    def __init__(
        self,
        workspace: str | Path,
        image: str,
        *,
        network: str = "none",
        allow_debug: bool = False,
        cpus: int = 8,
        memory: str = "8g",
    ):
        self.workspace = Path(workspace).resolve()
        self.image = image
        self.network = network
        self.allow_debug = allow_debug
        self.cpus = cpus
        self.memory = memory
        suffix = uuid.uuid4().hex[:10]
        base = _SAFE_NAME.sub("-", self.workspace.name).strip("-") or "worker"
        self.name = f"ssophiz-{base[:28]}-{suffix}"
        self.started = False

    def start(self) -> None:
        if shutil.which("docker") is None:
            raise RuntimeError("docker is not installed")
        self.workspace.mkdir(parents=True, exist_ok=True)
        command = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            self.name,
            "--network",
            self.network,
            "--cpus",
            str(self.cpus),
            "--memory",
            self.memory,
            "--pids-limit",
            "1024",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
        ]
        if self.allow_debug:
            command.extend(["--cap-add", "SYS_PTRACE", "--security-opt", "seccomp=unconfined"])
        if os.name == "nt":
            mount = f"{self.workspace}:/workspace"
        else:
            mount = f"{self.workspace.as_posix()}:/workspace"
        command.extend(["-v", mount, "-w", "/workspace", self.image, "sleep", "infinity"])
        completed = subprocess.run(command, text=True, errors="replace", capture_output=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
        self.started = True

    def run(self, command: str, timeout: int = 60) -> CommandResult:
        if not self.started:
            raise RuntimeError("sandbox has not been started")
        timeout = max(1, min(timeout, 600))
        try:
            completed = subprocess.run(
                ["docker", "exec", self.name, "bash", "-lc", command],
                text=True,
                errors="replace",
                capture_output=True,
                check=False,
                timeout=timeout,
            )
            return CommandResult(completed.returncode, completed.stdout[-20000:], completed.stderr[-20000:])
        except subprocess.TimeoutExpired as exc:
            return CommandResult(124, str(exc.stdout or "")[-20000:], f"timeout after {timeout}s")

    def stop(self) -> None:
        if not self.started:
            return
        subprocess.run(["docker", "stop", "--time", "2", self.name], capture_output=True, check=False)
        self.started = False

    def __enter__(self) -> "DockerSandbox":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()


def read_workspace_file(workspace: str | Path, relative: str, max_chars: int = 20000) -> str:
    path = safe_workspace_path(workspace, relative)
    if not path.is_file():
        raise FileNotFoundError(relative)
    return path.read_text(encoding="utf-8", errors="replace")[: max(1, min(max_chars, 100000))]


def write_workspace_file(workspace: str | Path, relative: str, content: str) -> str:
    path = safe_workspace_path(workspace, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def list_workspace_files(workspace: str | Path, relative: str = ".") -> list[str]:
    root = Path(workspace).resolve()
    path = safe_workspace_path(root, relative)
    if not path.exists():
        return []
    return [str(item.relative_to(root)) for item in sorted(path.rglob("*")) if item.is_file()][:1000]
