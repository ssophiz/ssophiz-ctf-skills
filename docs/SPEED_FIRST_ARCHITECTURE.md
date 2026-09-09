# Speed-first CTF architecture

The event objective is not minimum tokens in isolation. It is maximum verified score under a fixed wall-clock and token budget.

## Optimization order

1. Time to first primitive (TTFP)
2. Time to first flag (TTFF)
3. Score per minute
4. Solve rate
5. Tokens per flag
6. Duplicate worker time

A routing decision must stay cheap enough that a slightly wrong route can be corrected faster than a deep routing model could justify the choice.

## Event phases

- Early (0-25% elapsed): sweep high-probability fast flags. Rank primarily by expected score per second.
- Mid (25-75%): balance expected score, wall-clock and token cost.
- Late (75-100%): unused budget has little value; increase willingness to attempt high-point blockers.

The implementation lives in `ssophiz_ctf.speed_scheduler` and is deliberately deterministic.

## Solver lanes

### Fast lane

Use for WebSocket/SSE games, request-order races, timing-sensitive simulations, and other hot loops. The model should identify the protocol or strategy and generate a deterministic client/runner. The runner owns repeated control, retries, reconnects and timing samples.

### Staged lane

Use cheap deterministic extraction first, then bounded model reasoning over the smallest relevant source/evidence spans. Preserve state as a five-line capsule between phases.

### Ultra lane

Ultra is not a default model tier. It is an evidence-gated escalation state. Enter it only when:

- a concrete blocker is recorded,
- cheap paths are exhausted, and
- event phase/value justifies the additional cost.

High point value, late-event timing, or a strong conditional solve probability can justify escalation. Repeated vague failure cannot.

## Worker kill policy

Stop a worker mechanically when any of these becomes true:

- another worker already produced equivalent reproducible evidence,
- token budget is exceeded,
- wall-clock budget is exceeded,
- three consecutive steps produce no new evidence.

Do not ask another model to judge whether a stalled worker should continue.

## CCE 2026 regression cases

`benchmarks/cce2026-regression.json` contains sanitized behavioral regressions based on two challenge styles encountered during the 2026 qualifier work:

- GRID-style realtime control: route immediately to the fast lane and move the hot loop out of the model.
- Lease-Journal-style kernel/pwn: reach a concrete lifetime/race primitive quickly, use deterministic repetition, and gate Ultra on evidence.

The benchmark intentionally contains no flags, credentials, live endpoints, or raw challenge artifacts.

## Core comparison

For each historical/fresh authorized challenge, compare policies using the same model/provider budget:

- baseline monolithic agent,
- existing staged multi-agent policy,
- shallow routing + state capsule,
- speed-first scheduler + evidence-gated Ultra.

The main claim should be based on end-to-end results, not router accuracy: more verified score in less time with lower or comparable tokens per flag.
