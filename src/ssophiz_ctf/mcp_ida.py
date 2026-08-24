from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .mcp_common import current_store


IDA_HOST = os.getenv("SSOPHIZ_IDA_HOST", "127.0.0.1")
IDA_PORT = int(os.getenv("SSOPHIZ_IDA_PORT", "13337"))

mcp = FastMCP(
    "SSophiz CTF IDA",
    instructions=(
        "Read-only IDA analysis for an authorized CTF task. Every call requires a task_id, "
        "and the file currently open in IDA must match a registered task artifact."
    ),
)


def _rpc(method: str, *params: Any) -> Any:
    connection = http.client.HTTPConnection(IDA_HOST, IDA_PORT, timeout=30)
    payload = {"jsonrpc": "2.0", "method": method, "params": list(params), "id": 1}
    try:
        connection.request("POST", "/mcp", json.dumps(payload), {"Content-Type": "application/json"})
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()
    if "error" in data:
        error = data["error"]
        raise RuntimeError(f"IDA JSON-RPC {error.get('code')}: {error.get('message')}")
    return data.get("result")


def _guard_task(task_id: str) -> dict[str, Any]:
    store = current_store()
    try:
        task = store.get_task(task_id)
    finally:
        store.close()
    metadata = _rpc("get_metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("IDA returned invalid metadata")
    module = Path(str(metadata.get("module") or "")).name.casefold()
    allowed = {Path(name).name.casefold() for name in task.artifacts}
    if not module or module not in allowed:
        raise PermissionError(
            f"IDA has '{module or '<unknown>'}' open, but task {task_id} allows only {sorted(allowed)}"
        )
    return metadata


@mcp.tool()
def check_task_connection(task_id: str) -> dict[str, Any]:
    """Verify that IDA is connected and its open module belongs to this task."""
    return _guard_task(task_id)


@mcp.tool()
def get_metadata(task_id: str) -> dict[str, Any]:
    """Return metadata for the task-authorized module currently open in IDA."""
    return _guard_task(task_id)


@mcp.tool()
def list_functions(task_id: str, offset: int = 0, count: int = 100) -> Any:
    """List a bounded page of functions."""
    _guard_task(task_id)
    return _rpc("list_functions", max(0, offset), max(1, min(count, 500)))


@mcp.tool()
def list_imports(task_id: str, offset: int = 0, count: int = 100) -> Any:
    """List a bounded page of imports."""
    _guard_task(task_id)
    return _rpc("list_imports", max(0, offset), max(1, min(count, 500)))


@mcp.tool()
def list_strings(task_id: str, filter_text: str = "", offset: int = 0, count: int = 100) -> Any:
    """List a bounded page of strings, optionally filtered."""
    _guard_task(task_id)
    return _rpc("list_strings_filter", max(0, offset), max(1, min(count, 500)), filter_text)


@mcp.tool()
def get_function_by_name(task_id: str, name: str) -> Any:
    """Get one function by name."""
    _guard_task(task_id)
    return _rpc("get_function_by_name", name)


@mcp.tool()
def decompile_function(task_id: str, address: str) -> Any:
    """Decompile one function by address when Hex-Rays is available."""
    _guard_task(task_id)
    return _rpc("decompile_function", address)


@mcp.tool()
def disassemble_function(task_id: str, address: str) -> Any:
    """Disassemble one function by start address."""
    _guard_task(task_id)
    return _rpc("disassemble_function", address)


@mcp.tool()
def get_xrefs_to(task_id: str, address: str) -> Any:
    """Get cross-references to an address."""
    _guard_task(task_id)
    return _rpc("get_xrefs_to", address)


@mcp.tool()
def get_callees(task_id: str, function_address: str) -> Any:
    """Get callees for one function."""
    _guard_task(task_id)
    return _rpc("get_callees", function_address)


@mcp.tool()
def get_callers(task_id: str, function_address: str) -> Any:
    """Get callers for one function."""
    _guard_task(task_id)
    return _rpc("get_callers", function_address)


@mcp.tool()
def get_entry_points(task_id: str) -> Any:
    """Get module entry points."""
    _guard_task(task_id)
    return _rpc("get_entry_points")


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
