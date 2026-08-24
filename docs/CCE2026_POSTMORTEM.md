# CCE 2026 Qualifier — sanitized retrospective

## Result

Team 0xLSA finished in 20th place. The final Korean write-up documented 16 solved challenges: eight Reverse, four Web, three Pwn, and one AI challenge. This public retrospective omits all flags, credentials, live endpoints, and raw event artifacts.

| Category | Documented solves |
|---|---:|
| Reverse | 8 |
| Web | 4 |
| Pwn | 3 |
| AI | 1 |
| Total | 16 |

## Technical strengths

- Reverse work benefited from fast static discrimination, scripted inversion, symbolic recovery from traces, and isolated analysis of staged code.
- Pwn work succeeded when supplied environments were reproduced locally and device, allocator, or parser state was modeled explicitly.
- Web work was strongest when the complete authorization or workflow chain was mapped before automating a minimal request sequence.
- Late-event recovery remained productive because working scripts and concise evidence could be reused in the final write-up.

## Operational lessons

- Every challenge needs one owner and a visible state. Process liveness is not evidence of progress.
- Duplicate workers add value only when they pursue distinct hypotheses.
- Candidate flags need a saved reproducer immediately; screenshots and narrative can wait until event close.
- Completed or credit-exhausted workers must release their context before reassignment.
- Target outages, certificate or proxy failures, and solver failures require separate status tracking.
- Submission credentials belong only to a verifier boundary, even under time pressure.

## Improvements made after the event

- Added a live-event worker state machine and reassignment checklist to the orchestrator skill.
- Added competition-derived reference patterns for Reverse, Pwn, and Web workers.
- Added a postmortem skill that separates private evidence from public-safe lessons.
- Expanded repository ignore rules for event workspaces, agent state, dumps, and generated evidence.

## Practice backlog

Future preparation should emphasize reliable kernel race instrumentation, mixed-protocol parsing, network-independent reversing, and one-command evidence capture. Unsolved event artifacts remain private and are not included in this repository.
