from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ssophiz_ctf.config import load_config
from ssophiz_ctf.contracts import Finding, FlagCandidate, LedgerEntry, TaskEnvelope
from ssophiz_ctf.evidence_report import build_evidence_pdf
from ssophiz_ctf.router import infer_category, route_task, select_wave
from ssophiz_ctf.state import StateStore


class StateAndRouterTests(unittest.TestCase):
    def test_state_evidence_and_candidate_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = StateStore(root / "state.db")
            task = TaskEnvelope.create(name="demo", category="pwn", description="buffer overflow", workspace=str(root / "task"))
            store.add_task(task, "ready")
            store.add_finding(Finding(task.id, "codex", "offset", ["cyclic result: 72"], 0.9))
            candidate_id = store.add_candidate(FlagCandidate(task.id, "codex", "flag{reproduced}"))
            self.assertEqual(store.get_task(task.id).name, "demo")
            self.assertEqual(len(store.list_findings(task.id)), 1)
            self.assertEqual(store.get_candidate(candidate_id)["status"], "pending")
            store.close()

    def test_compact_ledger_links_reproduction_to_candidate_and_renders_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = StateStore(root / "state.db")
            task = TaskEnvelope.create(
                name="ledger-demo",
                category="pwn",
                description="buffer overflow",
                workspace=str(root / "task"),
            )
            store.add_task(task, "running")
            legacy_candidate_id = store.add_candidate(
                FlagCandidate(task.id, "codex", "flag{reproduced}")
            )
            self.assertFalse(store.candidate_has_reproduction(legacy_candidate_id))
            receipt = store.add_ledger_entry(
                LedgerEntry(
                    task_id=task.id,
                    worker="codex",
                    summary="ret2win succeeds at offset 72",
                    commands=["python notes/codex/solve.py"],
                    poc_paths=["notes/codex/solve.py"],
                    key_outputs=["offset=72\nflag{reproduced}"],
                    reproduction_steps=["Start the challenge.", "Run the solver."],
                    flag_candidates=["flag{reproduced}"],
                )
            )
            candidate_id = receipt["candidate_ids"][0]
            self.assertEqual(candidate_id, legacy_candidate_id)
            self.assertTrue(store.candidate_has_reproduction(candidate_id))
            self.assertEqual(len(store.list_ledger_entries(task.id)), 1)
            report = build_evidence_pdf(store, root / "evidence.pdf")
            self.assertEqual(report["tasks"], 1)
            self.assertEqual(report["entries"], 1)
            self.assertTrue((root / "evidence.pdf").read_bytes().startswith(b"%PDF"))
            store.close()

    def test_schema_migrates_candidate_evidence_column(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "old.db"
            import sqlite3

            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE candidates (
                  id TEXT PRIMARY KEY, task_id TEXT NOT NULL, worker TEXT NOT NULL,
                  value TEXT NOT NULL, status TEXT NOT NULL,
                  platform_response TEXT NOT NULL, created_at TEXT NOT NULL,
                  UNIQUE(task_id, value)
                );
                """
            )
            connection.close()
            store = StateStore(database)
            columns = {
                row["name"]
                for row in store.connection.execute("PRAGMA table_info(candidates)").fetchall()
            }
            self.assertIn("evidence_id", columns)
            store.close()

    def test_router_uses_configured_profiles(self) -> None:
        config = load_config(Path(__file__).parents[1] / "config" / "harness.example.json")
        task = TaskEnvelope.create(name="web", category="web", description="HTTP endpoint", workspace="C:/tmp/task")
        assignments = route_task(task, config)
        self.assertEqual([item["profile"] for item in assignments], ["codex_triage", "codex_fast", "codex_deep"])
        self.assertEqual([item["agent"] for item in assignments], ["codex", "codex", "codex"])
        self.assertEqual([item["wave"] for item in assignments], [0, 1, 2])
        self.assertEqual([item["profile"] for item in select_wave(assignments, 0)], ["codex_triage"])
        self.assertEqual(assignments[0]["model"], "gpt-5.6-luna")
        self.assertEqual(assignments[0]["effort"], "low")
        self.assertEqual(assignments[1]["model"], "gpt-5.6-sol")
        self.assertEqual(assignments[1]["effort"], "medium")
        self.assertEqual(assignments[2]["effort"], "xhigh")
        root = Path(__file__).parents[1]
        self.assertNotIn("dangerously-skip-permissions", (root / "scripts" / "claude_opus5_proxy.cmd").read_text())
        self.assertNotIn("dangerously-skip-permissions", (root / "scripts" / "claude_opus5_proxy.sh").read_text())

    def test_category_inference_prefers_artifact_signal(self) -> None:
        self.assertEqual(infer_category("no hint", ["capture.pcapng"]), "forensics")

    def test_latency_sensitive_tasks_skip_luna_triage(self) -> None:
        config = load_config(Path(__file__).parents[1] / "config" / "harness.example.json")
        task = TaskEnvelope.create(
            name="grid racing game",
            category="misc",
            description="realtime physics bot over WebSocket",
            workspace="C:/tmp/task",
        )
        assignments = route_task(task, config)
        self.assertEqual([item["profile"] for item in assignments], ["codex_fast", "codex_deep"])
        self.assertEqual([item["wave"] for item in assignments], [0, 1])
        self.assertEqual(assignments[0]["model"], "gpt-5.6-sol")
        self.assertEqual(assignments[0]["effort"], "medium")
        self.assertTrue(all(item["fast_lane"] for item in assignments))

    def test_malware_has_a_dedicated_category(self) -> None:
        self.assertEqual(infer_category("ransomware loader with C2 config", ["sample.exe"]), "malware")


if __name__ == "__main__":
    unittest.main()
