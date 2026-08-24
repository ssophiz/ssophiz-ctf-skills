# Lightweight evidence ledger

The live-event record is a small structured proof bundle, not a write-up. Each
solver records one entry per useful attack path through the `ctf-control`
`record_evidence` tool:

- `summary`: one short conclusion (500 characters maximum)
- `commands`: only decisive analysis or exploit commands
- `poc_paths`: workspace-relative scripts and captured artifacts
- `key_outputs`: the few output lines that prove the conclusion
- `reproduction_steps`: ordered steps another worker can execute
- `flag_candidates`: reproduced candidates only

An entry is stored per challenge and attributed to the worker. A flag included
in an entry is also added to the candidate queue and linked back to that entry.
The verifier lists and submits only candidates whose linked entry contains
reproduction steps. Older unlinked candidates remain visible in `show` and the
PDF, but are not verifier-eligible.

Example tool payload:

```json
{
  "task_id": "task_123",
  "worker": "pwn-exploit",
  "summary": "ret2win succeeds at offset 72",
  "commands": ["python notes/pwn-exploit/solve.py LOCAL=1"],
  "poc_paths": ["notes/pwn-exploit/solve.py"],
  "key_outputs": ["offset=72\nflag{reproduced}"],
  "reproduction_steps": [
    "Start the supplied challenge container.",
    "Run python notes/pwn-exploit/solve.py LOCAL=1.",
    "Confirm the emitted candidate matches the ledger."
  ],
  "flag_candidates": ["flag{reproduced}"]
}
```

Inspect one challenge without generating a report:

```powershell
.\scripts\ctf-harness.ps1 show <task_id>
```

Immediately before the event ends, build the single final PDF for all
registered challenges:

```powershell
.\scripts\ctf-harness.ps1 evidence-pdf `
  --output .\output\pdf\ctf-evidence-ledger.pdf
```

Use repeated `--task-id` options only when the final packet should contain a
selected subset. Set `SSOPHIZ_PDF_FONT` to a local TrueType/OpenType font when
the automatic Korean-capable font discovery is unsuitable.
