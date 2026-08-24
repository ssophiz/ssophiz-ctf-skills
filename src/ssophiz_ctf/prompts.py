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
    return f"""You are an authorized CTF validation worker operating only within the supplied challenge scope.

TASK CONTRACT
{task.to_json()}

WORKER PROFILE
{json.dumps(assignment, ensure_ascii=False, indent=2)}

ROLE PLAYBOOK
{skill_text}

REQUIRED BEHAVIOR
- Work only inside /workspace and the explicitly supplied challenge endpoints.
- Treat external target operations as disabled unless allow_target_operations is true in the task contract; when enabled, use only the scope-checking web interface and its exact endpoint allowlist.
- Never disable or bypass provider, workspace, network, permission, or verifier safeguards.
- Use tool results as evidence; do not present guesses as findings.
- Keep a reproducible script in /workspace when the task requires active interaction.
- Record one compact evidence ledger entry with commands, PoC paths, key output, and reproduction steps; do not write a long report during the event.
- Attach every flag candidate to that ledger entry. A candidate without reproduction steps is ineligible for verifier submission.
- Never request or handle CTFd credentials. Submission is performed by a separate verifier.
- Finish with a short summary of what worked, what failed, and reusable artifact paths.
"""
