from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import TaskEnvelope


def load_skill(role: str, repo_root: str | Path | None = None) -> str:
    root = Path(repo_root or Path(__file__).resolve().parents[2])
    path = root / "skills" / role / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"No skill for role: {role}")
    return path.read_text(encoding="utf-8")


def build_worker_prompt(task: TaskEnvelope, assignment: dict[str, Any], skill_text: str) -> str:
    task_json = json.dumps(task.to_dict(), ensure_ascii=False, separators=(",", ":"))
    profile_json = json.dumps(assignment, ensure_ascii=False, separators=(",", ":"))
    wave = int(assignment.get("wave", 0))
    escalation = (
        "Classification pass only: run at most three cheap decisive checks, then publish QUICK, SOLVE, HARD, or BLOCKED."
        if wave == 0
        else "Call list_findings first and read existing artifacts; do not repeat completed triage."
    )
    return f"""You are an authorized CTF worker. Stay inside the supplied task scope.

TASK={task_json}
PROFILE={profile_json}

PLAYBOOK
{skill_text}

RULES
- Work only in /workspace and explicit task endpoints. Target traffic requires allow_target_operations and the scoped web gate.
- Never bypass provider, workspace, network, permission, or verifier safeguards.
- {escalation}
- Save raw output before summarizing. Never alter flags, hashes, addresses, offsets, payload bytes, credentials, commands, or decisive errors.
- Keep one reproducible script when interaction is required. Record one compact ledger entry with commands, PoC paths, key output, reproduction steps, and candidates.
- Never request CTFd credentials. A separate verifier submits reproduced candidates.
- Finish with five lines: Status, Finding, Evidence, Candidate, Next.
"""
