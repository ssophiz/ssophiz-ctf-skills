from __future__ import annotations

import unittest

from ssophiz_ctf.contracts import TaskEnvelope
from ssophiz_ctf.orca_runtime import build_orca_plan, build_orca_worker_spec


class OrcaPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.task = TaskEnvelope.create(name="demo", category="pwn", description="buffer overflow", workspace="C:/tmp/task")
        self.assignments = [
            {"profile": "triage", "adapter": "orca", "agent": "codex", "model": "gpt-5.6-sol", "effort": "high", "role": "pwn", "focus": "triage", "wave": 0},
            {"profile": "exploit", "adapter": "orca", "agent": "codex", "model": "gpt-5.6-sol", "effort": "xhigh", "role": "pwn", "focus": "exploit", "wave": 0},
            {"profile": "review", "adapter": "openai_compatible", "model": "x", "role": "pwn", "focus": "review", "wave": 1},
        ]

    def test_each_orca_specialist_gets_a_distinct_task(self) -> None:
        commands = build_orca_plan(self.task, self.assignments)
        purposes = [item.purpose for item in commands]
        self.assertIn("create_triage_task", purposes)
        self.assertIn("create_exploit_task", purposes)
        self.assertIn("start_triage", purposes)
        self.assertIn("start_exploit", purposes)
        self.assertNotIn("start_review", purposes)

    def test_worker_spec_contains_scoped_prompt(self) -> None:
        spec = build_orca_worker_spec(self.task, self.assignments[0])
        self.assertEqual(spec["control_task_id"], self.task.id)
        self.assertIn("authorized CTF", spec["instructions"])


if __name__ == "__main__":
    unittest.main()
