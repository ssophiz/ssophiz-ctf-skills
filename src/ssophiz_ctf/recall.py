from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .contracts import TaskEnvelope
from .router import build_speed_plan, route_task


_SKIP_DIRS = {".git", ".harness", ".venv", "graphify-out", "node_modules"}
_CATEGORY_TERMS = {
    "pwn": "overflow rop heap race allocator kernel",
    "reverse": "reverse crackme bytecode validation decompile",
    "malware": "malware loader config c2 persistence unpack",
    "web": "web authorization injection race api session",
    "crypto": "crypto nonce rsa cipher oracle lattice",
    "forensics": "forensics pcap memory disk steganography timeline",
    "misc": "ctf protocol game automation puzzle",
}


def build_recall_query(task: TaskEnvelope) -> str:
    description = re.sub(r"\s+", " ", task.description).strip()[:320]
    return f"{task.name} {_CATEGORY_TERMS[task.category]} {description}".strip()


def _resolve_roots(config: HarnessConfig) -> list[Path]:
    project_root = config.path.parent.parent
    configured = list(config.data.get("retrieval", {}).get("roots", []))
    extra = os.getenv("SSOPHIZ_CTF_CORPUS", "")
    if extra:
        configured.extend(item for item in extra.split(os.pathsep) if item)
    roots: list[Path] = []
    for value in configured:
        if not str(value).strip():
            continue
        path = Path(str(value)).expanduser()
        path = path if path.is_absolute() else project_root / path
        path = path.resolve()
        if path.is_dir() and path not in roots:
            roots.append(path)
    return roots


def _document_count(roots: list[Path], limit: int) -> int:
    count = 0
    for root in roots:
        for directory, names, files in os.walk(root):
            names[:] = [name for name in names if name not in _SKIP_DIRS]
            count += sum(Path(name).suffix.lower() in {".md", ".txt", ".rst"} for name in files)
            if count >= limit:
                return count
    return count


def _python_search(query: str, roots: list[Path], line_limit: int) -> str:
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_]{4,}", query)]
    rows: list[str] = []
    files_seen = 0
    for root in roots:
        for path in root.rglob("*"):
            if any(part in _SKIP_DIRS for part in path.parts) or path.suffix.lower() not in {".md", ".txt", ".rst"}:
                continue
            files_seen += 1
            if files_seen > 2000:
                return "\n".join(rows)
            try:
                for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if any(term in line.lower() for term in terms):
                        rows.append(f"{path}:{number}:{line}")
                        if len(rows) >= line_limit:
                            return "\n".join(rows)
            except OSError:
                continue
    return "\n".join(rows)


def recall_prior_notes(task: TaskEnvelope, config: HarnessConfig) -> dict[str, Any]:
    settings = config.data.get("retrieval", {})
    roots = _resolve_roots(config)
    if not roots:
        return {"status": "disabled", "reason": "no existing retrieval roots", "results": ""}

    top_k = max(1, min(int(settings.get("top_k", 5)), 10))
    snippet_lines = max(1, min(int(settings.get("max_snippet_lines", 12)), 40))
    threshold = max(1, int(settings.get("semantic_file_threshold", 80)))
    query = build_recall_query(task)
    document_count = _document_count(roots, threshold + 1)
    use_semble = document_count > threshold and shutil.which("semble") is not None
    chunks: list[str] = []

    if use_semble:
        for root in roots:
            try:
                completed = subprocess.run(
                    [
                        "semble",
                        "search",
                        query,
                        str(root),
                        "--content",
                        "docs",
                        "--top-k",
                        str(top_k),
                        "--max-snippet-lines",
                        str(snippet_lines),
                    ],
                    text=True,
                    errors="replace",
                    capture_output=True,
                    check=False,
                    timeout=120,
                )
                output = completed.stdout.strip() or completed.stderr.strip()
                if completed.returncode == 0 and output:
                    chunks.append(f"## {root}\n{output}")
            except (OSError, subprocess.TimeoutExpired):
                continue
        if chunks:
            tool = "semble"
        else:
            chunks.append(_python_search(query, roots, top_k * snippet_lines))
            tool = "python-fallback"
    else:
        line_limit = top_k * snippet_lines
        rg = shutil.which("rg")
        if rg:
            terms = list(dict.fromkeys(re.findall(r"[A-Za-z0-9_]{4,}", query)))[:24]
            pattern = "|".join(re.escape(term) for term in terms)
            for root in roots:
                completed = subprocess.run(
                    [rg, "-n", "-i", "-g", "*.md", "-g", "*.txt", "-g", "*.rst", pattern, str(root)],
                    text=True,
                    errors="replace",
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
                lines = completed.stdout.splitlines()[:line_limit]
                if lines:
                    chunks.append(f"## {root}\n" + "\n".join(lines))
            tool = "rg"
        else:
            chunks.append(_python_search(query, roots, line_limit))
            tool = "python"

    return {
        "status": "ready",
        "tool": tool,
        "query": query,
        "roots": [str(root) for root in roots],
        "document_count_lower_bound": document_count,
        "results": "\n\n".join(chunk for chunk in chunks if chunk).strip(),
    }


def prepare_kickoff(task: TaskEnvelope, config: HarnessConfig) -> dict[str, Any]:
    workspace = Path(task.workspace)
    notes = workspace / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    recall = recall_prior_notes(task, config)
    prior_path = notes / "prior-notes.txt"
    if recall.get("results"):
        prior_path.write_text(str(recall["results"]), encoding="utf-8")
        recall["evidence_path"] = str(prior_path.relative_to(workspace))
    plan = {
        "task_id": task.id,
        "speed_plan": build_speed_plan(task, route_task(task, config)),
        "recall": {key: value for key, value in recall.items() if key != "results"},
    }
    kickoff_path = notes / "kickoff.json"
    kickoff_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    plan["kickoff_path"] = str(kickoff_path.relative_to(workspace))
    return plan
