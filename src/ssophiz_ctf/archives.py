from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unicodedata
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO


class ArchivePreparationError(ValueError):
    """Raised when an archive is unsafe or exceeds a preparation bound."""


@dataclass(frozen=True)
class ArchiveLimits:
    max_depth: int = 4
    max_members: int = 10_000
    max_member_bytes: int = 256 * 1024 * 1024
    max_total_bytes: int = 1024 * 1024 * 1024
    max_compression_ratio: int = 1_000

    def validate(self) -> None:
        if not 0 <= self.max_depth <= 8:
            raise ValueError("max_depth must be between 0 and 8")
        if not 1 <= self.max_members <= 50_000:
            raise ValueError("max_members must be between 1 and 50000")
        if not 1 <= self.max_member_bytes <= 2 * 1024 * 1024 * 1024:
            raise ValueError("max_member_bytes is outside the supported range")
        if not 1 <= self.max_total_bytes <= 4 * 1024 * 1024 * 1024:
            raise ValueError("max_total_bytes is outside the supported range")
        if not 1 <= self.max_compression_ratio <= 10_000:
            raise ValueError("max_compression_ratio is outside the supported range")


@dataclass(frozen=True)
class _Member:
    name: str
    size: int
    compressed_size: int
    is_dir: bool = False


class _Budget:
    def __init__(self, limits: ArchiveLimits):
        self.limits = limits
        self.members = 0
        self.total_bytes = 0

    def consume(self, member: _Member) -> None:
        self.members += 1
        self.total_bytes += member.size
        if self.members > self.limits.max_members:
            raise ArchivePreparationError("archive member limit exceeded")
        if member.size > self.limits.max_member_bytes:
            raise ArchivePreparationError(f"archive member is too large: {member.name}")
        if self.total_bytes > self.limits.max_total_bytes:
            raise ArchivePreparationError("archive expanded-byte limit exceeded")
        if member.size and member.compressed_size == 0:
            raise ArchivePreparationError(f"invalid zero compressed size for {member.name}")
        if member.compressed_size and member.size > member.compressed_size * self.limits.max_compression_ratio:
            raise ArchivePreparationError(f"compression ratio limit exceeded for {member.name}")


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _safe_parts(name: str) -> tuple[str, ...]:
    normalized = name.replace("\\", "/")
    if "\x00" in normalized:
        raise ArchivePreparationError("archive member contains a NUL byte")
    path = PurePosixPath(normalized)
    parts = tuple(part for part in path.parts if part not in {"", "."})
    if path.is_absolute() or not parts or any(part == ".." for part in parts):
        raise ArchivePreparationError(f"archive member escapes extraction root: {name}")
    windows_devices = {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)), *(f"LPT{index}" for index in range(1, 10))}
    for part in parts:
        if ":" in part:
            raise ArchivePreparationError(f"archive member contains a drive or stream prefix: {name}")
        if part.rstrip(" .") != part or part.split(".", 1)[0].upper() in windows_devices:
            raise ArchivePreparationError(f"archive member is not portable to a safe Windows path: {name}")
    return parts


def _safe_target(root: Path, name: str) -> Path:
    target = (root.joinpath(*_safe_parts(name))).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ArchivePreparationError(f"archive member escapes extraction root: {name}")
    return target


