# Routing research notes

The live solver uses shallow routing by design. Recent routing work supports separating cheap pre-inference selection from expensive solving.

- RouteMoA (ACL 2026) uses a lightweight scorer to screen candidate agents before inference, then ranks by performance, cost, and latency. This motivates keeping the CTF router non-generative whenever cheap features suffice.
- Agent-as-a-Router (2026) shows routing can improve by accumulating execution-grounded feedback. This motivates compact empirical priors from solved challenges rather than larger live prompts.
- BoundaryRouter (2026) uses compact early experience to decide when agent execution is needed, supporting the general principle that escalation should be learned from outcomes rather than assumed up front.

For this repository, the hypothesis is narrower: CTF artifact/category signals are unusually strong, so deterministic routing plus at most two tiny evidence probes should outperform deep router reasoning on end-to-end tokens-per-flag.

The benchmark should therefore compare end-to-end outcomes rather than router classification accuracy alone.
