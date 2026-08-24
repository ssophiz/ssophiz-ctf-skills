from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CATEGORIES = {"pwn", "reverse", "malware", "web", "crypto", "forensics", "misc"}
FLAG_PATTERN = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z0-9_]{2,32})\{[^\r\n{}]{1,256}\}")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_DUMMY_WORDS = {"dummy", "fake", "mock", "sample"}
_PLACEHOLDER_WORDS = {"changeme", "example", "placeholder", "redacted", "replace", "todo"}
_TEST_WORDS = {"demo", "testing", "testflag", "test"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class TaskEnvelope:
    id: str
    name: str
    category: str
    description: str
    workspace: str
    artifacts: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    allowed_mcp: list[str] = field(default_factory=list)
    scope: str = "Authorized CTF challenge only"
    timeout_minutes: int = 12
    allow_target_operations: bool = False
    platform_challenge_id: int | None = None
    created_at: str = field(default_factory=utc_now)

    def validate(self) -> None:
        if not self.id or not self.name or not self.description:
            raise ValueError("Task id, name, and description are required")
        if self.category not in CATEGORIES:
            raise ValueError(f"Unsupported category: {self.category}")
        if self.timeout_minutes < 1 or self.timeout_minutes > 240:
            raise ValueError("timeout_minutes must be between 1 and 240")
        if self.allow_target_operations and not self.endpoints:
            raise ValueError("Target operations require at least one explicit endpoint")
        workspace = Path(self.workspace)
        if workspace == Path("/") or str(workspace).strip() in {"", "."}:
            raise ValueError("Task workspace must be a dedicated directory")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskEnvelope":
        task = cls(**data)
        task.validate()
        return task

    @classmethod
    def create(
        cls,
        *,
        name: str,
        category: str,
        description: str,
        workspace: str,
        **kwargs: Any,
    ) -> "TaskEnvelope":
        return cls(
            id=f"task_{uuid.uuid4().hex[:12]}",
            name=name,
            category=category,
            description=description,
            workspace=workspace,
            **kwargs,
        )


@dataclass
class Finding:
    task_id: str
    worker: str
    summary: str
    evidence: list[str]
    confidence: float
    id: str = field(default_factory=lambda: f"finding_{uuid.uuid4().hex[:12]}")
    created_at: str = field(default_factory=utc_now)

    def validate(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.evidence:
            raise ValueError("At least one evidence item is required")


@dataclass
class LedgerEntry:
    """Small, structured proof bundle emitted by one solver worker."""

    task_id: str
    worker: str
    summary: str
    commands: list[str] = field(default_factory=list)
    poc_paths: list[str] = field(default_factory=list)
    key_outputs: list[str] = field(default_factory=list)
    reproduction_steps: list[str] = field(default_factory=list)
    flag_candidates: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: f"evidence_{uuid.uuid4().hex[:12]}")
    created_at: str = field(default_factory=utc_now)

    def validate(self) -> None:
        if not self.task_id.strip() or not self.worker.strip():
            raise ValueError("Ledger task_id and worker are required")
        if not self.summary.strip():
            raise ValueError("Ledger summary is required")
        if len(self.summary) > 500:
            raise ValueError("Ledger summary must be 500 characters or fewer")
        sections = (
            self.commands,
            self.poc_paths,
            self.key_outputs,
            self.reproduction_steps,
            self.flag_candidates,
        )
        if not any(sections):
            raise ValueError("Ledger entry requires a command, PoC, output, reproduction step, or flag candidate")
        if any(not isinstance(item, str) or not item.strip() for values in sections for item in values):
            raise ValueError("Ledger list values must be non-empty strings")
        if any(len(values) > 32 for values in sections):
            raise ValueError("Ledger sections are limited to 32 items")
        if sum(len(item) for values in sections for item in values) > 65536:
            raise ValueError("Ledger entry exceeds the 64 KiB evidence limit")
        if self.flag_candidates and not self.reproduction_steps:
            raise ValueError("Flag candidates require reproduction_steps")
        for value in self.flag_candidates:
            FlagCandidate(task_id=self.task_id, worker=self.worker, value=value).validate()


@dataclass
class FlagCandidate:
    task_id: str
    worker: str
    value: str
    id: str = field(default_factory=lambda: f"candidate_{uuid.uuid4().hex[:12]}")
    status: str = "pending"
    platform_response: str = ""
    evidence_id: str = ""
    created_at: str = field(default_factory=utc_now)

    def validate(self) -> None:
        if not FLAG_PATTERN.fullmatch(self.value.strip()):
            raise ValueError("Candidate does not match the configured flag shape")


@dataclass(frozen=True)
class FlagClassification:
    kind: str
    submit_eligible: bool
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_flag_candidate(value: str) -> FlagClassification:
    """Classify obvious fixtures without guessing whether an unknown flag is correct."""

    stripped = value.strip()
    if not FLAG_PATTERN.fullmatch(stripped):
        return FlagClassification("invalid", False, ["value does not match the configured flag shape"])
    prefix, payload = stripped.split("{", 1)
    payload = payload[:-1]
    normalized_prefix = _NON_ALNUM.sub("", prefix.lower())
    normalized_payload = _NON_ALNUM.sub("_", payload.lower()).strip("_")
    words = {part for part in normalized_payload.split("_") if part}
    joined = "".join(words)
    if normalized_prefix in _DUMMY_WORDS or words & _DUMMY_WORDS or normalized_payload in {
        "not_a_real_flag",
        "this_is_not_a_flag",
    }:
        return FlagClassification("mock", False, ["flag contains an explicit mock/dummy marker"])
    if normalized_prefix in _PLACEHOLDER_WORDS or words & _PLACEHOLDER_WORDS or joined in {
        "flaggohere",
        "insertflaghere",
    }:
        return FlagClassification("placeholder", False, ["flag contains an explicit placeholder marker"])
    if normalized_prefix in _TEST_WORDS or words & _TEST_WORDS:
        return FlagClassification("test", False, ["flag contains an explicit test marker"])
    if set(normalized_payload) <= {"0", "_", "-"} or set(normalized_payload) <= {"x", "_", "-"}:
        return FlagClassification("placeholder", False, ["flag payload is filler characters only"])
    return FlagClassification("candidate", True, ["no explicit mock, placeholder, or test marker detected"])


def extract_flag_candidates(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0) for match in FLAG_PATTERN.finditer(text)))