def _copy_bounded(source: BinaryIO, target: Path, expected_size: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with target.open("xb") as output:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            written += len(chunk)
            if written > expected_size:
                raise ArchivePreparationError(f"archive member expanded past declared size: {target.name}")
            output.write(chunk)
    if written != expected_size:
        raise ArchivePreparationError(f"archive member size mismatch: {target.name}")


def _archive_kind(path: Path) -> str | None:
    try:
        if zipfile.is_zipfile(path):
            return "zip"
    except OSError:
        return None
    try:
        if tarfile.is_tarfile(path):
            return "tar"
    except (OSError, tarfile.TarError):
        pass
    if path.suffix.lower() == ".7z":
        return "7z"
    return None


class _Preparer:
    def __init__(self, limits: ArchiveLimits):
        self.limits = limits
        self.budget = _Budget(limits)
        self.records: list[dict[str, Any]] = []

    def walk(self, archive: Path, destination: Path, chain: list[str], depth: int) -> None:
        if depth > self.limits.max_depth:
            raise ArchivePreparationError("nested archive depth limit exceeded")
        kind = _archive_kind(archive)
        if kind is None:
            raise ArchivePreparationError(f"unsupported archive format: {archive.name}")
        self.records.append(
            {
                "record_type": "archive",
                "archive_chain": list(chain),
                "depth": depth,
                "format": kind,
                "sha256": _sha256(archive),
                "size": archive.stat().st_size,
            }
        )
        destination.mkdir(parents=True, exist_ok=False)
        members = getattr(self, f"_extract_{kind}")(archive, destination)
        for member in members:
            target = _safe_target(destination, member.name)
            relative = "/".join(_safe_parts(member.name))
            record = {
                "record_type": "member",
                "archive_chain": list(chain),
                "depth": depth,
                "path": relative,
                "size": member.size,
                "compressed_size": member.compressed_size,
                "kind": "directory" if member.is_dir else "file",
            }
            if not member.is_dir:
                record["sha256"] = _sha256(target)
            self.records.append(record)
        for member in members:
            if member.is_dir:
                continue
            target = _safe_target(destination, member.name)
            if _archive_kind(target) is None:
                continue
            if depth == self.limits.max_depth:
                raise ArchivePreparationError("nested archive depth limit exceeded")
            nested_destination = target.with_name(f"{target.name}.contents")
            nested_chain = [*chain, "/".join(_safe_parts(member.name))]
            self.walk(target, nested_destination, nested_chain, depth + 1)

    def _validate_members(self, members: list[_Member]) -> None:
        seen: set[str] = set()
        for member in members:
            normalized = "/".join(_safe_parts(member.name))
            collision_key = unicodedata.normalize("NFC", normalized).casefold()
            if collision_key in seen:
                raise ArchivePreparationError(f"duplicate archive member path: {member.name}")
            seen.add(collision_key)
            self.budget.consume(member)

    def _extract_zip(self, archive: Path, destination: Path) -> list[_Member]:
        with zipfile.ZipFile(archive) as handle:
            infos = handle.infolist()
            members: list[_Member] = []
            for info in infos:
                unix_mode = (info.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(unix_mode)
                if file_type == stat.S_IFLNK:
                    raise ArchivePreparationError(f"archive symlink is not allowed: {info.filename}")
                if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ArchivePreparationError(f"archive special file is not allowed: {info.filename}")
                members.append(_Member(info.filename, info.file_size, info.compress_size, info.is_dir()))
            self._validate_members(members)
            for info, member in zip(infos, members, strict=True):
                target = _safe_target(destination, member.name)
                if member.is_dir:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                with handle.open(info, "r") as source:
                    _copy_bounded(source, target, member.size)
            return members

    def _extract_tar(self, archive: Path, destination: Path) -> list[_Member]:
        with tarfile.open(archive, "r:*") as handle:
            infos = [
                info
                for info in handle.getmembers()
                if not (info.isdir() and info.name.replace("\\", "/").rstrip("/") in {"", "."})
            ]
            members: list[_Member] = []
            for info in infos:
                if not (info.isfile() or info.isdir()):
                    raise ArchivePreparationError(f"archive link or special file is not allowed: {info.name}")
                members.append(_Member(info.name, info.size, info.size, info.isdir()))
            self._validate_members(members)
            for info, member in zip(infos, members, strict=True):
                target = _safe_target(destination, member.name)
                if member.is_dir:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                source = handle.extractfile(info)
                if source is None:
                    raise ArchivePreparationError(f"could not read archive member: {info.name}")
                with source:
                    _copy_bounded(source, target, member.size)
            return members

    def _extract_7z(self, archive: Path, destination: Path) -> list[_Member]:
        executable = shutil.which("7zz") or shutil.which("7z")
        if not executable:
            raise ArchivePreparationError("7z or 7zz is required to prepare .7z archives")
        listing = subprocess.run(
            [executable, "l", "-slt", "-ba", str(archive)],
            text=True,
            errors="replace",
            capture_output=True,
            check=False,
            timeout=60,
        )
        if listing.returncode != 0:
            raise ArchivePreparationError(listing.stderr.strip() or "7z inventory failed")
        members: list[_Member] = []
        for block in listing.stdout.replace("\r\n", "\n").split("\n\n"):
            fields: dict[str, str] = {}
            for line in block.splitlines():
                if " = " in line:
                    key, value = line.split(" = ", 1)
                    fields[key.strip()] = value.strip()
            if "Path" not in fields:
                continue
            attributes = fields.get("Attributes", "")
            if "L" in attributes.upper():
                raise ArchivePreparationError(f"archive symlink is not allowed: {fields['Path']}")
            members.append(
                _Member(
                    fields["Path"],
                    int(fields.get("Size", "0") or 0),
                    int(fields.get("Packed Size", "0") or 0) or int(fields.get("Size", "0") or 0),
                    attributes.upper().startswith("D"),
                )
            )
        self._validate_members(members)
        with tempfile.TemporaryDirectory(prefix="ssophiz-7z-") as temporary:
            stage = Path(temporary).resolve()
            extraction = subprocess.run(
                [executable, "x", "-y", "-bd", f"-o{stage}", str(archive)],
                text=True,
                errors="replace",
                capture_output=True,
                check=False,
                timeout=120,
            )
            if extraction.returncode != 0:
                raise ArchivePreparationError(extraction.stderr.strip() or "7z extraction failed")
            for member in members:
                staged = _safe_target(stage, member.name)
                target = _safe_target(destination, member.name)
                if staged.is_symlink() or (staged.exists() and not staged.resolve().is_relative_to(stage)):
                    raise ArchivePreparationError(f"archive link is not allowed: {member.name}")
                if member.is_dir:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not staged.is_file():
                    raise ArchivePreparationError(f"7z did not produce a regular file: {member.name}")
                with staged.open("rb") as source:
                    _copy_bounded(source, target, member.size)
        return members


def prepare_archive(
    source: str | Path,
    destination: str | Path | None = None,
    *,
    limits: ArchiveLimits | None = None,
) -> dict[str, Any]:
    """Safely inventory a nested archive and optionally persist extracted contents.

    Extraction is built in a private staging directory and moved into ``destination``
    only after every nested member passes traversal, type, and expansion checks.
    """

    archive = Path(source).resolve()
    if not archive.is_file():
        raise FileNotFoundError(source)
    selected_limits = limits or ArchiveLimits()
    selected_limits.validate()
    final_destination = Path(destination).resolve() if destination is not None else None
    if final_destination is not None and final_destination.exists():
        raise FileExistsError(f"archive destination already exists: {final_destination}")
    parent = final_destination.parent if final_destination is not None else None
    if parent is not None:
        parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ssophiz-archive-", dir=parent) as temporary:
        staging = Path(temporary) / "prepared"
        staging.mkdir()
        preparer = _Preparer(selected_limits)
        preparer.walk(archive, staging / "contents", [archive.name], 0)
        manifest = {
            "source": str(archive),
            "source_sha256": _sha256(archive),
            "generated_at": datetime.now(UTC).isoformat(),
            "limits": asdict(selected_limits),
            "records": preparer.records,
            "member_count": preparer.budget.members,
            "expanded_bytes": preparer.budget.total_bytes,
            "extraction_root": str(final_destination / "contents") if final_destination is not None else None,
        }
        (staging / "provenance.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if final_destination is not None:
            os.replace(staging, final_destination)
            manifest["provenance_path"] = str(final_destination / "provenance.json")
        return manifest
