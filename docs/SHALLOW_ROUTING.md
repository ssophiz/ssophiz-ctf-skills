# Shallow routing for CTF agents

The solver intentionally avoids deep reasoning when deciding which specialist to launch. Classification is usually cheaper to correct after one failed probe than to perfect with a large model call before any evidence exists.

## Design target

`routing_cost << first_solver_experiment_cost`

Use deterministic features first, then at most two bounded specialist probes. The system optimizes expected tokens-to-first-evidence and tokens-per-flag rather than routing accuracy in isolation.

## Why

A CTF task often exposes strong cheap signals: artifact type, executable format, imports, protocol, endpoint behavior, framework names, archive contents, or vocabulary. Those signals are sufficient to narrow the worker set without loading all skill descriptions or challenge history into a model.

The fallback is deliberately asymmetric: when uncertain, launch two cheap probes rather than one expensive judge. The first reproducible finding becomes evidence and collapses uncertainty naturally.

## Benchmark

Measure:

- route overhead tokens
- time to first evidence
- wrong-route recovery cost
- total tokens per solved flag
- solve rate under a fixed global token budget

Compare deterministic-only, deterministic+two-probe, and LLM-router baselines. A better router is one that improves end-to-end CTF efficiency, not merely category accuracy.

## Working hypothesis

Do not optimize routing accuracy first. Optimize expected end-to-end solving cost:

`E[cost] = route_cost + probe_cost + recovery_cost + solve_cost`

A shallow router may be slightly less accurate than a deep classifier and still win if its wrong-route recovery is cheap. This is especially plausible in CTFs because many challenges expose strong artifact and protocol signals before semantic reasoning is necessary.

Use empirical route outcomes as priors only after enough solved tasks exist. Until then, deterministic rules and tiny evidence probes are the default.
