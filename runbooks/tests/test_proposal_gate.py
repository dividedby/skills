import unittest

from runbooks.lib.proposal_gate import decide


class ProposalGateTest(unittest.TestCase):
    def test_returns_top_candidate_when_no_open_issues(self):
        candidates = [
            {"dedup_key": "refine-tdd", "priority": 3},
            {"dedup_key": "refine-triage", "priority": 1},
        ]
        result = decide(candidates, open_issues=[])
        self.assertEqual(result["file"], {"dedup_key": "refine-tdd", "priority": 3})

    def test_highest_priority_wins_regardless_of_order(self):
        candidates = [
            {"dedup_key": "low", "priority": 1},
            {"dedup_key": "high", "priority": 5},
            {"dedup_key": "mid", "priority": 3},
        ]
        result = decide(candidates, open_issues=[])
        self.assertEqual(result["file"]["dedup_key"], "high")

    def test_drops_to_next_when_top_already_open(self):
        candidates = [
            {"dedup_key": "high", "priority": 5},
            {"dedup_key": "mid", "priority": 3},
        ]
        result = decide(candidates, open_issues=["high"])
        self.assertEqual(result["file"]["dedup_key"], "mid")

    def test_files_nothing_when_every_candidate_already_open(self):
        candidates = [
            {"dedup_key": "high", "priority": 5},
            {"dedup_key": "mid", "priority": 3},
        ]
        result = decide(candidates, open_issues=["high", "mid"])
        self.assertIsNone(result["file"])

    def test_never_files_more_than_one(self):
        candidates = [
            {"dedup_key": f"cand-{i}", "priority": i} for i in range(50)
        ]
        result = decide(candidates, open_issues=[])
        # The cap is structural: a single candidate, never a collection.
        self.assertIsInstance(result["file"], dict)
        self.assertEqual(result["file"]["dedup_key"], "cand-49")

    def test_ties_broken_by_smallest_dedup_key(self):
        # Same priority; list order puts "zebra" first, but "alpha" must win.
        candidates = [
            {"dedup_key": "zebra", "priority": 4},
            {"dedup_key": "alpha", "priority": 4},
        ]
        result = decide(candidates, open_issues=[])
        self.assertEqual(result["file"]["dedup_key"], "alpha")

    def test_files_nothing_when_no_candidate_clears_the_bar(self):
        candidates = [
            {"dedup_key": "weak", "priority": 1},
            {"dedup_key": "weaker", "priority": 0},
        ]
        result = decide(candidates, open_issues=[], min_priority=2)
        self.assertIsNone(result["file"])

    def test_files_nothing_when_no_candidates(self):
        self.assertIsNone(decide([], open_issues=[])["file"])


if __name__ == "__main__":
    unittest.main()
