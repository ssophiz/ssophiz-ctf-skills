---
name: ctf-state-capsule
description: Preserve only decision-relevant CTF state between authorized solver workers. Use at phase boundaries, model handoffs, retries, and escalations to avoid replaying full transcripts while keeping exact evidence recoverable from workspace paths.
---

# CTF state capsule

Do not pass the full chat, terminal transcript, repository, decompiler output, or browser history to the next worker. Keep raw material in the task workspace and pass a compact state capsule that points back to it.

The capsule has exactly five required lines:

```text
Status: working | blocked | candidate | solved
Finding: one falsifiable, decision-relevant sentence
Evidence: workspace-relative raw paths and line/range hints
Candidate: exact value or none
Next: one bounded experiment with a clear success/failure observation
```

## Rules

1. A finding must change the next action. Omit background facts that do not affect routing.
2. Failed hypotheses are recorded once in `notes/rejected.jsonl`; later workers receive only the identifiers relevant to their next experiment.
3. Exact flags, hashes, addresses, offsets, payloads, credentials, commands, protocol bytes, and decisive errors are never summarized. Store them verbatim and reference their raw path.
4. Before asking a model to inspect source, retrieve the smallest relevant span: exact search first, then bounded semantic/graph retrieval only when necessary.
5. Keep at most three active hypotheses after triage and at most two during a normal solve wave. Every hypothesis must include a cheap falsification step.
6. Escalate reasoning only when the capsule contains a concrete blocker that cheaper deterministic work did not resolve.
7. If reproducible evidence proves a path, terminate duplicate workers and spend budget on verification or the next primitive.

## Attack-memory card

Historical write-ups and public research are converted to generalized cards rather than copied into the prompt:

```yaml
primitive: arbitrary_file_read
preconditions: [user_controlled_path]
observables: [download_parameter, traversal_normalization_difference]
cheap_checks: [known_safe_file_read, config_file_probe]
next_primitives: [credential_leak, internal_route_discovery]
source_refs: [local-corpus-id]
```

Retrieve at most three cards and never include historical flags. Cards are hints, not evidence.

## Phase boundary

At the end of each phase, write `notes/state-capsule.txt` and stop. The next worker starts from the challenge statement, this capsule, and only the evidence spans it explicitly requests. This makes context growth approximately bounded by the current hypothesis rather than by total event duration.
