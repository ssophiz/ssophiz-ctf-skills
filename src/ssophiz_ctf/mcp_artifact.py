from __future__ import annotations

from pathlib import PurePosixPath

from mcp.server.fastmcp import FastMCP

from .archives import ArchiveLimits, prepare_archive
from .hwpx import extract_hwpx_text
from .mcp_common import current_store
from .sandbox import list_workspace_files, read_workspace_file, safe_workspace_path, write_workspace_file


mcp = FastMCP(
    "SSophiz CTF Artifact",
    instructions="Workspace-confined artifact exchange. Paths cannot escape the registered task workspace.",
)


@mcp.tool()
def list_artifacts(task_id: str, relative_path: str = ".") -> list[str]:
    """List files under a task workspace path."""
    store = current_store()
    try:
        return list_workspace_files(store.get_task(task_id).workspace, relative_path)
    finally:
        store.close()


@mcp.tool()
def read_artifact_text(task_id: str, relative_path: str, max_chars: int = 20000) -> str:
    """Read UTF-8-compatible text inside the task workspace."""
    store = current_store()
    try:
        return read_workspace_file(store.get_task(task_id).workspace, relative_path, max_chars)
    finally:
        store.close()


@mcp.tool()
def write_note(task_id: str, worker: str, relative_path: str, content: str) -> dict[str, str]:
    """Write a worker note or reproduction script inside notes/<worker>/ only."""
    cleaned_worker = "".join(char if char.isalnum() or char in "-_" else "-" for char in worker)[:64] or "worker"
    candidate = PurePosixPath(relative_path.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts or str(candidate) in {"", "."}:
        raise ValueError("relative_path must stay below the worker note directory")
    scoped_path = f"notes/{cleaned_worker}/{relative_path}"
    store = current_store()
    try:
        path = write_workspace_file(store.get_task(task_id).workspace, scoped_path, content)
        return {"path": path}
    finally:
        store.close()


@mcp.tool()
def inventory_nested_archive(task_id: str, relative_path: str, max_depth: int = 4) -> dict[str, object]:
    """Safely inventory ZIP/TAR/7z contents, including nested archives, without persisting extraction."""
    store = current_store()
    try:
        workspace = store.get_task(task_id).workspace
    finally:
        store.close()
    source = safe_workspace_path(workspace, relative_path)
    return prepare_archive(source, limits=ArchiveLimits(max_depth=max_depth))


@mcp.tool()
def extract_nested_archive(
    task_id: str,
    relative_path: str,
    output_relative_path: str,
    max_depth: int = 4,
) -> dict[str, object]:
    """Safely extract nested archives under a new workspace path and write provenance.json."""
    store = current_store()
    try:
        workspace = store.get_task(task_id).workspace
    finally:
        store.close()
    source = safe_workspace_path(workspace, relative_path)
    destination = safe_workspace_path(workspace, output_relative_path)
    return prepare_archive(source, destination, limits=ArchiveLimits(max_depth=max_depth))


@mcp.tool()
def extract_hwpx(task_id: str, relative_path: str, output_relative_path: str = "") -> dict[str, object]:
    """Extract text from HWPX Contents/section*.xml inside the task workspace."""
    store = current_store()
    try:
        workspace = store.get_task(task_id).workspace
    finally:
        store.close()
    source = safe_workspace_path(workspace, relative_path)
    output = safe_workspace_path(workspace, output_relative_path) if output_relative_path else None
    return extract_hwpx_text(source, output)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
