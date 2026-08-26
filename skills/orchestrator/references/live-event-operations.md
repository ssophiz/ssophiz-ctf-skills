# Live event operations

## Normalize every challenge

Record one task ID, category, score, artifact inventory, supplied endpoint, authorization boundary, owner, and current hypothesis. Keep target outages separate from solver failure so workers do not repeatedly rediscover infrastructure problems.

## Run the first five minutes as a pipeline

Run `ctf-harness kickoff <task_id>` before dispatch. It writes `notes/kickoff.json` with three cheap category checks, the first model profile, and the local process that owns repeated execution. If a prior-write-up corpus is configured, it also writes bounded leads to `notes/prior-notes.txt`.

Use exact search for small corpora and Semble only for a large Markdown corpus. Treat retrieved text as a lead, not exploit evidence. Do not copy the full corpus into a worker prompt.

For CCE or ENKI-attributed tasks, prioritize the synchronized `enki` collection. Use RAG-Anything only when the needed prior evidence is in a PDF, Office file, image, table, or equation; keep it pre-indexed and return no more than three source-linked leads. Historical flags in derived retrieval text are masked and must never become live candidates.

The model selects hypotheses and parameters. A local runner owns brute force, fuzzing, symbolic execution, races, WebSocket/game loops, protocol replay, and repeated decompilation or decoding. Feed the model only summarized batches and preserve the raw output path.

## Use explicit worker states

Move each assignment through these states:

1. `active`: inventory or first hypothesis is in progress.
2. `promising`: a concrete primitive or algorithm has evidence.
3. `candidate`: an exact possible flag was directly observed and linked to the decisive command/output.
4. `submitted`: in candidate-first mode, the verifier may submit this evidence-linked value without waiting for an independent second run.
5. `verified`: a second run or the platform result confirmed the exact candidate.
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

Solver workers never receive the platform token and never submit directly. The verifier accepts only a candidate linked to a task and minimal reproduction evidence, records the server response, and rate-limits retries. A value copied directly from task output may be submitted immediately; a value guessed or synthesized by a model must wait for direct evidence. Do not retry the same rejected value or spray variations.

## Close the event cleanly

Freeze the ledger, export evidence once, reconcile it against the official result list, and route the final material to `ctf-postmortem`. Separate private evidence from public lessons before any Git operation.
