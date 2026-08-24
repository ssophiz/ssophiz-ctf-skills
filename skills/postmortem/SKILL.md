---
name: ctf-postmortem
description: Reconcile an authorized CTF result and final write-up, produce a private event retrospective, and distill public-safe agent skill improvements without exposing flags or credentials. Use after a competition, practice event, or certification lab when the user asks to wrap up, update CTF skills, prepare a GitHub commit, or organize CTF notes.
---

# CTF postmortem

Treat the final platform result, evidence ledger, submitted write-up, and saved PoCs as separate sources. Reconcile them before drawing lessons. A challenge counts as solved only when the final evidence or official result supports it; label partial and unsolved work explicitly.

Read [references/event-retrospective.md](references/event-retrospective.md) for the private retrospective structure. Read [references/publication-checklist.md](references/publication-checklist.md) before staging any public commit.

Keep two outputs:

- A private event record may contain flags, supplied credentials, exact endpoints, screenshots, raw artifacts, and unresolved hypotheses.
- A public skill update contains only reusable methods, sanitized examples, tool requirements, and operational lessons.

Distill lessons into the smallest relevant specialist skill. Put detailed patterns in `references/` and keep `SKILL.md` concise. Do not create challenge-specific instructions when a category-level pattern is sufficient.

If the user requests Obsidian organization, create or update a dedicated private CTF vault only after confirming its path. Do not mix CTF flags and credentials into an unrelated CTI or incident-response vault.

Before committing, inspect the exact staged file list, scan staged content for flags, credentials, live endpoints, pairing codes, personal data, dumps, and generated workspaces, then validate every changed skill. Push only when the user explicitly requests it.
