# Live event operations

## Normalize every challenge

Record one task ID, category, score, artifact inventory, supplied endpoint, authorization boundary, owner, and current hypothesis. Keep target outages separate from solver failure so workers do not repeatedly rediscover infrastructure problems.

## Use explicit worker states

Move each assignment through these states:

1. `active`: inventory or first hypothesis is in progress.
2. `promising`: a concrete primitive or algorithm has evidence.
3. `candidate`: a possible flag exists with a reproduction artifact.
4. `verified`: a second run reproduced the exact candidate.
5. `submitted`: the verifier recorded the platform result.
6. `exhausted`: tested hypotheses and blockers are preserved for reassignment.

Do not report a worker as productive merely because its process is alive. Require a short heartbeat containing its state, latest evidence path, blocker, and next action.

## Parallelize by hypothesis

Give each problem one primary owner. Add a second worker only when it has a different method, such as static versus dynamic reversing, source review versus request reproduction, or exploit construction versus allocator tracing. Duplicating identical prompts usually burns time without adding evidence.

When a worker finishes, fails, or loses provider credit, immediately reclaim its assignment and resources. Reassign the worker to the highest-value unresolved task only after its evidence and scripts are saved.

## Preserve the minimum useful evidence

During the event, save:

- the decisive command or request;
- the solver or PoC path;
- a short output excerpt;
- the candidate and its confidence;
- ordered steps needed for another worker to reproduce it.

Screenshots and report prose can wait until event close. Do not defer the reproducible command, because terminal history and remote state are fragile.

## Keep submission isolated

Solver workers never receive the platform token and never submit directly. The verifier accepts only a candidate linked to a task and reproduction path, records the server response, and rate-limits retries. A fast event does not justify blind repeated submissions.

## Close the event cleanly

Freeze the ledger, export evidence once, reconcile it against the official result list, and route the final material to `ctf-postmortem`. Separate private evidence from public lessons before any Git operation.
