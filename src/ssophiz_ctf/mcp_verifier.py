from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from .contracts import classify_flag_candidate
from .ctfd import CTFdClient
from .mcp_common import current_config, current_store


mcp = FastMCP(
    "SSophiz CTF Verifier",
    instructions="Verifier-only flag submission surface. Never connect this server to solver profiles.",
)


@mcp.tool()
def list_pending_candidates(task_id: str) -> list[dict[str, Any]]:
    """List pending candidates that have attached reproduction evidence."""
    store = current_store()
    try:
        return [
            item
            for item in store.list_candidates(task_id)
            if item["status"] == "pending" and store.candidate_has_reproduction(str(item["id"]))
        ]
    finally:
        store.close()


@mcp.tool()
def verify_candidate(candidate_id: str) -> dict[str, str]:
    """Submit a candidate only when SSOPHIZ_ENABLE_SUBMIT=1."""
    if os.getenv("SSOPHIZ_ENABLE_SUBMIT") != "1":
        raise PermissionError("Flag submission is disabled")
    config = current_config()
    store = current_store()
    try:
        candidate = store.get_candidate(candidate_id)
        if not store.candidate_has_reproduction(candidate_id):
            raise ValueError("Candidate has no attached reproduction evidence")
        classification = classify_flag_candidate(str(candidate["value"]))
        if not classification.submit_eligible:
            raise ValueError(f"Candidate is classified as {classification.kind}; refusing submission")
        task = store.get_task(str(candidate["task_id"]))
        if task.platform_challenge_id is None:
            raise ValueError("Task has no CTFd challenge id")
        result = CTFdClient.from_config(config.data["ctfd"]).submit_flag(task.platform_challenge_id, str(candidate["value"]))
        store.update_candidate(candidate_id, result.status, result.message)
        if result.status == "correct":
            store.update_task_status(task.id, "completed")
        return {"candidate_id": candidate_id, "status": result.status, "message": result.message}
    finally:
        store.close()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
