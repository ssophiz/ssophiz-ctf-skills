from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ssophiz_ctf.config import HarnessConfig
from ssophiz_ctf.contracts import TaskEnvelope
from ssophiz_ctf.recall import _rank_lines, prepare_kickoff, recall_query


class RecallTests(unittest.TestCase):
    def test_rank_lines_prefers_matches_with_more_query_terms(self) -> None:
        lines = ["1:side note", "2:Side-channel oracle at /proc/self/io", "3:proc helper"]
        self.assertEqual(_rank_lines(lines, ["proc", "self", "side", "channel"], 1), [lines[1]])

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

    def test_explicit_collection_limits_recall_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            general = root / "general"
            enki = root / "enki"
            general.mkdir()
            enki.mkdir()
            (general / "note.txt").write_text("general authorization note", encoding="utf-8")
            (enki / "note.txt").write_text("ENKI full-chain authorization note", encoding="utf-8")
            config_path = root / "config" / "harness.json"
            config_path.parent.mkdir()
            config = HarnessConfig(
                data={
                    "runtime": {},
                    "profiles": {},
                    "routes": {},
                    "retrieval": {
                        "roots": [str(general)],
                        "collections": [
                            {"name": "enki", "root": str(enki), "keywords": ["cce", "enki"]}
                        ],
                    },
                },
                path=config_path,
            )
            with patch("ssophiz_ctf.recall.shutil.which", return_value=None):
                result = recall_query("authorization", config, "enki")
            self.assertEqual(result["collections"], ["enki"])
            self.assertEqual(result["roots"], [str(enki.resolve())])
            self.assertIn("ENKI full-chain", result["results"])
            self.assertNotIn("general authorization", result["results"])


if __name__ == "__main__":
    unittest.main()
