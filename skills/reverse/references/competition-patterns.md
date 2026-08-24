# Competition reversing patterns

## Start with the cheapest discriminator

Check strings, sections, imports, embedded resources, and direct table transforms before opening a debugger. A repeated XOR, fixed permutation, or validation table can often be recovered with a short script and verified against the original binary.

## Patch behavior, then extract state

If anti-debugging or crash handling hides a transient secret, identify the smallest control point that changes artifact generation. Patch only that decision, reproduce the crash in an isolated workspace, and inspect the resulting mapping or dump. Record the original byte, patched byte, file offset, and extraction command.

## Convert traces into constraints

Generated instruction traces, checker logs, or symbolic comparisons are often a better specification than the decompiler. Parse them into explicit equations, solve with a suitable constraint engine, and run the recovered input through the unmodified program. Treat a satisfiable model without original-binary verification as provisional.

## Separate transport from the algorithm

For custom protocols, first reproduce framing, counters, endianness, authentication tags, and error behavior exactly. Only then reverse the payload transform. Save a transport-only test so protocol bugs are not confused with cryptographic or VM bugs.

## Isolate staged code safely

When code is decrypted or generated at runtime, capture the bytes after the transformation and analyze the pure routine separately. Prefer emulation or a debugger snapshot with network disabled. Document the stage boundary and how addresses were rebased.

## Model custom VMs explicitly

Build an instruction table containing opcode, width, operand decoding, state changes, and branch semantics. Implement a small interpreter before attempting symbolic execution. Compare interpreter state with at least one real trace at several instruction boundaries.

## Invert layered transforms one stage at a time

Name each transformation and write an inverse test for it. Apply inverses in reverse order, checking intermediate lengths and any known output format. This makes endianness and permutation mistakes local instead of hiding them in one monolithic solver.
