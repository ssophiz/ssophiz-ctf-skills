# Runtime to direct client

## Capture one real run

Record the entry URL, final URL, cookies or bearer mechanism, Origin, subprotocol, HTTP methods, request bodies, and message order. Save only traffic needed for the challenge path. For binary frames, preserve raw bytes plus direction and monotonic timestamp.

Use the cheapest observation that answers the question:

- DOM controls: compact accessibility snapshot.
- Network contract: filtered request list, one request body, or a bounded HAR.
- JavaScript state: targeted runtime evaluation or console output.
- Visual-only canvas: one screenshot for orientation, then inspect the state feeding the renderer.

## Recover the actively served runtime

Inventory entry HTML, script tags, preload hints, manifests, chunk registries, `sourceMappingURL` values, public configuration objects, worker scripts, and WASM files. Follow the bootstrap loader only far enough to locate endpoint strings, message codecs, state transitions, and validation logic.

Keep these claims separate:

- checked-in source says what was intended;
- served assets say what this instance executes;
- captured traffic says what the server accepted.

## Derive the smallest client

Reproduce one accepted interaction before adding automation:

1. establish the same session and transport;
2. send the same initial frame or request;
3. advance sequence numbers, nonces, or ticks exactly once;
4. compare response type, status, state identifier, and error text;
5. save the minimal parity transcript.

Then remove browser dependencies from the hot path. Keep browser login or session export only when authentication cannot be reproduced more cheaply. Never hard-code a value that changes per instance without also implementing its discovery step.

## Game and rendering traps

- Do not infer authoritative physics from pixels when server telemetry exists.
- Do not assume client-side success state is accepted by the server.
- Look for hidden debug panels, state stores, workers, prediction buffers, replay formats, and repair or wear telemetry before modeling physics.
- If an essential pace, wear, seed, or service value is absent from assets and captures, record the model as underdetermined and seek a server oracle instead of adding guesses.
- Run bots and simulations locally. Return compact batch summaries with the tested parameter range, decisive state change, evidence path, and next bounded experiment.
