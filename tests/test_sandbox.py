from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ssophiz_ctf.sandbox import safe_workspace_path, write_workspace_file


class SandboxTests(unittest.TestCase):
    def test_workspace_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                safe_workspace_path(temporary, "../outside")

    def test_workspace_writes_inside_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = Path(write_workspace_file(temporary, "notes/test.txt", "ok"))
            self.assertEqual(result.read_text(encoding="utf-8"), "ok")


if __name__ == "__main__":
    unittest.main()
