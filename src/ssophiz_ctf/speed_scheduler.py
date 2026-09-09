from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ChallengeEstimate:
    task_id: str
    points: int
    solve_probability: float
    expected_seconds: float
    expected_tokens: int
    fast_lane: bool = False
    concrete_blocker: bool = False
    cheap_paths_exhausted: bool = False
    no_new_evidence_steps: int = 0

    def validate(self) -> None:
        if self.points < 0:
            raise ValueError("points must be non-negative")
        if not 0.0 <= self.solve_probability <= 1.0:
            raise ValueError("solve_probability must be between 0 and 1")
        if self.expected_seconds <= 0:
            raise ValueError("expected_seconds must be positive")
        if self.expected_tokens <= 0:
            raise ValueError("expected_tokens must be positive")


def event_phase(elapsed_fraction: float) -> str:
    if not 0.0 <= elapsed_fraction <= 1.0:
        raise ValueError("elapsed_fraction must be between 0 and 1")
    if elapsed_fraction < 0.25:
        return "early"
    if elapsed_fraction < 0.75:
        return "mid"
    return "late"


def priority_score(item: ChallengeEstimate, elapsed_fraction: float) -> float:
    """Rank work by expected scoreboard value while preserving early-event speed.

    Early game strongly rewards fast flags. Mid game balances time and token cost.
    Late game increases the value of high-point attempts because unused budget has
    no value after the event.
    """
    item.validate()
    phase = event_phase(elapsed_fraction)
    expected_points = item.points * item.solve_probability
    seconds = max(item.expected_seconds, 1.0)
    tokens_k = max(item.expected_tokens / 1000.0, 0.1)

    if phase == "early":
        score = expected_points / seconds
    elif phase == "mid":
        score = expected_points / (seconds ** 0.8 * tokens_k ** 0.2)
    else:
        score = expected_points / (seconds ** 0.45 * tokens_k ** 0.1)

    if item.fast_lane:
        score *= 1.35
    return score


def rank_challenges(items: Iterable[ChallengeEstimate], elapsed_fraction: float) -> list[ChallengeEstimate]:
    return sorted(items, key=lambda item: priority_score(item, elapsed_fraction), reverse=True)


def choose_solver_lane(item: ChallengeEstimate, elapsed_fraction: float) -> str:
    """Choose solving depth without spending model reasoning on the decision."""
    item.validate()
    phase = event_phase(elapsed_fraction)

    if item.fast_lane:
        return "fast"

    # Ultra is evidence-gated, not failure-count-gated. A concrete blocker must
    # exist and cheap paths must already have been consumed.
    if item.concrete_blocker and item.cheap_paths_exhausted:
        if phase == "late" or item.points >= 400 or item.solve_probability >= 0.65:
            return "ultra"

    return "staged"


def should_kill_worker(
    *,
    duplicate_evidence_exists: bool,
    no_new_evidence_steps: int,
    token_budget_exceeded: bool,
    wall_clock_budget_exceeded: bool,
) -> bool:
    """Terminate waste quickly; evidence, tokens and wall-clock are hard signals."""
    return bool(
        duplicate_evidence_exists
        or token_budget_exceeded
        or wall_clock_budget_exceeded
        or no_new_evidence_steps >= 3
    )


def benchmark_metrics(*, started_at: float, first_primitive_at: float | None, first_flag_at: float | None,
                      input_tokens: int, output_tokens: int, flags: int, points: int) -> dict[str, float | int | None]:
    total_tokens = input_tokens + output_tokens
    return {
        "time_to_first_primitive_seconds": None if first_primitive_at is None else max(0.0, first_primitive_at - started_at),
        "time_to_first_flag_seconds": None if first_flag_at is None else max(0.0, first_flag_at - started_at),
        "total_tokens": total_tokens,
        "tokens_per_flag": None if flags <= 0 else total_tokens / flags,
        "score_per_1k_tokens": 0.0 if total_tokens <= 0 else points / (total_tokens / 1000.0),
        "flags": flags,
        "points": points,
    }
