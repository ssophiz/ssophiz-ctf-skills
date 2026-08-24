from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contracts import Finding, FlagCandidate, LedgerEntry, TaskEnvelope, classify_flag_candidate, utc_now


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  status TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  worker TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);
CREATE TABLE IF NOT EXISTS evidence_ledger (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  worker TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);
CREATE TABLE IF NOT EXISTS candidates (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  worker TEXT NOT NULL,
  value TEXT NOT NULL,
  status TEXT NOT NULL,
  platform_response TEXT NOT NULL,
  evidence_id TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  UNIQUE(task_id, value),
  FOREIGN KEY(task_id) REFERENCES tasks(id)
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT,
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout=10000")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        candidate_columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(candidates)").fetchall()
        }
        if "evidence_id" not in candidate_columns:
            with self.connection:
                self.connection.execute(
                    "ALTER TABLE candidates ADD COLUMN evidence_id TEXT NOT NULL DEFAULT ''"
                )

    def close(self) -> None:
        self.connection.close()

    def add_task(self, task: TaskEnvelope, status: str = "pending") -> None:
        payload = task.to_json()
        now = utc_now()
        with self.connection:
            self.connection.execute(
                """INSERT INTO tasks(id, category, status, payload, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     category=excluded.category,
                     status=excluded.status,
                     payload=excluded.payload,
                     updated_at=excluded.updated_at""",
                (task.id, task.category, status, payload, task.created_at, now),
            )
            self.record_event(task.id, "task_upserted", {"status": status})

    def get_task(self, task_id: str) -> TaskEnvelope:
        row = self.connection.execute("SELECT payload FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown task: {task_id}")
        return TaskEnvelope.from_dict(json.loads(row["payload"]))

    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT id, category, status, payload, created_at, updated_at FROM tasks"
        params: tuple[Any, ...] = ()
        if status:
            query += " WHERE status=?"
            params = (status,)
        query += " ORDER BY created_at"
        return [dict(row) for row in self.connection.execute(query, params).fetchall()]

    def update_task_status(self, task_id: str, status: str) -> None:
        allowed = {"pending", "ready", "running", "completed", "failed", "blocked"}
        if status not in allowed:
            raise ValueError(f"Unsupported task status: {status}")
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
                (status, utc_now(), task_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown task: {task_id}")
            self.record_event(task_id, "task_status", {"status": status})

    def add_finding(self, finding: Finding) -> None:
        finding.validate()
        with self.connection:
            self.connection.execute(
                "INSERT INTO findings(id, task_id, worker, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    finding.id,
                    finding.task_id,
                    finding.worker,
                    json.dumps(asdict(finding), ensure_ascii=False),
                    finding.created_at,
                ),
            )
            self.record_event(finding.task_id, "finding_published", {"finding_id": finding.id})

    def list_findings(self, task_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT payload FROM findings WHERE task_id=? ORDER BY created_at", (task_id,)
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def add_ledger_entry(self, entry: LedgerEntry) -> dict[str, Any]:
        """Atomically preserve minimal proof and queue its reproduced candidates."""

        entry.flag_candidates = [value.strip() for value in entry.flag_candidates]
        entry.validate()
        candidate_ids: list[str] = []
        with self.connection:
            self.connection.execute(
                "INSERT INTO evidence_ledger(id, task_id, worker, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    entry.id,
                    entry.task_id,
                    entry.worker,
                    json.dumps(asdict(entry), ensure_ascii=False),
                    entry.created_at,
                ),
            )
            for value in entry.flag_candidates:
                candidate = FlagCandidate(
                    task_id=entry.task_id,
                    worker=entry.worker,
                    value=value.strip(),
                    evidence_id=entry.id,
                    created_at=entry.created_at,
                )
                candidate_ids.append(self._add_candidate_row(candidate))
            self.record_event(
                entry.task_id,
                "evidence_recorded",
                {"evidence_id": entry.id, "candidate_ids": candidate_ids},
            )
        return {"evidence_id": entry.id, "candidate_ids": candidate_ids}

    def get_ledger_entry(self, evidence_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT payload FROM evidence_ledger WHERE id=?", (evidence_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown evidence entry: {evidence_id}")
        return json.loads(row["payload"])

    def list_ledger_entries(self, task_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT payload FROM evidence_ledger WHERE task_id=? ORDER BY created_at, id",
            (task_id,),
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def add_candidate(self, candidate: FlagCandidate) -> str:
        candidate.validate()
        with self.connection:
            return self._add_candidate_row(candidate)

    def _add_candidate_row(self, candidate: FlagCandidate) -> str:
        candidate.validate()
        self.connection.execute(
            """INSERT OR IGNORE INTO candidates
               (id, task_id, worker, value, status, platform_response, evidence_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                candidate.id,
                candidate.task_id,
                candidate.worker,
                candidate.value,
                candidate.status,
                candidate.platform_response,
                candidate.evidence_id,
                candidate.created_at,
            ),
        )
        if candidate.evidence_id:
            self.connection.execute(
                """UPDATE candidates SET evidence_id=?
                   WHERE task_id=? AND value=? AND evidence_id=''""",
                (candidate.evidence_id, candidate.task_id, candidate.value),
            )
        row = self.connection.execute(
            "SELECT id FROM candidates WHERE task_id=? AND value=?",
            (candidate.task_id, candidate.value),
        ).fetchone()
        candidate_id = str(row["id"])
        self.record_event(candidate.task_id, "candidate_published", {"candidate_id": candidate_id})
        return candidate_id

    def candidate_has_reproduction(self, candidate_id: str) -> bool:
        candidate = self.get_candidate(candidate_id)
        evidence_id = str(candidate.get("evidence_id") or "")
        if not evidence_id:
            return False
        try:
            entry = self.get_ledger_entry(evidence_id)
        except KeyError:
            return False
        return bool(
            entry.get("task_id") == candidate.get("task_id")
            and entry.get("reproduction_steps")
            and candidate.get("value") in (entry.get("flag_candidates") or [])
        )

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown candidate: {candidate_id}")
        result = dict(row)
        result["classification"] = classify_flag_candidate(str(result["value"])).to_dict()
        return result

    def list_candidates(self, task_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for row in self.connection.execute(
            "SELECT * FROM candidates WHERE task_id=? ORDER BY created_at", (task_id,)
        ).fetchall():
            result = dict(row)
            result["classification"] = classify_flag_candidate(str(result["value"])).to_dict()
            results.append(result)
        return results

    def update_candidate(self, candidate_id: str, status: str, response: str) -> None:
        if status not in {"pending", "correct", "incorrect", "error"}:
            raise ValueError(f"Unsupported candidate status: {status}")
        with self.connection:
            self.connection.execute(
                "UPDATE candidates SET status=?, platform_response=? WHERE id=?",
                (status, response, candidate_id),
            )

    def record_event(self, task_id: str | None, kind: str, payload: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO events(task_id, kind, payload, created_at) VALUES (?, ?, ?, ?)",
            (task_id, kind, json.dumps(payload, ensure_ascii=False), utc_now()),
        )
