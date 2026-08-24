from __future__ import annotations

import unittest
import json
from pathlib import Path

from ssophiz_ctf.mcp_artifact import mcp as artifact_mcp
from ssophiz_ctf.mcp_control import mcp as control_mcp
from ssophiz_ctf.mcp_ida import mcp as ida_mcp
from ssophiz_ctf.mcp_sandbox import mcp as sandbox_mcp
from ssophiz_ctf.mcp_verifier import mcp as verifier_mcp
from ssophiz_ctf.mcp_web import mcp as web_mcp


class MCPTopologyTests(unittest.TestCase):
    def test_servers_are_role_separated(self) -> None:
        self.assertEqual(control_mcp.name, "SSophiz CTF Control")
        self.assertEqual(artifact_mcp.name, "SSophiz CTF Artifact")
        self.assertEqual(sandbox_mcp.name, "SSophiz CTF Sandbox")
        self.assertEqual(ida_mcp.name, "SSophiz CTF IDA")
        self.assertEqual(verifier_mcp.name, "SSophiz CTF Verifier")
        self.assertEqual(web_mcp.name, "SSophiz CTF Web")

    def test_project_mcp_config_registers_scoped_web_server(self) -> None:
        root = Path(__file__).parents[1]
        config = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
        servers = config["mcpServers"]
        self.assertIn("ctf-web", servers)
        self.assertEqual(servers["ctf-web"]["args"], ["-m", "ssophiz_ctf.mcp_web"])
        self.assertEqual(servers["ctf-web"]["command"], "scripts\\project-venv-python.cmd")
        roles = json.loads((root / "config" / "harness.example.json").read_text(encoding="utf-8"))["mcp_roles"]
        self.assertIn("ctf-web", roles["web"])
        self.assertNotIn("browser", roles["web"])
        self.assertNotIn("web-proxy", roles["web"])


if __name__ == "__main__":
    unittest.main()
