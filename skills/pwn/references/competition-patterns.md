# Competition pwn patterns

## Rebuild the supplied environment first

Use the provided kernel, initramfs, QEMU command line, libc, loader, and launch scripts as the source of truth. Keep extracted and modified artifacts separate, and record hashes. A local reproducer is more valuable than repeated blind interaction with a restarting endpoint.

## Custom QEMU and MMIO devices

Map the device state structure, BAR or MMIO ranges, access widths, command state machine, and callback order. Confirm each field offset with both decompilation and one runtime observation. Build exploitation in stages: information disclosure, address calculation, controlled write or call, then a minimal host-side chain.

## Buffered protocol desynchronization

Track where each parser consumes bytes and where buffering changes line or frame boundaries. Preserve exact sent bytes, not only printable terminal output. If exploitation yields a shell or alternate protocol state, make the script explicitly drain pending data before sending the next command.

## Use-after-free and allocator reclaim

Identify the stale reference, object lifetime transition, allocation class, and controllable replacement object. Instrument allocations and reference counts when possible. A crash after free is only a primitive; require a repeatable reclaim and a controlled field before building the final chain.

For input-driven fake chunks, preserve the exact accepted bytes and the parser result that produced each metadata byte. After a fake chunk reaches a tcache or freelist, do not assume the same parser can safely edit its encoded link: if the edit path frees or resolves the object again, first test for allocator consistency failures. An immediate double-free or `!prev` abort means the next experiment is a resolver-free write or allocator-state cleanup, not a different target address.

When a kernel race leaves two live handles pointing to one slab object, separate alias proof from replacement proof. Gate the replacement allocator on the exact freed address and verify that the intended object owns the slot before triggering the second free. A SLUB double-free guard at the held address proves co-aliasing, but also proves that the replacement did not win that allocation.

## Privileged FUSE connections

Opening a fresh `/dev/fuse` file descriptor does not attach it to an existing daemon connection. Before treating clone or fusectl operations as a privilege boundary, verify mount ownership, access to the daemon's file-descriptor table, visibility of the fusectl connection, and whether the clone ioctl requires an already attached descriptor in the caller's own table. Preserve one dynamic permission probe and the matching ioctl call-site evidence.

## Timing-sensitive kernel races

Write down the two orders the exploit must align: object or archive traversal order, and workqueue or callback execution order. Use debugger traces or kernel logs to prove refcount and lifetime transitions. Increase reliability by controlling scheduling inputs and heap state rather than adding arbitrary sleeps.

## Reject false positives early

A leaked pointer, panic, or one-off shell-like prompt is not enough. Re-run from a clean task workspace, calculate bases from saved output, and keep the final exploit independent of debugger-only state.
