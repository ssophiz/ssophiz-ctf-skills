---
name: ctf-router
description: Cheaply route an authorized CTF challenge to at most two specialist skills using deterministic features and tiny probes. Never use deep reasoning merely to choose an agent.
---

# CTF shallow router

Routing is an overhead function, not a solving function. Its total expected cost must stay materially below the first specialist experiment.

## Order

1. Inspect challenge metadata already available: declared category, filenames, extensions, MIME/file type, endpoint scheme/port, and a bounded keyword sample.
2. Apply `config/router.yaml` deterministic rules.
3. If one category wins, dispatch exactly one specialist.
4. If two categories are within the ambiguity margin, dispatch at most two tiny probes in parallel. Each probe answers only: `Can this skill produce one concrete new piece of evidence cheaply?`
5. Keep the first worker that produces reproducible evidence. Cancel the duplicate unless a concrete cross-category handoff is already apparent.
6. Never ask a frontier model to write a taxonomy essay or compare every available agent.

## Router output

```text
Route: web
Backup: reverse | none
Signals: js,http,jwt
Confidence: high | medium | low
Probe: none | one bounded question
```

Keep this output under roughly 80 words. Do not include challenge history.

## Ambiguity policy

A wrong cheap route is acceptable if recovery is cheap. Prefer fast evidence-driven correction over expensive up-front certainty. When a specialist fails to produce evidence within its probe budget, return only the failure signal and try the backup. Do not replay its transcript.

## Learning

Record route outcomes as compact structured telemetry. Update empirical category priors from solved tasks later; do not inject historical transcripts into the live router context. Routing should improve through measured outcomes, not larger prompts.
