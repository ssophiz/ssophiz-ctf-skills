# Competition web patterns

## Trace the complete authorization chain

Map credential creation, token parsing, signature or MAC verification, claim validation, session lookup, and route authorization. Test the exact sequence used by the protected route. A weak token primitive matters only when the application accepts it in a privileged path.

## Treat timing as a statistical oracle

Establish baseline variance, randomize candidate order, repeat samples, and compare robust statistics rather than one request. Recover data in bounded chunks with retry and confidence thresholds. Save the raw sample set and a deterministic resume point.

## Look for parser disagreement

When proxies, tunnels, upgrades, or protocol translation are present, compare how each hop determines message boundaries. Record the raw request bytes and connection reuse behavior. Keep tests within the supplied endpoint and avoid broad proxy scanning.

## Audit document and report generation

Follow user-controlled fields into templates, renderers, converters, URL fetchers, and subprocesses. Confirm the exact library version and configuration from source or package metadata. Demonstrate the smallest harmless proof before attempting any flag-read path.

## Model stateful APIs as a workflow

For games, approval boards, AI-assisted review systems, and multi-step SaaS applications, list state transitions and the identity trusted at each transition. Automate the legitimate sequence first, then change one invariant at a time. This separates logic flaws from client-side scripting mistakes.

## Preserve a request-level reproducer

Export a minimal sequence with method, path, required headers, body, cookie state, and expected response marker. Remove reusable credentials before publication and replace live endpoints with placeholders.
