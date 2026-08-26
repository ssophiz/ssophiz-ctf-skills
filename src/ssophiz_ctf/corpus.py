from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .config import HarnessConfig


_MAX_PAGE_BYTES = 12 * 1024 * 1024
_MAX_REPO_TEXT_BYTES = 8 * 1024 * 1024
_TEXT_SUFFIXES = {
    ".c", ".cpp", ".go", ".h", ".html", ".java", ".js", ".json", ".md",
    ".php", ".ps1", ".py", ".rst", ".rs", ".sh", ".toml", ".ts", ".txt",
    ".yaml", ".yml",
}
_HISTORICAL_FLAG = re.compile(r"\b(?:[A-Z][A-Z0-9_]{2,31}|flag)\{[^{}\r\n]{4,256}\}")


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        elif not self.skip_depth and tag in {"article", "br", "div", "h1", "h2", "h3", "h4", "li", "p", "pre"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in {"article", "div", "li", "p", "pre"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        lines = (re.sub(r"[ \t]+", " ", line).strip() for line in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line)


def _project_root(config: HarnessConfig) -> Path:
    return config.path.parent.parent


def _load_manifest(config: HarnessConfig, collection: str) -> tuple[Path, dict[str, Any]]:
    path = _project_root(config) / "corpora" / collection / "sources.json"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown corpus collection: {collection}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("collection") != collection or not isinstance(manifest.get("sources"), list):
        raise ValueError(f"Invalid corpus manifest: {path}")
    return path, manifest


def collection_sources(config: HarnessConfig, collection: str) -> dict[str, Any]:
    path, manifest = _load_manifest(config, collection)
    return {"collection": collection, "manifest": str(path), "sources": manifest["sources"]}


def _collection_root(config: HarnessConfig, manifest: dict[str, Any], destination: str = "") -> Path:
    candidate = destination or os.getenv(str(manifest.get("root_env") or ""), "")
    if not candidate:
        candidate = str(manifest.get("default_root") or f".harness/corpora/{manifest['collection']}")
    path = Path(candidate).expanduser()
    return path.resolve() if path.is_absolute() else (_project_root(config) / path).resolve()


def matching_collection_roots(
    config: HarnessConfig, query: str = "", collection: str = ""
) -> list[tuple[str, Path]]:
    matches: list[tuple[str, Path]] = []
    corpus_root = _project_root(config) / "corpora"
    if not corpus_root.is_dir():
        return matches
    lowered = query.casefold()
    for manifest_path in sorted(corpus_root.glob("*/sources.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = str(manifest.get("collection") or manifest_path.parent.name)
        include = name == collection if collection else any(
            str(keyword).casefold() in lowered for keyword in manifest.get("keywords", [])
        )
        retrieval = _collection_root(config, manifest) / "retrieval" if include else None
        if retrieval and retrieval.is_dir():
            matches.append((name, retrieval.resolve()))
    return matches


def _metadata(source: dict[str, Any]) -> str:
    fields = {
        key: source[key]
        for key in ("title", "url", "provenance", "publisher", "event", "year", "categories", "license")
        if key in source
    }
    return json.dumps(fields, ensure_ascii=False, indent=2)


def _mask_historical_flags(text: str) -> str:
    return _HISTORICAL_FLAG.sub("<HISTORICAL_FLAG>", text)


def _write_retrieval(path: Path, source: dict[str, Any], text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"SOURCE_METADATA\n{_metadata(source)}\n\n{_mask_historical_flags(text)}\n", encoding="utf-8")


def _sync_page(source: dict[str, Any], raw_root: Path, retrieval_root: Path) -> dict[str, Any]:
    request = urllib.request.Request(str(source["url"]), headers={"User-Agent": "ssophiz-ctf-corpus/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        content = response.read(_MAX_PAGE_BYTES + 1)
        if len(content) > _MAX_PAGE_BYTES:
            raise ValueError(f"page exceeds {_MAX_PAGE_BYTES} bytes")
        charset = response.headers.get_content_charset() or "utf-8"
    raw_path = raw_root / "pages" / f"{source['id']}.html"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)
    parser = _HTMLText()
    parser.feed(content.decode(charset, errors="replace"))
    retrieval_path = retrieval_root / f"{source['id']}.txt"
    _write_retrieval(retrieval_path, source, parser.text())
    return {
        "raw_path": str(raw_path),
        "retrieval_path": str(retrieval_path),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _repo_text(repo: Path) -> str:
    chunks: list[str] = []
    size = 0
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        encoded_size = len(content.encode("utf-8"))
        if size + encoded_size > _MAX_REPO_TEXT_BYTES:
            break
        chunks.append(f"\n## {path.relative_to(repo)}\n{content}")
        size += encoded_size
    return "\n".join(chunks)


def _git(*args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args], text=True, errors="replace", capture_output=True, check=False, timeout=timeout
    )
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or "git command failed")
    return completed


def _sync_github(source: dict[str, Any], raw_root: Path, retrieval_root: Path) -> dict[str, Any]:
    if shutil.which("git") is None:
        raise FileNotFoundError("git is required to sync GitHub corpus sources")
    repo = raw_root / "repos" / str(source["id"])
    if repo.exists():
        if not (repo / ".git").is_dir():
            raise ValueError(f"existing corpus path is not a Git repository: {repo}")
        _git("-C", str(repo), "pull", "--ff-only")
    else:
        repo.parent.mkdir(parents=True, exist_ok=True)
        _git("clone", "--depth", "1", str(source["url"]), str(repo))
    revision = _git("-C", str(repo), "rev-parse", "HEAD", timeout=30).stdout.strip()
    retrieval_path = retrieval_root / f"{source['id']}.txt"
    _write_retrieval(retrieval_path, source, _repo_text(repo))
    return {"raw_path": str(repo), "retrieval_path": str(retrieval_path), "revision": revision}


def sync_collection(config: HarnessConfig, collection: str, destination: str = "") -> dict[str, Any]:
    manifest_path, manifest = _load_manifest(config, collection)
    root = _collection_root(config, manifest, destination)
    raw_root = root / "raw"
    retrieval_root = root / "retrieval"
    results: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        row = {"id": source.get("id"), "url": source.get("url")}
        if not source.get("ingest", True):
            results.append({**row, "status": "reference-only"})
            continue
        try:
            if source.get("type") == "page":
                detail = _sync_page(source, raw_root, retrieval_root)
            elif source.get("type") == "github":
                detail = _sync_github(source, raw_root, retrieval_root)
            else:
                raise ValueError(f"unsupported source type: {source.get('type')}")
            results.append({**row, "status": "ready", **detail})
        except (OSError, RuntimeError, ValueError) as exc:
            results.append({**row, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
    summary = {
        "collection": collection,
        "manifest": str(manifest_path),
        "root": str(root),
        "retrieval_root": str(retrieval_root),
        "status": "ready" if all(row["status"] != "failed" for row in results) else "partial",
        "sources": results,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "sync.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
