from __future__ import annotations

import re
import stat
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .archives import ArchivePreparationError, _safe_parts


_SECTION = re.compile(r"^Contents/section(\d+)\.xml$", re.IGNORECASE)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _section_text(xml_data: bytes) -> str:
    root = ElementTree.fromstring(xml_data)
    paragraphs: list[str] = []
    for paragraph in (element for element in root.iter() if _local_name(element.tag) == "p"):
        fragments = [element.text or "" for element in paragraph.iter() if _local_name(element.tag) == "t"]
        text = "".join(fragments).strip()
        if text:
            paragraphs.append(text)
    if not paragraphs:
        paragraphs = [
            (element.text or "").strip()
            for element in root.iter()
            if _local_name(element.tag) == "t" and (element.text or "").strip()
        ]
    return "\n".join(paragraphs)


def extract_hwpx_text(source: str | Path, output: str | Path | None = None, *, max_bytes: int = 64 * 1024 * 1024) -> dict[str, object]:
    """Extract paragraph text from HWPX section XML without unpacking the ZIP."""

    path = Path(source).resolve()
    if not path.is_file():
        raise FileNotFoundError(source)
    if not 1 <= max_bytes <= 512 * 1024 * 1024:
        raise ValueError("max_bytes is outside the supported range")
    sections: list[tuple[int, zipfile.ZipInfo]] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            normalized = "/".join(_safe_parts(info.filename))
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
                raise ArchivePreparationError(f"HWPX symlink is not allowed: {info.filename}")
            match = _SECTION.fullmatch(normalized)
            if match:
                sections.append((int(match.group(1)), info))
        if not sections:
            raise ValueError("HWPX contains no Contents/section*.xml files")
        total = sum(info.file_size for _, info in sections)
        if total > max_bytes:
            raise ArchivePreparationError("HWPX section XML exceeds the extraction limit")
        rendered: list[str] = []
        names: list[str] = []
        for _, info in sorted(sections, key=lambda item: item[0]):
            names.append(info.filename)
            text = _section_text(archive.read(info))
            if text:
                rendered.append(text)
    combined = "\n\n".join(rendered)
    result: dict[str, object] = {
        "source": str(path),
        "sections": names,
        "text": combined,
        "characters": len(combined),
    }
    if output is not None:
        target = Path(output).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(target)
        target.write_text(combined, encoding="utf-8")
        result["output"] = str(target)
    return result
