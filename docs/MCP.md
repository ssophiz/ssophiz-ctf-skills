# MCP topology

The project provides four local stdio servers. Connect only the servers listed for the worker role in `mcp_roles` of `config/harness.json`.

| MCP server | Connect to | Purpose | Does not provide |
|---|---|---|---|
| `ctf-control-mcp` | orchestrator, Pwn, Reverse, Web | task contracts, compact evidence ledger, candidates | shell, CTFd token, submission |
| `ctf-artifact-mcp` | orchestrator, specialists | confined file read and `notes/<worker>/` write | paths outside task workspace |
| `ctf-sandbox-mcp` | Pwn, Reverse, Web | one bounded command in Docker | host shell, persistent privileged container |
| `ctf-ida-mcp` | Pwn, Reverse | read-only IDA analysis after task/artifact match | unrelated open IDBs, IDA write/patch operations |
| `ctf-verifier-mcp` | verifier process only | review and gated CTFd submit | solver access, general task tools |

External integrations are optional because their setup and trust boundaries vary.

- `ctf-ida`: wraps the locally installed `ida-pro-mcp` plugin and refuses access unless IDA's current module name matches the task artifact list. It belongs to Pwn/Reverse, not the orchestrator.
- `browser` and `web-proxy`: use only against CTFd and endpoints embedded in a task contract. They belong to orchestrator/Web.
- `search`: use for a narrow, named reverse-engineering question. It belongs to Reverse.

## Registration

The repository `.mcp.json` registers the three non-verifier local servers for Claude-compatible clients. Add the control server to Codex with:

```powershell
codex mcp add ctf-control -- ctf-control-mcp
```

Add the artifact and sandbox servers only to specialist sessions:

```powershell
codex mcp add ctf-artifact -- ctf-artifact-mcp
codex mcp add ctf-sandbox -- ctf-sandbox-mcp
codex mcp add ctf-ida -- ctf-ida-mcp
```

Use a separate verifier client/process for `ctf-verifier-mcp` and expose `SSOPHIZ_ENABLE_SUBMIT=1` only there. Do not register it in a general-purpose model session.

Solvers should prefer `record_evidence` over a prose finding at completion. It
stores the decisive command, PoC path, key output, reproduction sequence, and
candidate together; only a candidate linked to such reproduction evidence is
eligible for verifier submission.

The machine may also have the upstream `ida-pro-mcp` registered globally. CTF workers should use `ctf-ida` because it enforces the task/artifact match. Remove or disable the unrestricted upstream entry in worker-only Codex profiles if hard role isolation is required.

## WSL and Docker

Run Docker from the same Windows workspace that holds `.harness/workspaces`; Docker Desktop performs the mount. If tools must run inside WSL, use a WSL path consistently for the repository and state database. Do not mix a Windows task workspace with a separately-created WSL workspace for the same task.
