---
name: ctf-orchestrator
description: Coordinate authorized CTF tasks across specialist workers, preserving evidence and routing cross-category handoffs.
---

# CTF orchestrator

Treat the task contract as the complete authorization boundary. First normalize the challenge, list artifacts and endpoints, then dispatch the smallest useful set of specialists.

For live-event ownership, worker states, evidence minimums, failover, and reassignment rules, read [references/live-event-operations.md](references/live-event-operations.md).

Use `ctf-control` to record decisions and evidence. Use `ctf-artifact` to inspect or share task-scoped files. Browser access is for the supplied CTF platform or endpoints only; capture a screenshot or source excerpt when it materially changes routing.

During the event, require each solver to call `record_evidence` with only the decisive commands, workspace-relative PoC paths, short key output, candidate flags, and ordered reproduction steps. Do not ask workers for prose write-ups. At event close, run `ctf-harness evidence-pdf` once to batch the per-challenge ledger into the final PDF.

Keep Pwn, Reverse, and Web work independent until a concrete handoff exists. Examples include a leaked binary from Web, a decryption routine from Reverse, or an endpoint protocol identified by Pwn. Record the handoff as a finding with source paths and the next worker's question.

Do not run analysis commands directly from this role, request verifier access, or submit flags. A candidate needs an attached reproduction path before it moves to verifier review.

At event close, hand the evidence ledger and final write-up to `ctf-postmortem` for private reconciliation and public-safe skill distillation.
