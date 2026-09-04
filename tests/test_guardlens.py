from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ssophiz_ctf.guardlens import FunctionRecord, analyze, load_functions, main


class GuardLensTests(unittest.TestCase):
    def test_missing_peer_guard_is_ranked_with_evidence(self) -> None:
        functions = [
            FunctionRecord("read_profile", family="profile", pseudocode="authorize(user); return readfile(path);"),
            FunctionRecord("update_profile", family="profile", pseudocode="access_check(user); update(record);"),
            FunctionRecord("delete_profile", family="profile", pseudocode="delete(record);", address="0x401250"),
        ]
        report = analyze(functions)
        candidate = next(item for item in report.candidates if item.function == "delete_profile")
        self.assertEqual(candidate.missing_guard, "authorization")
        self.assertEqual(candidate.address, "0x401250")
        self.assertIn("state_change", candidate.sensitive_operations)
        self.assertGreaterEqual(candidate.confidence, 0.75)

    def test_no_finding_without_sensitive_operation(self) -> None:
        report = analyze([
            FunctionRecord("show_one", family="show", pseudocode="authorize(user); return 1;"),
            FunctionRecord("show_two", family="show", pseudocode="permission_check(user); return 2;"),
            FunctionRecord("show_three", family="show", pseudocode="return 3;"),
        ])
        self.assertEqual(report.candidates, [])

    def test_singleton_family_is_diagnostic_only(self) -> None:
        report = analyze([FunctionRecord("only", pseudocode="system(cmd);")])
        self.assertEqual(report.candidates, [])
        self.assertTrue(report.diagnostics)

    def test_cli_writes_machine_readable_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "functions.json"
            output = root / "report.json"
            source.write_text(json.dumps({"functions": [
                {"name": "a", "family": "ops", "pseudocode": "is_admin(user); update(x);"},
                {"name": "b", "family": "ops", "pseudocode": "is_root(user); delete(x);"},
                {"name": "c", "family": "ops", "pseudocode": "delete(x);"},
            ]}), encoding="utf-8")
            self.assertEqual(main([str(source), "--output", str(output)]), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "guardlens/v1")
            self.assertEqual(payload["candidates"][0]["function"], "c")

    def test_invalid_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_functions(path)


if __name__ == "__main__":
    unittest.main()
