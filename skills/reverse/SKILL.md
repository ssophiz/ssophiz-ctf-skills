---
name: ctf-reverse
description: Reverse authorized CTF binaries and mobile artifacts using static and bounded dynamic analysis, with structured handoff evidence.
---

# Reverse worker

Identify format, architecture, packing/obfuscation signs, entry points, input checks, and data transforms before trying to solve. Maintain a map of relevant functions, constants, structures, and call sites in a workspace note.

Read [references/competition-patterns.md](references/competition-patterns.md) when the task involves generated traces, custom bytecode, staged code, protocol authentication, patch-and-dump techniques, or layered transforms.

Use IDA MCP when it is available and task-scoped. For automation, prefer reproducible Ghidra headless, radare2, angr, or small scripts. Use the search connector only to investigate a precise algorithm, format, or compiler artifact; do not outsource unverified conclusions.

For novel struct-heavy code, reconstruct the data layout from allocation sizes, field offsets, and access patterns, then validate it against at least one execution trace or sample input.

Publish decryption keys, recovered formats, or cross-category leads through `ctf-control`, with function names/offsets and artifact paths.
