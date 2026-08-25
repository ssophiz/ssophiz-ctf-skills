from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .contracts import TaskEnvelope


EXTENSION_CATEGORY = {
    ".pcap": "forensics",
    ".pcapng": "forensics",
    ".mem": "forensics",
    ".raw": "forensics",
    ".apk": "reverse",
    ".so": "reverse",
    ".elf": "pwn",
}

KEYWORD_CATEGORY = {
    "pwn": ("buffer overflow", "rop", "heap", "shellcode", "libc", "pwntools"),
    "reverse": ("reverse", "decompile", "crackme", "android", "binary"),
    "malware": ("malware", "ransomware", "loader", "dropper", "c2", "command and control"),
    "web": ("http", "website", "login", "cookie", "api", "ssrf", "ssti", "xss"),
    "crypto": ("rsa", "cipher", "nonce", "elliptic", "aes", "hash"),
    "forensics": ("pcap", "memory dump", "disk image", "steganography", "forensic"),
}

FIRST_CHECKS = {
    "pwn": [
        "Identify architecture, mitigations, loader/libc, and the first controlled crash or parser boundary.",
        "Run strings/imports and inspect only the input path that reaches memory-unsafe code.",
        "Put cyclic, fuzz, race, or brute-force repetitions in a local runner and save its raw output.",
    ],
    "reverse": [
        "Identify format, architecture, packing, imports, and the success/failure output path.",
        "Search strings and xrefs before decompiling only the smallest validation slice.",
        "Move decoding, emulation, tracing, or constraint iterations into a local script.",
    ],
    "malware": [
        "Hash and identify the sample, packer, imports, persistence, and likely configuration path.",
        "Extract strings/resources statically before any bounded dynamic run.",
        "Automate repeated decoding or configuration extraction outside the model.",
    ],
    "web": [
        "Inventory routes, authentication state, client bundles, and one legitimate request sequence.",
        "Check authorization and server-side trust boundaries before broad payload spraying.",
        "Put request races, enumeration, replay, and protocol loops in a bounded local client.",
    ],
    "crypto": [
        "Parse all parameters and test the cheapest invariant or known construction first.",
        "Check reuse, size, entropy, subgroup, padding, and oracle assumptions mechanically.",
        "Run algebra, brute force, SAT/SMT, or lattice experiments in a deterministic local solver.",
    ],
    "forensics": [
        "Hash and inventory the artifact without modifying the original.",
        "Extract metadata, timelines, strings, and embedded files with provenance.",
        "Automate bulk carving, decoding, packet filtering, or candidate ranking locally.",
    ],
    "misc": [
        "Inventory artifacts, endpoints, formats, and observable success conditions.",
        "Run one cheap discriminator for the two most likely categories.",
        "Move repeated simulation, scraping, decoding, or search into a bounded local runner.",
    ],
}

MACHINE_LOOPS = {
    "pwn": "pwntools/GDB runner owns crashes, offsets, heap shaping, races, and retries",
    "reverse": "batch disassembler, emulator, tracer, or solver owns repeated execution",
    "malware": "isolated decoder or bounded sandbox runner owns repeated extraction",
    "web": "direct HTTP/WebSocket client owns enumeration, races, replay, and timing samples",
    "crypto": "Python/Sage/Z3 runner owns algebra, search, and candidate verification",
    "forensics": "local extraction pipeline owns carving, filtering, decoding, and ranking",
    "misc": "small deterministic script owns repeated simulation, scraping, or decoding",
}


def infer_category(description: str, artifacts: list[str]) -> str:
    lowered = description.lower()
    scores = {category: 0 for category in KEYWORD_CATEGORY}
    for category, keywords in KEYWORD_CATEGORY.items():
        scores[category] += sum(1 for keyword in keywords if keyword in lowered)
    for artifact in artifacts:
        category = EXTENSION_CATEGORY.get(Path(artifact).suffix.lower())
        if category:
            scores[category] = scores.get(category, 0) + 3
    best = max(scores, key=scores.get)
    return best if scores[best] else "misc"


def route_task(task: TaskEnvelope, config: HarnessConfig) -> list[dict[str, Any]]:
    profile_names = config.routes.get(task.category, config.routes.get("misc", []))
    fast_lane = config.data.get("fast_lane", {})
    task_text = f"{task.name} {task.description}".lower()
    is_fast_lane = any(keyword.lower() in task_text for keyword in fast_lane.get("keywords", []))
    if is_fast_lane:
        profile_names = fast_lane.get("profiles", profile_names)
    assignments: list[dict[str, Any]] = []
    for index, profile_name in enumerate(profile_names):
        profile = config.profiles[profile_name]
        assignments.append(
            {
                "profile": profile_name,
                "adapter": profile["adapter"],
                "agent": profile.get("agent"),
                "model": profile["model"],
                "effort": profile.get("effort"),
                "role": profile.get("role", task.category),
                "focus": profile.get("focus", "Independently solve and validate the task."),
                "wave": index if is_fast_lane else int(profile.get("wave", 0 if index == 0 else 1)),
                "fast_lane": is_fast_lane,
            }
        )
    return assignments


def select_wave(assignments: list[dict[str, Any]], wave: int) -> list[dict[str, Any]]:
    if wave < 0:
        raise ValueError("wave must be non-negative")
    return [assignment for assignment in assignments if int(assignment.get("wave", 0)) == wave]


def build_speed_plan(task: TaskEnvelope, assignments: list[dict[str, Any]]) -> dict[str, Any]:
    first = min(assignments, key=lambda item: int(item.get("wave", 0))) if assignments else {}
    fast_lane = bool(first.get("fast_lane"))
    return {
        "category": task.category,
        "lane": "fast" if fast_lane else "staged",
        "first_profile": first.get("profile"),
        "first_checks": FIRST_CHECKS[task.category],
        "machine_loop": (
            "direct HTTP/WebSocket client or challenge-protocol client owns timing, retries, simulation, and reconnects"
            if fast_lane
            else MACHINE_LOOPS[task.category]
        ),
        "model_job": "Choose the next hypothesis from summarized batches; do not manually drive the hot loop.",
        "stop": "Publish a directly observed, evidence-linked candidate or one concrete blocker.",
    }
