from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from .contracts import Finding, FlagCandidate, LedgerEntry, TaskEnvelope
from .prompts import build_worker_prompt, load_skill
from .sandbox import DockerSandbox, list_workspace_files, read_workspace_file, write_workspace_file
from .state import StateStore


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a command inside the isolated CTF worker container.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 600},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file in the worker workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "max_chars": {"type": "integer"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a UTF-8 text file in the worker workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files under a workspace-relative directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_evidence",
            "description": "Record one compact proof bundle; any reproduced flag candidates are queued automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "maxLength": 500},
                    "commands": {"type": "array", "items": {"type": "string"}},
                    "poc_paths": {"type": "array", "items": {"type": "string"}},
                    "key_outputs": {"type": "array", "items": {"type": "string"}},
                    "reproduction_steps": {"type": "array", "items": {"type": "string"}},
                    "flag_candidates": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "summary",
                    "commands",
                    "poc_paths",
                    "key_outputs",
                    "reproduction_steps",
                    "flag_candidates",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "publish_finding",
            "description": "Publish a finding backed by concrete evidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["summary", "evidence", "confidence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "publish_candidate",
            "description": "Legacy candidate queue; provide the evidence_id returned by record_evidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flag": {"type": "string"},
                    "evidence_id": {"type": "string"},
                },
                "required": ["flag", "evidence_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_findings",
            "description": "Read evidence-backed findings already published by other workers for this task.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 180):
        parsed = urlparse(base_url)
        loopback = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme != "https" and not loopback:
            raise ValueError("Provider base_url must use HTTPS; HTTP is allowed only for loopback Ollama")
        self.endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps({"model": self.model, "messages": messages, "tools": tools, "tool_choice": "auto"}).encode(),
            method="POST",
            headers={"Authorization": f"Bearer {self.api_key or 'ollama'}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"Provider HTTP {exc.code}: {detail[:1000]}") from exc
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError(f"Provider returned no choices: {payload}")
        return choices[0]["message"]


class APIWorker:
    def __init__(self, task: TaskEnvelope, profile_name: str, profile: dict[str, Any], store: StateStore, runtime: dict[str, Any]):
        self.task = task
        self.profile_name = profile_name
        self.profile = profile
        self.store = store
        self.runtime = runtime

    def _execute_tool(self, sandbox: DockerSandbox, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "run_command":
            return sandbox.run(str(arguments["command"]), int(arguments.get("timeout_seconds", 60))).to_dict()
        if name == "read_file":
            return {"content": read_workspace_file(self.task.workspace, str(arguments["path"]), int(arguments.get("max_chars", 20000)))}
        if name == "write_file":
            requested = str(arguments["path"]).replace("\\", "/").lstrip("/")
            requested_path = PurePosixPath(requested)
            if requested_path.is_absolute() or ".." in requested_path.parts or str(requested_path) in {"", "."}:
                raise ValueError("write_file path must remain below the worker note directory")
            scoped = f"notes/{self.profile_name}/{requested}"
            return {"path": write_workspace_file(self.task.workspace, scoped, str(arguments["content"]))}
        if name == "list_files":
            return {"files": list_workspace_files(self.task.workspace, str(arguments.get("path", ".")))}
        if name == "publish_finding":
            finding = Finding(
                task_id=self.task.id,
                worker=self.profile_name,
                summary=str(arguments["summary"]),
                evidence=[str(item) for item in arguments["evidence"]],
                confidence=float(arguments["confidence"]),
            )
            self.store.add_finding(finding)
            return {"finding_id": finding.id}
        if name == "record_evidence":
            entry = LedgerEntry(
                task_id=self.task.id,
                worker=self.profile_name,
                summary=str(arguments["summary"]),
                commands=[str(item) for item in arguments["commands"]],
                poc_paths=[str(item) for item in arguments["poc_paths"]],
                key_outputs=[str(item) for item in arguments["key_outputs"]],
                reproduction_steps=[str(item) for item in arguments["reproduction_steps"]],
                flag_candidates=[str(item).strip() for item in arguments["flag_candidates"]],
            )
            return self.store.add_ledger_entry(entry)
        if name == "publish_candidate":
            candidate = FlagCandidate(
                task_id=self.task.id,
                worker=self.profile_name,
                value=str(arguments["flag"]).strip(),
                evidence_id=str(arguments["evidence_id"]),
            )
            return {"candidate_id": self.store.add_candidate(candidate)}
        if name == "list_findings":
            return {"findings": self.store.list_findings(self.task.id)}
        raise ValueError(f"Unsupported tool: {name}")

    def run(self) -> dict[str, Any]:
        key_env = str(self.profile.get("api_key_env", ""))
        api_key = os.getenv(key_env, "") if key_env else "ollama"
        if self.profile.get("adapter") != "ollama" and not api_key:
            raise RuntimeError(f"Missing API key environment variable: {key_env}")
        skill = load_skill(self.task.category)
        assignment = {"profile": self.profile_name, **self.profile}
        prompt = build_worker_prompt(self.task, assignment, skill)
        client = OpenAICompatibleClient(str(self.profile["base_url"]), api_key, str(self.profile["model"]))
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Begin by inspecting the task files and publish only evidence-backed results."},
        ]
        max_turns = max(1, min(int(self.profile.get("max_turns", 24)), 100))
        network = str(self.runtime.get("worker_network", "none"))
        allow_debug = self.task.category in {"pwn", "reverse"}
        final_text = ""
        self.store.update_task_status(self.task.id, "running")
        try:
            with DockerSandbox(
                self.task.workspace,
                str(self.runtime["worker_image"]),
                network=network,
                allow_debug=allow_debug,
            ) as sandbox:
                for _ in range(max_turns):
                    message = client.complete(messages, TOOLS)
                    messages.append(message)
                    tool_calls = message.get("tool_calls") or []
                    if not tool_calls:
                        final_text = str(message.get("content") or "")
                        break
                    for tool_call in tool_calls:
                        function = tool_call.get("function") or {}
                        try:
                            arguments = json.loads(function.get("arguments") or "{}")
                            result = self._execute_tool(sandbox, str(function.get("name")), arguments)
                        except Exception as exc:
                            result = {"error": f"{type(exc).__name__}: {exc}"}
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.get("id"),
                                "content": json.dumps(result, ensure_ascii=False),
                            }
                        )
            self.store.record_event(self.task.id, "worker_completed", {"profile": self.profile_name})
            self.store.connection.commit()
            return {"outcome": "completed", "summary": final_text, "files": list_workspace_files(self.task.workspace)}
        except Exception:
            self.store.record_event(self.task.id, "worker_failed", {"profile": self.profile_name})
            self.store.connection.commit()
            raise
