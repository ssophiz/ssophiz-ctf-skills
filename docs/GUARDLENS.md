# GuardLens Variant Hunter

GuardLens is a deterministic, evidence-gated prototype for finding missing
security checks across sibling functions. It turns decompiler or static-analysis
exports into a guard matrix and ranks inconsistencies that also reach a sensitive
operation. It is intended for software you own or are authorized to assess.

## Why this is different

Variant hunting often starts from one fixed bug and asks where the same mistake
survives. GuardLens instead models the repeated *guard invariant* in a function
family. A candidate is emitted only when:

1. at least two sibling functions contain the same guard signal;
2. the configured majority threshold is met;
3. one sibling lacks that signal; and
4. that sibling performs a sensitive operation.

Every candidate contains its peer support, matched sensitive-operation class,
and the reason it was ranked. The result is triage evidence, not a vulnerability
verdict.

## Quick start

```bash
python -m pip install -e ".[dev]"
guardlens examples/guardlens/sample_handlers.json -o guardlens-report.json
python -m unittest tests.test_guardlens -v
```

The input is either a JSON list or `{ "functions": [...] }`. Each function needs
`name`; optional fields are `address`, `pseudocode`, `callees`, `callers`, and
`family`. Supplying a stable `family` from a dispatcher, route table, vtable, or
call-graph cluster gives the strongest comparison. Without it, GuardLens uses a
shared caller and then a conservative name heuristic.

## Current guard and sink vocabulary

The MVP recognizes authentication, authorization, bounds, path-validation,
signature, and privilege guards. Sensitive operations include command execution,
file access, memory access, and state changes. Patterns are intentionally visible
in `guardlens.py` so results can be reproduced and challenged.

## IDA workflow

Use the existing read-only `ctf-ida-mcp` tools to list sibling functions, fetch
callers/callees, and decompile only the authorized module. Export those bounded
results to the schema above, then run GuardLens locally. A future adapter can
automate export without changing the scoring contract.

## Non-goals and limitations

- GuardLens does not exploit, patch, or modify a target.
- A missing textual signal is not proof that a guard is absent.
- Inlined checks, wrapper functions, indirect calls, or poor decompilation can
  produce false positives or negatives.
- Reviewers must verify control flow and reachability before treating a candidate
  as a security finding.

These limits are deliberate: the MVP establishes a measurable baseline for a
later graph model or LLM-assisted semantic layer without hiding uncertainty.
