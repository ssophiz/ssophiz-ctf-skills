# Race windows and instance churn

## Establish a baseline

Run the legitimate sequence serially and record final state, response markers, latency distribution, and reset behavior. A race result is meaningful only when the same payloads produce a different final state under changed ordering.

## Build a controlled race

Prepare authentication and connections before the release point. Use a barrier so workers wait after setup, then release the smallest competing actions together. Reuse warmed connections when connection setup would dominate the target window.

Record monotonic send and receive times, request identity, response identity, and final server state. Change only one of concurrency, ordering, delay, connection reuse, or payload per batch. Use bounded attempts and stop when the success condition, rejection condition, or attempt budget is reached.

Prefer the repository's existing bounded `ctf-web` race runner when it fits. Write a challenge-specific runner only when protocol framing, persistent WebSockets, or a multi-step state machine requires it.

## Separate timing evidence from state evidence

A latency shift may locate a window but does not prove useful state drift. Preserve both:

- baseline and racing timing samples;
- the durable state or capability created by the changed ordering.

Reduce the explanation to read, check, write, enqueue, commit, or retry boundaries. Name the missing lock, weak idempotency, stale read, delayed commit, or retry side effect only when evidence supports it.

## Handle restarting challenge servers

Before each batch, fingerprint the current instance with the cheapest stable markers available: health response, build hash, session identifier, banner, asset hash, or initial state token. Treat connection resets, a changed fingerprint, expired cookies, and repeated impossible state as instance churn rather than exploit failure.

When churn is detected:

1. stop the current batch;
2. reacquire endpoint and session state through the authorized challenge flow;
3. recapture every nonce, seed, token, and asset tied to that instance;
4. resume from a saved phase boundary, not from a partially synchronized protocol state.

Do not mix captures, parameters, or flags from different instances.
