from __future__ import annotations

import unittest

from ssophiz_ctf.contracts import (
    FlagCandidate,
    LedgerEntry,
    TaskEnvelope,
    classify_flag_candidate,
    extract_flag_candidates,
)


class ContractTests(unittest.TestCase):
    def test_task_contract_rejects_unknown_category(self) -> None:
        task = TaskEnvelope.create(name="x", category="unknown", description="desc", workspace="C:/tmp/task")
        with self.assertRaises(ValueError):
            task.validate()

    def test_flag_candidates_are_deduplicated(self) -> None:
        values = extract_flag_candidates("flag{one} text flag{one} and ENKI{two}")
        self.assertEqual(values, ["flag{one}", "ENKI{two}"])

    def test_candidate_requires_flag_shape(self) -> None:
        with self.assertRaises(ValueError):
            FlagCandidate(task_id="task_x", worker="test", value="nope").validate()

    def test_mock_and_placeholder_flags_are_not_submit_eligible(self) -> None:
        self.assertEqual(classify_flag_candidate("flag{dummy_flag}").kind, "mock")
        self.assertEqual(classify_flag_candidate("flag{replace_me}").kind, "placeholder")
        self.assertFalse(classify_flag_candidate("flag{test}").submit_eligible)
        self.assertTrue(classify_flag_candidate("CCE{8b3107a95f}").submit_eligible)

    def test_target_opt_in_requires_an_endpoint(self) -> None:
        task = TaskEnvelope.create(
            name="x",
            category="web",
            description="desc",
            workspace="C:/tmp/task",
            allow_target_operations=True,
        )
        with self.assertRaises(ValueError):
            task.validate()

    def test_ledger_candidate_requires_reproduction_steps(self) -> None:
        entry = LedgerEntry(
            task_id="task_x",
            worker="solver",
            summary="candidate",
            flag_candidates=["flag{candidate}"],
        )
        with self.assertRaises(ValueError):
            entry.validate()

    def test_ledger_rejects_long_live_report(self) -> None:
        entry = LedgerEntry(
            task_id="task_x",
            worker="solver",
            summary="x" * 501,
            commands=["solve"],
        )
        with self.assertRaises(ValueError):
            entry.validate()


if __name__ == "__main__":
    unittest.main()
