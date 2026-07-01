import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

from proposal_gate import MAX_BUDGET, decide  # noqa: E402  (after sys.path bootstrap)


class ProposalGateTest(unittest.TestCase):
    def test_returns_top_candidate_when_no_open_issues(self):
        candidates = [
            {"dedup_key": "refine-tdd", "priority": 3},
            {"dedup_key": "refine-triage", "priority": 1},
        ]
        result = decide(candidates, open_issues=[])
        self.assertEqual(result["file"], [{"dedup_key": "refine-tdd", "priority": 3}])

    def test_highest_priority_wins_regardless_of_order(self):
        candidates = [
            {"dedup_key": "low", "priority": 1},
            {"dedup_key": "high", "priority": 5},
            {"dedup_key": "mid", "priority": 3},
        ]
        result = decide(candidates, open_issues=[])
        self.assertEqual(result["file"][0]["dedup_key"], "high")

    def test_drops_to_next_when_top_already_open(self):
        candidates = [
            {"dedup_key": "high", "priority": 5},
            {"dedup_key": "mid", "priority": 3},
        ]
        result = decide(candidates, open_issues=["high"])
        self.assertEqual(result["file"][0]["dedup_key"], "mid")

    def test_files_nothing_when_every_candidate_already_open(self):
        candidates = [
            {"dedup_key": "high", "priority": 5},
            {"dedup_key": "mid", "priority": 3},
        ]
        result = decide(candidates, open_issues=["high", "mid"])
        self.assertEqual(result["file"], [])

    def test_default_budget_never_files_more_than_one(self):
        candidates = [
            {"dedup_key": f"cand-{i}", "priority": i} for i in range(50)
        ]
        result = decide(candidates, open_issues=[])
        self.assertEqual(len(result["file"]), 1)
        self.assertEqual(result["file"][0]["dedup_key"], "cand-49")

    def test_budget_returns_ranked_top_k(self):
        candidates = [
            {"dedup_key": f"cand-{i:02d}", "priority": i} for i in range(10)
        ]
        # budget=3 clamps to MAX_BUDGET; still exercises ranked top-k selection
        result = decide(candidates, open_issues=[], budget=3)
        expected = ["cand-09", "cand-08", "cand-07"][:MAX_BUDGET]
        self.assertEqual([c["dedup_key"] for c in result["file"]], expected)

    def test_budget_is_a_ceiling_not_a_target(self):
        candidates = [{"dedup_key": "only", "priority": 5}]
        result = decide(candidates, open_issues=[], budget=5)
        self.assertEqual(len(result["file"]), 1)

    def test_budget_is_clamped_to_max(self):
        candidates = [
            {"dedup_key": f"cand-{i:02d}", "priority": i} for i in range(20)
        ]
        result = decide(candidates, open_issues=[], budget=99)
        self.assertEqual(len(result["file"]), MAX_BUDGET)

    def test_duplicate_keys_within_batch_keep_best_only(self):
        # The dedup-skip branch only fires once the loop has room for a second
        # item; raise MAX_BUDGET locally so this pure-function regression
        # guard keeps exercising it even though the system-wide cap is 1.
        candidates = [
            {"dedup_key": "same", "priority": 5},
            {"dedup_key": "same", "priority": 3},
            {"dedup_key": "other", "priority": 4},
        ]
        with mock.patch("proposal_gate.MAX_BUDGET", 5):
            result = decide(candidates, open_issues=[], budget=5)
        self.assertEqual(
            [(c["dedup_key"], c["priority"]) for c in result["file"]],
            [("same", 5), ("other", 4)],
        )

    def test_ties_broken_by_smallest_dedup_key(self):
        # Same priority; list order puts "zebra" first, but "alpha" must win.
        candidates = [
            {"dedup_key": "zebra", "priority": 4},
            {"dedup_key": "alpha", "priority": 4},
        ]
        result = decide(candidates, open_issues=[])
        self.assertEqual(result["file"][0]["dedup_key"], "alpha")

    def test_files_nothing_when_no_candidate_clears_the_bar(self):
        candidates = [
            {"dedup_key": "weak", "priority": 1},
            {"dedup_key": "weaker", "priority": 0},
        ]
        result = decide(candidates, open_issues=[], min_priority=2)
        self.assertEqual(result["file"], [])

    def test_files_nothing_when_no_candidates(self):
        self.assertEqual(decide([], open_issues=[])["file"], [])


if __name__ == "__main__":
    unittest.main()
