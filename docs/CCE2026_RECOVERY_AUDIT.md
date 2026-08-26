# CCE 2026 post-event recovery audit

This audit records the bounded offline recovery of five challenges that were
not completed during the qualifier. It contains no competition flags,
credentials, live endpoints, or supplied challenge binaries. Raw workspaces,
logs, local test flags, and generated evidence remain ignored by Git.

## Outcome

No genuine competition flag was recovered after the event. A second independent
current-model pass completed the local mail-server reproduction again, recovered
an overlooked replay-client contract, proved a same-slot Lease Journal co-alias,
and produced a separate resolver-safe nsprobe tcache primitive. PiEEE remained
blocked after a fresh FUSE-connection and object-map audit.

| Challenge | Offline recovery result | Remaining blocker |
|---|---|---|
| PiEEE | Fresh device and ioctl probes proved that an unprivileged process can open only unbound FUSE descriptors and cannot reach the daemon connection | No non-mangled live object was proven from the recovered write-helper callers |
| nsprobe | A parser-accepted numeric input forges a valid small fake chunk and places it in a deterministic tcache chain | The first encoded-link edit aborts with `double free or corruption (!prev)` |
| Lease Journal | Two stale interleavings now produce two live leases aliasing the same kmalloc-192 blob | The intended replacement object had not reclaimed the exact slot before the second free |
| GRID | An overlooked replay-list and manifest-fetch contract was recovered from the served client cache | No replay manifest or authoritative telemetry frame series survived locally |
| Mail server | A fresh ASLR-enabled local target again reproduced the supplied test-flag read | Saved reports and captures contained no competition flag attributable to this challenge |

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

The independent source-first pass found a separate small-bin route. A
zero-padded legacy numeric address survives resolver validation while supplying
the byte needed for a valid small fake-chunk header. The fake chunk can be freed
into a deterministic tcache chain, but the first attempt to edit its encoded
link through the same resolver lifecycle stops at:

```text
double free or corruption (!prev)
```

This narrows the next experiment to a resolver-free link overwrite or an
allocator-state cleanup. It does not establish an arbitrary allocation.

## Lease Journal: same-slot co-alias resolved

The second pass extended the deterministic stale alias into two live leases
that reference the same kmalloc-192 blob. Exact-address tracing then showed the
second pipe resize freeing that held address before the intended message object
owned it, causing the SLUB double-free guard. This proves the co-alias and the
failed reclaim in one run. A future attempt should gate the replacement
allocation on the exact held address before triggering the matching resize,
rather than rerunning the already-solved scheduling race.

## GRID: replay contract recovered

The cache audit recovered the served replay client and its replay-list,
manifest-fetch, polling, and fixed-frame validation contract. The apparent
telemetry cache entries were framework 404 pages, not race telemetry. Because
the real manifests were fetched without durable caching, no authoritative pace,
wear, service, or flag evidence survived. The local controller therefore
remains an underdetermined sensitivity model, not a verified solve.

## PiEEE: fresh FUSE route exhausted

The unprivileged process could open new `/dev/fuse` descriptors but could not
inspect the daemon file-descriptor table or fusectl connection. Static ioctl
recovery confirmed that cloning requires an already attached descriptor in the
caller's own table. The write matcher and its filesystem callers were mapped,
but no usable non-mangled lifetime object was proven within the bounded pass.

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
