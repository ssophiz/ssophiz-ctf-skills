from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from .contracts import Finding, FlagCandidate, LedgerEntry, classify_flag_candidate
from .mcp_common import current_store


mcp = FastMCP(
    "SSophiz CTF Control",
    instructions="Task coordination and evidence exchange for authorized CTF validation. No shell or CTFd credential access.",
)


@mcp.tool()
def list_tasks(status: str = "") -> list[dict[str, Any]]:
    """List registered tasks, optionally filtered by status."""
    store = current_store()
    try:
        rows = store.list_tasks(status or None)
        for row in rows:
            row["payload"] = json.loads(row["payload"])
        return rows
    finally:
        store.close()


@mcp.tool()
def get_task(task_id: str) -> dict[str, Any]:
    """Get one sanitized task contract."""
    store = current_store()
    try:
        return store.get_task(task_id).to_dict()
    finally:
        store.close()


@mcp.tool()
def claim_task(task_id: str, worker: str) -> dict[str, str]:
    """Mark a task running and record the worker identity."""
    store = current_store()
    try:
        store.update_task_status(task_id, "running")
        store.record_event(task_id, "task_claimed", {"worker": worker})
        store.connection.commit()
        return {"task_id": task_id, "status": "running", "worker": worker}
    finally:
        store.close()


@mcp.tool()
def publish_finding(task_id: str, worker: str, summary: str, evidence: list[str], confidence: float) -> dict[str, str]:
    """Publish an evidence-backed finding for cross-agent handoff."""
    finding = Finding(task_id=task_id, worker=worker, summary=summary, evidence=evidence, confidence=confidence)
    store = current_store()
    try:
        store.add_finding(finding)
        return {"finding_id": finding.id}
    finally:
        store.close()


@mcp.tool()
def list_findings(task_id: str) -> list[dict[str, Any]]:
    """List findings for one task."""
    store = current_store()
    try:
        return store.list_findings(task_id)
    finally:
        store.close()


@mcp.tool()
def record_evidence(
    task_id: str,
    worker: str,
    summary: str,
    commands: list[str],
    poc_paths: list[str],
    key_outputs: list[str],
    reproduction_steps: list[str],
    flag_candidates: list[str] | None = None,
) -> dict[str, Any]:
    """Record one compact solver ledger entry; reproduced flags are queued automatically."""

    entry = LedgerEntry(
        task_id=task_id,
        worker=worker,
        summary=summary,
        commands=commands,
        poc_paths=poc_paths,
        key_outputs=key_outputs,
        reproduction_steps=reproduction_steps,
        flag_candidates=flag_candidates or [],
    )
    store = current_store()
    try:
        return store.add_ledger_entry(entry)
    finally:
        store.close()


@mcp.tool()
def list_evidence(task_id: str) -> list[dict[str, Any]]:
    """List compact solver evidence in chronological order for one challenge."""

    store = current_store()
    try:
        return store.list_ledger_entries(task_id)
    finally:
        store.close()


@mcp.tool()
def publish_candidate(task_id: str, worker: str, flag: str, evidence_id: str = "") -> dict[str, Any]:
    """Queue a candidate; verifier eligibility requires a ledger evidence_id with reproduction steps."""
    store = current_store()
    try:
        candidate = FlagCandidate(
            task_id=task_id,
            worker=worker,
            value=flag.strip(),
            evidence_id=evidence_id,
        )
        classification = classify_flag_candidate(candidate.value)
        return {
            "candidate_id": store.add_candidate(candidate),
            "status": "pending",
            "classification": classification.to_dict(),
        }
    finally:
        store.close()


@mcp.tool()
def list_candidates(task_id: str) -> list[dict[str, Any]]:
    """List candidate values and verifier states."""
    store = current_store()
    try:
        return store.list_candidates(task_id)
    finally:
        store.close()


@mcp.tool()
def classify_candidate(flag: str) -> dict[str, Any]:
    """Classify an apparent flag as candidate, mock, placeholder, test, or invalid."""
    return classify_flag_candidate(flag).to_dict()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
