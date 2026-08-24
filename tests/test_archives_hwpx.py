from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from ssophiz_ctf.archives import ArchiveLimits, ArchivePreparationError, prepare_archive
from ssophiz_ctf.hwpx import extract_hwpx_text


class ArchivePreparationTests(unittest.TestCase):
    def test_nested_zip_inventory_and_extraction_include_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested_bytes = io.BytesIO()
            with zipfile.ZipFile(nested_bytes, "w", zipfile.ZIP_DEFLATED) as nested:
                nested.writestr("payload.txt", "nested evidence")
            source = root / "outer.zip"
            with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as outer:
                outer.writestr("readme.txt", "outer evidence")
                outer.writestr("bundle/inner.zip", nested_bytes.getvalue())

            inventory = prepare_archive(source)
            archives = [item for item in inventory["records"] if item["record_type"] == "archive"]
            self.assertEqual(len(archives), 2)
            self.assertEqual(archives[1]["archive_chain"], ["outer.zip", "bundle/inner.zip"])

            destination = root / "prepared"
            result = prepare_archive(source, destination)
            nested_payload = destination / "contents" / "bundle" / "inner.zip.contents" / "payload.txt"
            self.assertEqual(nested_payload.read_text(encoding="utf-8"), "nested evidence")
            provenance = json.loads((destination / "provenance.json").read_text(encoding="utf-8"))
            self.assertEqual(provenance["source_sha256"], result["source_sha256"])

    def test_zip_slip_is_rejected_without_persisting_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "bad.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("../escape.txt", "no")
            destination = root / "prepared"
            with self.assertRaises(ArchivePreparationError):
                prepare_archive(source, destination)
            self.assertFalse(destination.exists())
            self.assertFalse((root / "escape.txt").exists())

    def test_nested_depth_is_a_rejection_not_a_silent_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = io.BytesIO()
            with zipfile.ZipFile(nested, "w") as archive:
                archive.writestr("value.txt", "x")
            source = root / "outer.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("inner.zip", nested.getvalue())
            with self.assertRaises(ArchivePreparationError):
                prepare_archive(source, limits=ArchiveLimits(max_depth=0))


class HWPXTests(unittest.TestCase):
    def test_extracts_ordered_section_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "writeup.hwpx"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr(
                    "Contents/section1.xml",
                    '<hp:sec xmlns:hp="urn:test"><hp:p><hp:run><hp:t>Second</hp:t></hp:run></hp:p></hp:sec>',
                )
                archive.writestr(
                    "Contents/section0.xml",
                    '<hp:sec xmlns:hp="urn:test"><hp:p><hp:run><hp:t>First</hp:t></hp:run></hp:p></hp:sec>',
                )
            result = extract_hwpx_text(source)
            self.assertEqual(result["text"], "First\n\nSecond")
            self.assertEqual(result["sections"], ["Contents/section0.xml", "Contents/section1.xml"])


if __name__ == "__main__":
    unittest.main()
