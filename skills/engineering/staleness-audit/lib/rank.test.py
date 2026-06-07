#!/usr/bin/env python3
"""Table-driven tests for the urgency ranking of staleness findings (ADR 0004)."""
import unittest

from rank import rank_findings, urgency_key


def f(target, gap, eol_passed=None):
    return {"target": target, "gap": gap, "eol_passed": eol_passed}


class TestUrgencyKey(unittest.TestCase):
    def test_eol_passed_outranks_any_gap(self):
        # a patch-gap finding past EOL is more urgent than a major-gap finding still supported
        self.assertGreater(urgency_key(f("a", "patch", True)),
                           urgency_key(f("b", "major", False)))

    def test_gap_orders_within_same_eol(self):
        self.assertGreater(urgency_key(f("a", "major")), urgency_key(f("b", "minor")))
        self.assertGreater(urgency_key(f("a", "minor")), urgency_key(f("b", "patch")))
        self.assertGreater(urgency_key(f("a", "patch")), urgency_key(f("b", "none")))

    def test_unknown_gap_is_lowest(self):
        self.assertEqual(urgency_key(f("a", "unknown"))[1], urgency_key(f("b", "none"))[1])


class TestRankFindings(unittest.TestCase):
    def test_orders_most_urgent_first(self):
        findings = [
            f("patch-supported", "patch", False),
            f("eol-minor", "minor", True),
            f("major-supported", "major", False),
            f("eol-patch", "patch", True),
        ]
        ranked = [x["target"] for x in rank_findings(findings)]
        self.assertEqual(
            ranked,
            ["eol-minor", "eol-patch", "major-supported", "patch-supported"],
        )

    def test_is_stable_on_ties(self):
        # two equally-urgent findings keep their input order
        findings = [f("first", "major"), f("second", "major")]
        self.assertEqual([x["target"] for x in rank_findings(findings)],
                         ["first", "second"])

    def test_missing_eol_treated_as_not_passed(self):
        findings = [f("no-eol-data", "major"), f("eol-patch", "patch", True)]
        self.assertEqual([x["target"] for x in rank_findings(findings)],
                         ["eol-patch", "no-eol-data"])

    def test_does_not_mutate_input(self):
        findings = [f("b", "minor"), f("a", "major")]
        rank_findings(findings)
        self.assertEqual([x["target"] for x in findings], ["b", "a"])


if __name__ == "__main__":
    unittest.main()
