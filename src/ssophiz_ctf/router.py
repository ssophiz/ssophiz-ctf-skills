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
                "wave": int(profile.get("wave", 0 if index == 0 else 1)),
            }
        )
    return assignments
