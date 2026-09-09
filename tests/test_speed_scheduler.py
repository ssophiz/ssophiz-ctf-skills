from __future__ import annotations

import unittest

from ssophiz_ctf.speed_scheduler import (
    ChallengeEstimate,
    benchmark_metrics,
    choose_solver_lane,
    event_phase,
    rank_challenges,
    should_kill_worker,
)


class SpeedSchedulerTests(unittest.TestCase):
    def test_event_phase_boundaries(self) -> None:
        self.assertEqual(event_phase(0.0), "early")
        self.assertEqual(event_phase(0.25), "mid")
        self.assertEqual(event_phase(0.75), "late")

    def test_early_game_prefers_fast_expected_flag(self) -> None:
        easy = ChallengeEstimate("easy", 100, 0.95, 60, 5000)
        hard = ChallengeEstimate("hard", 500, 0.20, 2400, 100000)
        ranked = rank_challenges([hard, easy], 0.10)
        self.assertEqual(ranked[0].task_id, "easy")

    def test_fast_lane_skips_depth_decision(self) -> None:
        grid = ChallengeEstimate("grid", 250, 0.65, 180, 12000, fast_lane=True)
        self.assertEqual(choose_solver_lane(grid, 0.05), "fast")

    def test_ultra_requires_evidence_gated_blocker(self) -> None:
        lease = ChallengeEstimate(
            "lease-journal",
            500,
            0.70,
            1200,
            60000,
            concrete_blocker=True,
            cheap_paths_exhausted=True,
        )
        self.assertEqual(choose_solver_lane(lease, 0.50), "ultra")
        no_blocker = ChallengeEstimate("guessing", 500, 0.70, 1200, 60000)
        self.assertEqual(choose_solver_lane(no_blocker, 0.50), "staged")

    def test_worker_kill_is_mechanical(self) -> None:
        self.assertTrue(
            should_kill_worker(
                duplicate_evidence_exists=False,
                no_new_evidence_steps=3,
                token_budget_exceeded=False,
                wall_clock_budget_exceeded=False,
            )
        )
        self.assertFalse(
            should_kill_worker(
                duplicate_evidence_exists=False,
                no_new_evidence_steps=1,
                token_budget_exceeded=False,
                wall_clock_budget_exceeded=False,
            )
        )

    def test_metrics_expose_ttfp_ttff_and_token_efficiency(self) -> None:
        metrics = benchmark_metrics(
            started_at=100.0,
            first_primitive_at=130.0,
            first_flag_at=190.0,
            input_tokens=9000,
            output_tokens=1000,
            flags=1,
            points=200,
        )
        self.assertEqual(metrics["time_to_first_primitive_seconds"], 30.0)
        self.assertEqual(metrics["time_to_first_flag_seconds"], 90.0)
        self.assertEqual(metrics["tokens_per_flag"], 10000.0)
        self.assertEqual(metrics["score_per_1k_tokens"], 20.0)


if __name__ == "__main__":
    unittest.main()
