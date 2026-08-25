# CCE 2026 post-event recovery audit

This audit records the bounded offline recovery of five challenges that were
not completed during the qualifier. It contains no competition flags,
credentials, live endpoints, or supplied challenge binaries. Raw workspaces,
logs, local test flags, and generated evidence remain ignored by Git.

## Outcome

No genuine competition flag was recovered after the event. The recovery did,
however, complete the local mail-server exploit, make the Lease Journal race
deterministic, and identify the first exact allocator invariant blocking the
current nsprobe route.

| Challenge | Offline recovery result | Remaining blocker |
|---|---|---|
| PiEEE | 54 bounded FUSE replies produced no disclosure, useful overwrite, or reachable executable pointer | No primitive that preserves the object header |
| nsprobe | Reproducible controlled editor at `H-0x20` across ASLR-varying runs | The next allocation aborts with `malloc(): invalid size (unsorted)` |
| Lease Journal | Expiry/compaction stale alias reproduced deterministically with `PASS/PASS` evidence | kmalloc-192 reclaim and the final overlap remain stochastic |
| GRID | Local protocol and assets were exhausted | Required server-side pace, wear, and service telemetry was absent |
| Mail server | ASLR-enabled local exploit recovered the supplied dummy flag | The former server was unavailable, so no competition flag could be read |

## Lease Journal: race primitive resolved

The race was reduced to an exact ordering between expiry and compaction. A
two-attachment QEMU/GDB harness stops CPU0 after compaction reloads the blob but
before it subtracts two references, permits CPU1 to run the matching expiry,
then releases CPU0. With four linked jobs, one bounded network-disabled boot
recorded the intended refcount sequence:

```text
active lease plus four linked jobs: 9
expiry consumes the raced job:      7
compaction and ordinary releases:  -1
```

The active lease slot retained the raced blob pointer after the allocation was
freed. The saved summary reported:

```text
gdb_rc  stale_gdb_rc  interleave  stale_alias  release_us
0       0             PASS        PASS         50000
```

This resolves the scheduling blocker. The intended endgame uses kmalloc-192
pipe rings, `msg_msg`, and a delayed-work object to obtain a leak and reclaim a
live timer object. That reclaim did not become reliable enough to claim a flag.

## nsprobe: exact shifted-editor blocker

The revised carve reproducibly obtains a separately controlled editor at
`H-0x20`. Immediately before the adjacent `H+0x20` allocation, however,
`fastbin[0]` remains populated and `main_arena.unsorted` points to `H+0x10`,
whose interpreted size is invalid. Three ASLR-varying runs preserved both
relations and stopped at the same decisive error:

```text
malloc(): invalid size (unsorted)
```

The process aborts before the `H+0x20` record exists. Consequently, the
proposed `0x500974` mutation and `lookup(10)` endgame remain unproven. A future
attempt should change the allocator state before parking the adjacent editor,
not add more retries to the same malformed-unsorted path.

## Other bounded results

- PiEEE tested qword/guard disclosures, writes to the callback object while
  preserving its first qword, and reachable executable or vtable pointers. All
  three result classes remained empty. Reclaim operations overwrote the object
  header before they provided useful control.
- GRID proved that the decisive pace value was not present in the distributed
  assets, protocol captures, or cached responses. Changing an offline repair
  assumption changed the outcome, confirming that the local model was
  underdetermined rather than proving a flag.
- The mail-server exploit was reproduced under randomized PIE, libc, heap,
  stack, and canary state. A bounded retry reached the required fixed point on
  attempt 10 and read only the supplied local dummy flag.

## Orchestration lesson

Race-condition, TOCTOU, scheduler/workqueue, real-time protocol, and game tasks
now use a latency-sensitive fast lane:

1. Skip broad low-cost triage when the timing signature is explicit.
2. Start with Sol medium to construct a deterministic PoC, controller, or bot.
3. Let a local runner execute high-volume races, frames, or protocol attempts.
4. Escalate to Sol xhigh only after one concrete invariant or blocker is saved.
5. Stop duplicate workers unless they test genuinely independent hypotheses.

This keeps the model focused on hypothesis selection and exploit construction
instead of spending tokens driving every iteration. Exact flags, payloads,
addresses, commands, and decisive errors are never compressed in worker
handoffs.

## Publication boundary

The public repository stores this sanitized audit and the generic harness
improvements only. Event workspaces, raw logs, local test values, challenge
binaries, credentials, and endpoint details remain private and untracked.
