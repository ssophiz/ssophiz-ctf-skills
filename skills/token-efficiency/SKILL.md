---
name: ctf-token-efficiency
description: Reduce model context and output during authorized CTF triage, multi-agent solving, and evidence handoffs while preserving exact exploit and flag data. Use for large logs, repeated worker prompts, source-tree navigation, or token-cost reviews; do not compress exact proof such as flags, hashes, addresses, offsets, payload bytes, credentials, commands, or decisive error text.
---

# CTF token efficiency

Save raw challenge inputs and tool output to the task workspace before summarizing them. Treat compression as an index into evidence, never as evidence itself.

Route work by need:

- Use Graphify for cross-file architecture, call-path, and symbol questions when a project graph exists. Use `rg` or a direct read for one file or one symbol.
- Use Headroom only for large, repetitive listings, JSON, logs, or transcripts. Retrieve the original span before using an exact value in a PoC or verifier.
- Use Caveman `lite` for compact progress updates and worker handoffs. Keep code, commands, warnings, reports, and reproduction steps in normal precise language. Do not enable Caveman proxy hooks together with Ponytail hooks.
- Use CodeBurn at a baseline or milestone, not every turn. It measures token use but does not reduce it.
- Use Impeccable only for a requested frontend, dashboard, or report-viewer task. Never load it for ordinary Web, Pwn, Reverse, Crypto, Forensics, Malware, or Misc solving.
- Keep one installed copy of each skill per agent discovery path. Codex does not merge duplicate skill names, so duplicate `.agents` and legacy `.codex` copies waste discovery context.

Never transform candidate flags, credentials, cryptographic material, hashes, memory addresses, offsets, ROP chains, shellcode, serialized payloads, exact HTTP requests, exploit commands, stack traces, or the shortest decisive error line. Copy these verbatim and include the raw evidence path.

Dispatch the smallest useful worker set. Give each worker a workspace path, one question, and an evidence contract instead of repeating the full challenge transcript. Use this compact handoff:

```text
Status: working | blocked | candidate
Finding: one decisive sentence
Evidence: workspace-relative paths
Candidate: exact value or none
Next: one bounded experiment
```

Start one medium-effort Codex worker for classification, extraction, mechanical decoding, and known-pattern checks. Escalate to one xhigh Codex worker only for a concrete blocker, competing hypotheses, exploit construction, or cross-category synthesis. Use one Claude reviewer only when an independent model family materially helps. Stop duplicate workers after one produces reproducible evidence.
