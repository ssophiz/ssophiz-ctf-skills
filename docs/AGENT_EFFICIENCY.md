# Agent context-efficiency tools

This repository supports six optional third-party tools. They solve different
problems and none replaces challenge-specific verification. The project skill
`ctf-token-efficiency` routes them without compressing exact exploit evidence.

| Tool | Use | CTF default |
|---|---|---|
| Ponytail | Avoid unnecessary implementation | On-demand skill; `lite` during research |
| Graphify | Query a source-code knowledge graph | Use for cross-file questions only |
| Headroom | Compress large model inputs and tool output | Opt-in launch wrapper |
| CodeBurn | Measure token and cost history | Baseline and milestone only |
| Caveman | Shorten natural-language output | Skill-only, explicit `lite` mode |
| Impeccable | Audit and improve frontend UI | Off for ordinary CTF solving |

## Ponytail

Ponytail is installed as an on-demand skill that favors the smallest correct implementation, existing code, standard libraries, and native platform features. It can reduce unnecessary code and explanation, but it does not guarantee lower reasoning-token use on every task.

After installation, restart the agent and invoke a mode explicitly:

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

Codex user skills are installed once under `~/.agents/skills`; Claude Code gets
its copy under `~/.claude/skills`. Do not duplicate the same user skill under
legacy `~/.codex/skills`, because Codex does not merge identical skill names and
the duplicate descriptions consume discovery context.

## Headroom

Headroom is installed in `~/.local/share/headroom-venv` so its Python
dependencies do not alter the CTF harness environment. It remains opt-in:

```powershell
.\scripts\start-codex-headroom.ps1
.\scripts\start-claude-headroom.ps1
```

Pass agent arguments after the wrapper command. Both wrappers disable Serena
registration with `--code-memory none`. The Claude wrapper also preserves
on-demand MCP tool loading with `--tool-search true`; otherwise a custom
Anthropic base URL can load every tool schema into context.

Headroom may summarize large tool results. Store the raw result first and
retrieve the original span before copying a flag candidate, hash, address,
offset, payload, credential, command, or decisive error into a PoC.

## CodeBurn

CodeBurn reads supported local agent transcripts and reports where tokens were
used. It is an observability tool, not a compressor:

```powershell
codeburn overview --no-color
codeburn web
```

Run it before a workflow change and after a comparable milestone. Do not run a
full transcript scan on every solver turn.

## Caveman

The installer copies `caveman` and `caveman-compress` into the shared Codex
skill path (`~/.agents/skills`) and Claude Code (`~/.claude/skills`). It
deliberately does not install Caveman's proxy
or automatic hooks because those can compete with Ponytail's injected context.
Use `/caveman lite` explicitly for concise updates. Do not run
`caveman-compress` on evidence, PoCs, write-ups, or files containing exact
challenge values.

## Impeccable

Impeccable is available on demand for a challenge frontend, dashboard, or
report viewer. Its large design playbooks should not be loaded for ordinary
Web, Pwn, Reverse, Crypto, Forensics, Malware, or Misc analysis.

## Additional tools considered

- WarpGrep is not enabled by default. It requires a Morph API key and can send
  repository context to an external service; the local Graphify index plus
  `rg` covers the normal CTF source-navigation path.
- Valyu is not enabled by default. It requires an external API key and is not a
  substitute for task-scoped evidence or official technical sources.
- `gh-fix-ci` and `gh-address-comments` are useful official repository
  maintenance skills, but they do not belong in live CTF worker context.
- The frontend skill is redundant with Impeccable and the existing frontend
  design skill. `stop-slop` overlaps the installed Korean humanization skill
  for reports.
- Superpowers is not installed. Its always-on planning and review workflow
  overlaps this repository's orchestrator and would add turns during a
  time-boxed competition.
- Codex Security is a separate product capability, not a local CTF skill.

## Installation

Run from the repository root:

```powershell
.\scripts\install-agent-efficiency-tools.ps1
```

When NetShare is required:

```powershell
.\scripts\install-agent-efficiency-tools.ps1 -ProxyUrl http://192.168.49.1:8282
```

The script installs the versions in `config/agent-tools.lock.json`, enables
Codex multi-agent support for Graphify, performs a project-scoped Graphify
registration, installs shared skills for Codex and Claude Code, and verifies
all command-line tools.

## CTF privacy boundary

- Do not build or commit graphs containing flags, supplied credentials, private write-ups, or live-event cookies.
- Keep `graphify-out/`, `.codex/`, raw challenge workspaces, dumps, and evidence ledgers untracked.
- Run Graphify on the sanitized harness repository or an isolated task workspace.
- Treat graph output as an index, not proof. Candidate flags still require the original solver or PoC and verifier boundary.
- Keep Headroom learning and persistent memory disabled for live tasks unless the event rules and data boundary explicitly permit them.
- Never send raw private challenge artifacts to a third-party compression service. The configured Headroom deployment is local-first, but the wrapped model provider still receives the resulting request.

## Measuring value

Compare similar tasks with and without each tool. Record files read, input/output tokens, elapsed time, changed lines, and whether the result reproduced. Keep the tool only when it reduces context or implementation without lowering correctness.

For worker handoffs, prefer five lines: status, one finding, evidence paths,
exact candidate or `none`, and one next experiment. This avoids repeatedly
copying full challenge transcripts into every worker.

## Project-scoped Codex defaults

The committed `.codex/config.toml` applies conservative defaults whenever
Codex trusts and opens this repository:

- medium reasoning and low response verbosity for interactive triage;
- an 8,000-token per-tool history limit;
- web search and Apps disabled by default;
- at most two nested subagent threads.

Orca's explicit `--effort` still overrides the reasoning default, so wave 1
continues to use xhigh only after a concrete blocker. The output limit is not
an evidence limit: save raw command output to the task workspace before
summarizing it.

For an authorized OSINT problem that genuinely needs live search, start a
separate session instead of changing the repository default:

```powershell
codex -c 'web_search="live"'
```

Use `codex -s read-only` for planning or review only. Active CTF solving needs
workspace writes for PoCs, extracted artifacts, and evidence, so read-only is
not the default. Start a new session for each challenge or unrelated problem;
do not carry a full transcript between tasks.

Keep compact handoff labels in English, but do not translate an entire Korean
challenge just to chase token counts. Store the original statement once and
pass later workers only the evidence paths and the five-line handoff.
