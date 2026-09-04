from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


GUARD_PATTERNS: dict[str, tuple[str, ...]] = {
    "authentication": (r"\bauth(?:enticate|enticated|entication)?\b", r"\blogin\b", r"\bsession\b"),
    "authorization": (r"\bauthori[sz](?:e|ed|ation)\b", r"\bpermission\b", r"\baccess[_ ]?check\b", r"\bacl\b"),
    "bounds": (r"\bbounds?[_ ]?check\b", r"\blength\b", r"\bsize\b", r"\bindex\b.*(?:<|<=)"),
    "path_validation": (r"\bcanonicali[sz]e\b", r"\brealpath\b", r"\bpath[_ ]?(?:check|validate|sanitize)\b", r"\.\.[/\\]"),
    "signature": (r"\bverify[_ ]?(?:signature|sig)\b", r"\bsignature[_ ]?check\b", r"\bhmac\b"),
    "privilege": (r"\bis[_ ]?(?:admin|root|privileged)\b", r"\buid\b.*(?:==|!=)", r"\bcapabilit(?:y|ies)\b"),
}

SENSITIVE_PATTERNS: dict[str, tuple[str, ...]] = {
    "command_execution": (r"\bsystem\s*\(", r"\bexec(?:ve|v|vp|lp|le)?\s*\(", r"\bpopen\s*\("),
    "file_access": (r"\bopen\s*\(", r"\bfopen\s*\(", r"\breadfile\b", r"\bwritefile\b"),
    "memory_access": (r"\bmemcpy\s*\(", r"\bmemmove\s*\(", r"\bstrcpy\s*\(", r"\bstrncpy\s*\("),
    "state_change": (r"\bdelete\b", r"\bupdate\b", r"\bwrite\s*\(", r"\bset[_a-z0-9]*\s*\("),
}


@dataclass(frozen=True)
class FunctionRecord:
    name: str
    address: str = ""
    pseudocode: str = ""
    callees: tuple[str, ...] = ()
    callers: tuple[str, ...] = ()
    family: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FunctionRecord":
        name = str(value.get("name", "")).strip()
        if not name:
            raise ValueError("every function requires a non-empty name")
        return cls(
            name=name,
            address=str(value.get("address", "")),
            pseudocode=str(value.get("pseudocode", "")),
            callees=tuple(str(item) for item in value.get("callees", [])),
            callers=tuple(str(item) for item in value.get("callers", [])),
            family=str(value.get("family", "")).strip(),
        )

    @property
    def searchable_text(self) -> str:
        return "\n".join((self.name, self.pseudocode, *self.callees)).casefold()


@dataclass(frozen=True)
class Evidence:
    kind: str
    matches: tuple[str, ...]


@dataclass(frozen=True)
class VariantCandidate:
    function: str
    address: str
    family: str
    missing_guard: str
    confidence: float
    peer_support: str
    sensitive_operations: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass
class GuardLensReport:
    schema_version: str = "guardlens/v1"
    candidates: list[VariantCandidate] = field(default_factory=list)
    guard_matrix: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidates": [asdict(item) for item in self.candidates],
            "guard_matrix": self.guard_matrix,
            "diagnostics": self.diagnostics,
        }


def _matches(text: str, patterns: dict[str, tuple[str, ...]]) -> dict[str, Evidence]:
    found: dict[str, Evidence] = {}
    for kind, expressions in patterns.items():
        hits = tuple(expression for expression in expressions if re.search(expression, text, re.IGNORECASE))
        if hits:
            found[kind] = Evidence(kind=kind, matches=hits)
    return found


def _infer_family(function: FunctionRecord) -> str:
    if function.family:
        return function.family
    if function.callers:
        return "caller:" + sorted(function.callers)[0]
    stem = re.sub(r"(?:handler?|callback|endpoint|route)$", "", function.name, flags=re.IGNORECASE)
    stem = re.sub(r"(?:[_-](?:get|set|add|del|delete|update|create|read|write))+$", "", stem, flags=re.IGNORECASE)
    return "name:" + (stem.strip("_-") or function.name).casefold()


def analyze(functions: Iterable[FunctionRecord], *, baseline_ratio: float = 0.6) -> GuardLensReport:
    if not 0.5 <= baseline_ratio <= 1.0:
        raise ValueError("baseline_ratio must be between 0.5 and 1.0")
    groups: dict[str, list[FunctionRecord]] = {}
    for function in functions:
        groups.setdefault(_infer_family(function), []).append(function)

    report = GuardLensReport()
    for family, members in sorted(groups.items()):
        guards = {item.name: _matches(item.searchable_text, GUARD_PATTERNS) for item in members}
        report.guard_matrix[family] = {name: sorted(values) for name, values in guards.items()}
        if len(members) < 2:
            report.diagnostics.append(f"{family}: skipped; at least two sibling functions are required")
            continue

        required = max(2, math.ceil(len(members) * baseline_ratio))
        for guard_kind in GUARD_PATTERNS:
            guarded = [item for item in members if guard_kind in guards[item.name]]
            if len(guarded) < required:
                continue
            for item in members:
                if guard_kind in guards[item.name]:
                    continue
                sensitive = _matches(item.searchable_text, SENSITIVE_PATTERNS)
                if not sensitive:
                    continue
                support_ratio = len(guarded) / len(members)
                confidence = round(min(0.99, 0.45 + 0.4 * support_ratio + 0.05 * min(len(sensitive), 2)), 2)
                peer_names = tuple(sorted(peer.name for peer in guarded))
                report.candidates.append(
                    VariantCandidate(
                        function=item.name,
                        address=item.address,
                        family=family,
                        missing_guard=guard_kind,
                        confidence=confidence,
                        peer_support=f"{len(guarded)}/{len(members)} siblings: {', '.join(peer_names)}",
                        sensitive_operations=tuple(sorted(sensitive)),
                        evidence=(
                            f"{guard_kind} appears in {len(guarded)} sibling functions",
                            f"candidate contains sensitive operation(s): {', '.join(sorted(sensitive))}",
                            "candidate has no matching guard signal",
                        ),
                    )
                )
    report.candidates.sort(key=lambda item: (-item.confidence, item.family, item.function, item.missing_guard))
    return report


def load_functions(path: Path) -> list[FunctionRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("functions") if isinstance(payload, dict) else payload
    if not isinstance(values, list):
        raise ValueError("input must be a list or an object containing a 'functions' list")
    return [FunctionRecord.from_dict(item) for item in values]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="guardlens", description="Evidence-gated missing-guard variant hunter")
    parser.add_argument("input", type=Path, help="JSON export containing related functions")
    parser.add_argument("--output", "-o", type=Path, help="write the JSON report to this path")
    parser.add_argument("--baseline-ratio", type=float, default=0.6)
    args = parser.parse_args(argv)
    report = analyze(load_functions(args.input), baseline_ratio=args.baseline_ratio).to_dict()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
