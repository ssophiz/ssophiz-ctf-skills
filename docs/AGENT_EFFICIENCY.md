# Agent context-efficiency tools

This repository supports two optional third-party tools. They solve different problems and neither replaces challenge-specific verification.

## Ponytail

Ponytail is a Codex plugin that favors the smallest correct implementation, existing code, standard libraries, and native platform features. It can reduce unnecessary code and explanation, but it does not guarantee lower reasoning-token use on every task.

After installation, restart Codex, inspect and trust the Ponytail lifecycle hooks in `/hooks`, then select a mode:

```text
/ponytail lite
/ponytail full
/ponytail ultra
/ponytail off
```

Use `lite` for exploratory reversing and exploit research where competing hypotheses are still valuable. Use `full` for solver cleanup, harness changes, report automation, and routine fixes. Avoid using brevity as a reason to remove validation, evidence capture, or security boundaries.

## Graphify

Graphify builds a local AST-backed knowledge graph for source code. Querying the graph can be cheaper than repeatedly reading the same repository files:

```powershell
graphify . --no-viz
graphify query "Where are candidate flags validated and submitted?" --budget 1500
graphify path "record_evidence" "submit"
graphify explain "TaskEnvelope"
```

Code extraction is local and does not require an API key. Semantic extraction for documents and media may use the host agent or a separately configured provider, so it can consume tokens. Prefer the structural graph for CTF source trees and use a query budget.

The project installer writes Graphify's Codex skill under `.codex/`, adds the Graphify section to `AGENTS.md`, and registers a local hook. Machine-specific `.codex/` files and generated `graphify-out/` data are intentionally ignored by Git; run the installer on each worker PC.

## Installation

Run from the repository root:

```powershell
.\scripts\install-agent-efficiency-tools.ps1
```

When NetShare is required:

```powershell
.\scripts\install-agent-efficiency-tools.ps1 -ProxyUrl http://192.168.49.1:8282
```

The script installs the versions in `config/agent-tools.lock.json`, enables Codex multi-agent support for Graphify, performs a project-scoped Graphify registration, and verifies both tools.

## CTF privacy boundary

- Do not build or commit graphs containing flags, supplied credentials, private write-ups, or live-event cookies.
- Keep `graphify-out/`, `.codex/`, raw challenge workspaces, dumps, and evidence ledgers untracked.
- Run Graphify on the sanitized harness repository or an isolated task workspace.
- Treat graph output as an index, not proof. Candidate flags still require the original solver or PoC and verifier boundary.

## Measuring value

Compare similar tasks with and without each tool. Record files read, input/output tokens, elapsed time, changed lines, and whether the result reproduced. Keep the tool only when it reduces context or implementation without lowering correctness.
