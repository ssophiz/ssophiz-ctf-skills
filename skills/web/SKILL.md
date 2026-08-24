---
name: ctf-web
description: Analyze supplied authorized CTF web applications through evidence-driven requests, source review, and bounded browser/proxy use.
---

# Web worker

Inventory routes, authentication state, request formats, server-side components, and exposed files. Prefer source and local-container review when available. For black-box instances, use only the task endpoints and save minimally sufficient HTTP evidence.

Read [references/competition-patterns.md](references/competition-patterns.md) for authentication-chain review, timing oracles, parser disagreement, document-rendering sinks, and stateful API workflows.

Browser and proxy integrations are for reproducing a precise interaction, not broad discovery outside the challenge. If a Web observation yields a binary, secret format, or cryptographic primitive, save it to the workspace and publish a handoff finding.

Use the task's supplied accounts, tokens, and endpoints only. Do not add targets, perform internet-wide scanning, or reuse challenge credentials elsewhere.

Every candidate must be tied to a reproducible request sequence or source-level proof.
