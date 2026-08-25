from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ssophiz_ctf.config import HarnessConfig
from ssophiz_ctf.contracts import TaskEnvelope
from ssophiz_ctf.recall import prepare_kickoff


class RecallTests(unittest.TestCase):
    def test_kickoff_uses_local_fallback_and_preserves_source_line(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "corpus"
            corpus.mkdir()
            note = corpus / "race.md"
            note.write_text("Use a bounded WebSocket race runner.\n", encoding="utf-8")
            config_path = root / "config" / "harness.json"
            config_path.parent.mkdir()
            config = HarnessConfig(
                data={
                    "runtime": {},
                    "profiles": {
                        "fast": {"adapter": "orca", "agent": "codex", "model": "sol", "wave": 0}
                    },
                    "routes": {"web": ["fast"]},
                    "retrieval": {"roots": [str(corpus)], "semantic_file_threshold": 80},
                },
                path=config_path,
            )
            workspace = root / "workspace"
            task = TaskEnvelope.create(
                name="race portal",
                category="web",
                description="WebSocket authorization race",
                workspace=str(workspace),
            )
            with patch("ssophiz_ctf.recall.shutil.which", return_value=None):
                result = prepare_kickoff(task, config)
            prior = workspace / result["recall"]["evidence_path"]
            self.assertIn("bounded WebSocket race runner", prior.read_text(encoding="utf-8"))
            saved = json.loads((workspace / "notes" / "kickoff.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["speed_plan"]["lane"], "staged")
            self.assertEqual(saved["recall"]["tool"], "python")


if __name__ == "__main__":
    unittest.main()
