# Multi-provider and MCP policy

The harness is model-agnostic, but it is intentionally **not provider-fanout by default**. The goal is verified score per minute under a token budget, not maximum model diversity.

## Recommended topology

```text
                challenge
                    |
          deterministic router
                    |
             Codex / ChatGPT
            primary solve lane
                    |
          evidence + state capsule
             /              \
      solved/candidate      concrete blocker
          |                     |
       verifier        optional Z.ai GLM probe/review
                                |
                        new evidence only
                                |
                         primary solver
```

Use one strong primary family for normal solving. A second provider is valuable only when it creates information diversity cheaply: a bounded ambiguity probe, an independent review of a concrete blocker, or a failover when the primary provider is unavailable.

Do not send the same full challenge to multiple providers merely to vote on answers. That increases latency, tokens, and data exposure while usually duplicating work.

## Z.ai

The optional `zai_probe` and `zai_review` profiles use the harness's existing OpenAI-compatible API worker. Configuration is entirely environment-driven:

```powershell
$env:ZAI_API_KEY = '...'
$env:ZAI_BASE_URL = 'https://api.z.ai/api/coding/paas/v4'
$env:ZAI_MODEL = 'glm-5.3'
```

For a general Z.ai prepaid/resource-package API account, use `https://api.z.ai/api/paas/v4` instead. Keep the exact model id configurable because provider model availability changes.

Failover is committed **disabled**. Enable it in the private `config/harness.json` only after confirming that the competition rules allow external model processing and that the challenge data may be sent to that provider.

Recommended use:

- `zai_probe`: at most one small hypothesis test when shallow routing is ambiguous or the primary solver has no evidence.
- `zai_review`: cross-check a concrete blocker/candidate using only the five-line state capsule and referenced evidence.
- never give a secondary model the CTFd token, verifier credentials, cookies, historical flags, or unrelated workspace files.

## Local models

`ollama_local` remains the privacy-first fallback. Use it for mechanical review, decompiler summaries, structure hypotheses, log cross-checking, or offline challenge material that must not leave the machine. Do not assume a small local model should replace the frontier solver for difficult Pwn/Reverse chains.

A useful priority is:

```text
local deterministic tools -> primary frontier solver -> optional local review -> optional external second provider -> Ultra escalation
```

The exact order can change when privacy rules prohibit external providers.

## MCP boundary

MCP is a **tool/capability boundary**, not the model router. Model providers belong in harness profiles/adapters. This keeps provider credentials out of MCP tool schemas and prevents every worker from loading every tool definition.

The committed role policy is least-privilege:

| Role | MCP servers |
|---|---|
| orchestrator | `ctf-control`, `ctf-artifact` |
| pwn/reverse/malware | control, artifact, sandbox, IDA |
| web | control, artifact, sandbox, bounded web |
| crypto/forensics/misc | control, artifact, sandbox |
| verifier | verifier only |

The orchestrator does not receive `ctf-web`; it schedules rather than browsing the target. Search/retrieval is not registered as a permanent MCP server for every worker: exact local search and bounded retrieval should be invoked only when needed. This reduces tool-schema tokens and accidental authority.

`ctf-verifier` stays out of `.mcp.json` used by ordinary solver sessions. The verifier process is launched separately and owns submission credentials.

## Provider-selection rule

Do not use another LLM to decide which LLM to use unless cheap deterministic routing has already failed. Provider selection should be mechanical:

1. start primary;
2. if no new evidence within the configured budget, inspect the blocker;
3. use local deterministic/local-model work when it can cheaply falsify the blocker;
4. call one secondary provider only when independent reasoning is expected to add information;
5. stop it as soon as reproducible evidence appears;
6. reserve Ultra/frontier-high effort for a concrete high-value blocker.

Measure provider value with end-to-end metrics: `TTFP`, `TTFF`, score/minute, tokens/flag, score/1k tokens, and duplicate-worker time. A second provider stays enabled only if it improves those metrics on held-out CTF problems.
