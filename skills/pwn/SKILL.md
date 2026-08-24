---
name: ctf-pwn
description: Analyze authorized binary-exploitation CTF challenges in a task-scoped Docker workspace and preserve reproducible evidence.
---

# Pwn worker

Begin with offline triage: file type, architecture, mitigations, imports, input surface, and supplied libc/loader. Store a short triage note and any repeatable script under the task workspace.

Read [references/competition-patterns.md](references/competition-patterns.md) for kernel/QEMU packages, custom MMIO devices, parser desynchronization, use-after-free, and timing-sensitive allocator races.

Use `ctf-sandbox` for dynamic commands. Pwn tasks may use the limited debug container capability, never host shell access. Use the supplied endpoint only after a local hypothesis is concrete; respect the task timeout and avoid broad scans.

When IDA MCP is configured, use it for decompilation or cross-references that change the exploit hypothesis. Fall back to Ghidra headless/radare2 rather than blocking on an unavailable GUI integration.

Publish a finding only with an offset, trace, disassembly location, program output, or saved reproduction artifact. Publish a candidate only after the complete path reproduces it.
