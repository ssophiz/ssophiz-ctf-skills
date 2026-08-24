from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from ssophiz_ctf.ctfd import CTFdClient


class CTFdTests(unittest.TestCase):
    def test_attachment_rejects_cross_origin_url(self) -> None:
        client = CTFdClient("https://ctf.example", "token")
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                client.download_attachment("https://other.example/file", Path(temporary) / "file")


if __name__ == "__main__":
    unittest.main()
