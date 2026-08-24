from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from .contracts import TaskEnvelope
from .prompts import build_worker_prompt, load_skill


@dataclass(frozen=True)
class OrcaCommand:
    argv: list[str]
    purpose: str


def build_orca_worker_spec(task: TaskEnvelope, assignment: dict[str, Any]) -> dict[str, Any]:
    skill = load_skill(task.category)
    return {
        "kind": "ssophiz_ctf_worker",
        "control_task_id": task.id,
        "worker": assignment,
        "objective": str(assignment.get("focus") or "Independently solve and validate the task."),
        "task_contract": task.to_dict(),
        "instructions": build_worker_prompt(task, assignment, skill),
    }


def build_orca_plan(task: TaskEnvelope, assignments: list[dict[str, Any]], executable: str = "orca") -> list[OrcaCommand]:
    commands = [
        OrcaCommand(
            [executable, "orchestration", "run-create", "--objective", f"Solve and validate: {task.name}", "--json"],
            "create_run",
        )
    ]
    for assignment in assignments:
        if assignment["adapter"] != "orca":
            continue
        spec = json.dumps(build_orca_worker_spec(task, assignment), ensure_ascii=False)
        task_placeholder = f"<task_id_for_{assignment['profile']}>"
        commands.append(
            OrcaCommand(
                [executable, "orchestration", "task-create", "--spec", spec, "--json"],
                f"create_{assignment['profile']}_task",
            )
        )
        argv = [
            executable,
            "orchestration",
            "worker-start",
            "--task",
            task_placeholder,
            "--worktree",
            "current",
            "--agent",
            assignment["agent"],
            "--model",
            assignment["model"],
        ]
        if assignment.get("effort"):
            argv.extend(["--effort", assignment["effort"]])
        argv.append("--json")
        commands.append(OrcaCommand(argv, f"start_{assignment['profile']}"))
    return commands


class OrcaRuntime:
    def __init__(self, executable: str = "orca"):
        self.executable = executable

    def _run(self, *args: str) -> dict[str, Any]:
        completed = subprocess.run(
            [self.executable, *args, "--json"],
            text=True,
            errors="replace",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
        return json.loads(completed.stdout)

    def status(self) -> dict[str, Any]:
        return self._run("status")

    def create_run(self, objective: str) -> dict[str, Any]:
        return self._run("orchestration", "run-create", "--objective", objective)

    def create_task(self, spec: TaskEnvelope | dict[str, Any]) -> dict[str, Any]:
        payload = spec.to_json() if isinstance(spec, TaskEnvelope) else json.dumps(spec, ensure_ascii=False)
        return self._run("orchestration", "task-create", "--spec", payload)

    def create_worker_task(self, task: TaskEnvelope, assignment: dict[str, Any]) -> dict[str, Any]:
        return self.create_task(build_orca_worker_spec(task, assignment))

    def start_worker(self, task_id: str, assignment: dict[str, Any]) -> dict[str, Any]:
        args = [
            "orchestration",
            "worker-start",
            "--task",
            task_id,
            "--worktree",
            "current",
            "--agent",
            str(assignment["agent"]),
            "--model",
            str(assignment["model"]),
        ]
        if assignment.get("effort"):
            args.extend(["--effort", str(assignment["effort"])])
        return self._run(*args)

    def task_list(self) -> dict[str, Any]:
        return self._run("orchestration", "task-list")

    def check_wait(self, timeout_ms: int) -> dict[str, Any]:
        return self._run(
            "orchestration",
            "check",
            "--wait",
            "--types",
            "worker_done,escalation,question",
            "--timeout-ms",
            str(max(1000, min(timeout_ms, 900000))),
        )

    def acknowledge(self, delivery_id: str) -> dict[str, Any]:
        return self._run("orchestration", "check", "--ack", delivery_id)

    def release_worker(self, dispatch_id: str) -> dict[str, Any]:
        return self._run("orchestration", "worker-release", "--dispatch", dispatch_id)
