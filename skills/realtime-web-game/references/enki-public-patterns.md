# ENKI public challenge patterns

Use this reference for ENKI-authored challenges or when a black-box web task appears to require several different boundaries. These are public patterns, not a prediction that every ENKI challenge uses the same chain.

## Product feature to internal architecture

Start with ordinary features and identify the smallest input that reaches file handling, previews, templates, reports, or internal fetches. When a bounded file read is found, prioritize configuration, route definitions, process layout, and the source serving the active path before searching broadly for a flag.

Map the complete request chain: public frontend, reverse proxy, internal service, cache or queue, custom parser, and privileged helper. Record which component validates each header, path, identity, and message boundary. A primitive becomes useful when it crosses a concrete authorization or routing boundary.

## Chaining over isolated bug labels

Express progress as capabilities:

1. recover active configuration or source;
2. identify an internal-only route or trusted header;
3. reach that route through parser, redirect, or proxy behavior;
4. analyze the custom template, binary, or protocol at the next boundary;
5. use direct output or a measured oracle to recover the target artifact.

This prevents spending event time polishing a vulnerability that does not advance the chain.

## Side-channel fallback

When direct flag output is filtered, look for a bounded observable affected by a candidate match: response length, status, timing, byte counters, log volume, retry behavior, or state transition. Establish baseline noise, test randomized candidates, retain raw samples, and recover only the smallest unknown per iteration.

Do not call a timing or counter difference an oracle until repeated controls separate it from normal variance.

## Public ENKI sources

- ENKI GitHub organization: https://github.com/enki-kr
- Odin CTF write-ups: https://github.com/enki-kr/odin-ctf
- CODEGATE 2025 final full-chain material: https://github.com/enki-kr/codegate2025-final-fullchain
- ENKI RedTeam CTF Jeopardy write-up: https://www.enki.co.kr/en/media-center/blog/enki-redteam-ctf-jeopardy-writeup
