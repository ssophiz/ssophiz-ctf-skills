from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ssophiz_ctf.config import HarnessConfig
from ssophiz_ctf.corpus import collection_sources, sync_collection
from ssophiz_ctf.recall import recall_query


class CorpusTests(unittest.TestCase):
    def test_page_sync_preserves_raw_and_masks_historical_flag_in_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = root / "source.html"
            page.write_text(
                '<html><body><h1>Race</h1><p>ENKI{old_public_flag}</p>'
                '<pre>raise RuntimeError(f"request failed{resp.status_code}")</pre></body></html>',
                encoding="utf-8",
            )
            manifest_dir = root / "corpora" / "enki"
            manifest_dir.mkdir(parents=True)
            manifest = {
                "schema_version": 1,
                "collection": "enki",
                "default_root": ".harness/corpora/enki",
                "keywords": ["cce", "enki"],
                "sources": [
                    {
                        "id": "fixture",
                        "title": "Fixture",
                        "type": "page",
                        "url": page.as_uri(),
                        "provenance": "official",
                        "license": "not-stated",
                        "ingest": True,
                    }
                ],
            }
            (manifest_dir / "sources.json").write_text(json.dumps(manifest), encoding="utf-8")
            config_path = root / "config" / "harness.json"
            config_path.parent.mkdir()
            config_path.write_text("{}", encoding="utf-8")
            config = HarnessConfig(data={"retrieval": {}}, path=config_path)

            listed = collection_sources(config, "enki")
            result = sync_collection(config, "enki")

            self.assertEqual(listed["sources"][0]["id"], "fixture")
            self.assertEqual(result["status"], "ready")
            raw = root / ".harness" / "corpora" / "enki" / "raw" / "pages" / "fixture.html"
            retrieval = root / ".harness" / "corpora" / "enki" / "retrieval" / "fixture.txt"
            self.assertIn("ENKI{old_public_flag}", raw.read_text(encoding="utf-8"))
            text = retrieval.read_text(encoding="utf-8")
            self.assertIn("<HISTORICAL_FLAG>", text)
            self.assertNotIn("ENKI{old_public_flag}", text)
            self.assertIn("failed{resp.status_code}", text)
            recalled = recall_query("CCE race", config)
            self.assertEqual(recalled["collections"], ["enki"])
            self.assertIn("Race", recalled["results"])


if __name__ == "__main__":
    unittest.main()
