#!/usr/bin/env python3
"""Table-driven tests for the auto-apply gating decision (ADR 0004)."""
import unittest

from apply_policy import decide


def f(gap="patch", eol_passed=None, file_owned=True,
      verify_available=True, verify_passed=None, low_confidence=None,
      is_floor=None):
    return {
        "gap": gap,
        "eol_passed": eol_passed,
        "file_owned": file_owned,
        "verify_available": verify_available,
        "verify_passed": verify_passed,
        "low_confidence": low_confidence,
        "is_floor": is_floor,
    }


class TestDecide(unittest.TestCase):
    def test_in_major_with_verify_is_applied(self):
        self.assertEqual(decide(f(gap="patch")), "apply")
        self.assertEqual(decide(f(gap="minor")), "apply")

    def test_in_major_that_passed_verify_is_applied(self):
        self.assertEqual(decide(f(gap="minor", verify_passed=True)), "apply")

    def test_cross_major_never_applied(self):
        self.assertEqual(decide(f(gap="major")), "recommended: cross-major")
        # even with a green verify result, a major jump stays a recommendation
        self.assertEqual(decide(f(gap="major", verify_passed=True)),
                         "recommended: cross-major")

    def test_eol_jump_never_applied(self):
        # a past-EOL pin is a recommendation even when its gap reads in-major
        self.assertEqual(decide(f(gap="minor", eol_passed=True)),
                         "recommended: eol jump")
        self.assertEqual(decide(f(gap="major", eol_passed=True)),
                         "recommended: eol jump")

    def test_no_verify_command_disables_apply_for_all(self):
        # absence of a verify command dominates every other disposition
        self.assertEqual(decide(f(gap="patch", verify_available=False)),
                         "unverified: no verify command")
        self.assertEqual(decide(f(gap="major", verify_available=False)),
                         "unverified: no verify command")
        self.assertEqual(decide(f(gap="minor", eol_passed=True,
                                  verify_available=False)),
                         "unverified: no verify command")

    def test_verify_failed_downgrades_an_otherwise_eligible_bump(self):
        self.assertEqual(decide(f(gap="patch", verify_passed=False)),
                         "recommended (verify failed)")

    def test_not_owned_file_is_not_applied(self):
        self.assertEqual(decide(f(gap="patch", file_owned=False)),
                         "recommended: not owned")

    def test_nothing_to_bump(self):
        self.assertEqual(decide(f(gap="none")), "recommended: none")
        self.assertEqual(decide(f(gap="unknown")), "recommended: none")

    def test_low_confidence_is_recommend_only_even_when_otherwise_eligible(self):
        # an installer-sourced finding that is in-major, owned, verify available
        # AND passed verify would normally be "apply" — low confidence overrides it
        self.assertEqual(
            decide(f(gap="patch", file_owned=True, verify_available=True,
                     verify_passed=True, low_confidence=True)),
            "recommended: low confidence (installer)",
        )

    def test_low_confidence_dominates_every_other_disposition(self):
        # decided first — ahead of even the missing-verify global disable
        self.assertEqual(
            decide(f(gap="patch", verify_available=False, low_confidence=True)),
            "recommended: low confidence (installer)",
        )
        self.assertEqual(
            decide(f(gap="major", low_confidence=True)),
            "recommended: low confidence (installer)",
        )
        self.assertEqual(
            decide(f(gap="minor", eol_passed=True, low_confidence=True)),
            "recommended: low confidence (installer)",
        )
        self.assertEqual(
            decide(f(gap="patch", file_owned=False, low_confidence=True)),
            "recommended: low confidence (installer)",
        )

    def test_floor_is_recommend_only_even_when_otherwise_eligible(self):
        # an in-major, owned floor with a green verify would normally be "apply" —
        # raising a consumer-imposed floor is never a mechanical bump
        self.assertEqual(
            decide(f(gap="patch", file_owned=True, verify_available=True,
                     verify_passed=True, is_floor=True)),
            "recommended: floor (consumer-imposed)",
        )

    def test_floor_dominates_the_verify_gate_and_ceilings(self):
        # decided ahead of the missing-verify disable and the cross-major/EOL
        # ceilings, so the report names the floor reason rather than burying it
        self.assertEqual(
            decide(f(gap="patch", verify_available=False, is_floor=True)),
            "recommended: floor (consumer-imposed)",
        )
        self.assertEqual(
            decide(f(gap="major", is_floor=True)),
            "recommended: floor (consumer-imposed)",
        )
        self.assertEqual(
            decide(f(gap="minor", eol_passed=True, is_floor=True)),
            "recommended: floor (consumer-imposed)",
        )

    def test_low_confidence_outranks_floor(self):
        # both are source/shape distrust; low_confidence is decided first
        self.assertEqual(
            decide(f(gap="patch", low_confidence=True, is_floor=True)),
            "recommended: low confidence (installer)",
        )


if __name__ == "__main__":
    unittest.main()
