from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .mcp_common import current_config, current_store
from .sandbox import DockerSandbox


mcp = FastMCP(
    "SSophiz CTF Sandbox",
    instructions="Execute analysis commands only inside a task-scoped Docker container.",
)


@mcp.tool()
def run_analysis(task_id: str, command: str, timeout_seconds: int = 60) -> dict[str, object]:
    """Run one bounded command in an ephemeral, task-scoped worker container."""
    config = current_config()
    store = current_store()
    try:
        task = store.get_task(task_id)
    finally:
        store.close()
    with DockerSandbox(
        task.workspace,
        str(config.runtime["worker_image"]),
        network=str(config.runtime.get("worker_network", "none")),
        allow_debug=task.category in {"pwn", "reverse"},
    ) as sandbox:
        return sandbox.run(command, timeout_seconds).to_dict()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
