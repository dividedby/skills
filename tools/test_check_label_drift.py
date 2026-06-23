"""Tests for check_label_drift — pure helpers and drift-shape detection.

No network calls, no filesystem I/O; all consumer-repo content is supplied via
fixtures (in-memory strings or None for missing files).

Run: python3 -m unittest tools.test_check_label_drift
"""

import unittest

from tools.check_label_drift import (
    LABELS_PATH,
    TRIAGE_LABELS_PATH,
    TIER_MARKERS,
    DriftShape,
    classify_drift,
    _issue_title,
    build_issue_body,
)


# ---------------------------------------------------------------------------
# Canonical triage-labels.md fixture — contains all three required tiers.
# ---------------------------------------------------------------------------

_CANONICAL_TRIAGE = """\
# Label Convention

## CORE — State (all repos)

| Label | Color | Description |
| `needs-triage` | `FBCA04` | Maintainer needs to evaluate |

## LOOP/NETWORK (full-tier repos)

| Label | Color | Description |
| `workflow-onboarding` | `0052CC` | Onboarding to a proposal-loop workflow |

## CHANNELS (owned by `dividedby/skills`, applied by consumers)

| Label | Color | Description |
| `skill-request` | `006B75` | Cross-repo demand for a skill |
"""

# A triage-labels.md that is missing the LOOP/NETWORK tier.
_TRIAGE_MISSING_LOOP = """\
# Label Convention

## CORE — State (all repos)

| Label | Color | Description |
| `needs-triage` | `FBCA04` | Maintainer needs to evaluate |

## CHANNELS (owned by `dividedby/skills`, applied by consumers)

| Label | Color | Description |
| `skill-request` | `006B75` | Cross-repo demand for a skill |
"""

# A triage-labels.md that is missing CHANNELS.
_TRIAGE_MISSING_CHANNELS = """\
# Label Convention

## CORE — State (all repos)

| Label | Color | Description |
| `needs-triage` | `FBCA04` | Maintainer needs to evaluate |

## LOOP/NETWORK (full-tier repos)

| Label | Color | Description |
| `workflow-onboarding` | `0052CC` | Onboarding to a proposal-loop workflow |
"""

# A triage-labels.md missing all three tiers (e.g. Matt's short-form version).
_TRIAGE_STUB = "See docs/agents/labels.md for label definitions.\n"


class TestClassifyDrift(unittest.TestCase):
    """classify_drift is pure: given (labels_md, triage_labels_md) → DriftShape."""

    # -----------------------------------------------------------------------
    # Shape 1: stray labels.md present alongside triage-labels.md
    # -----------------------------------------------------------------------

    def test_stray_labels_md_detected_when_both_present(self):
        shape = classify_drift(
            labels_md=_TRIAGE_STUB,  # content is irrelevant for this shape
            triage_labels_md=_CANONICAL_TRIAGE,
        )
        self.assertEqual(shape, DriftShape.STRAY_LABELS_MD)

    def test_stray_labels_md_with_drifted_triage_reports_stray(self):
        # Even if triage-labels.md is also drifted, stray takes precedence
        # (one shape per repo; stray is most obviously actionable).
        shape = classify_drift(
            labels_md=_TRIAGE_STUB,
            triage_labels_md=_TRIAGE_STUB,
        )
        self.assertEqual(shape, DriftShape.STRAY_LABELS_MD)

    # -----------------------------------------------------------------------
    # Shape 2: triage-labels.md present but missing one or more tier headings
    # -----------------------------------------------------------------------

    def test_missing_loop_network_tier_detected(self):
        shape = classify_drift(
            labels_md=None,
            triage_labels_md=_TRIAGE_MISSING_LOOP,
        )
        self.assertEqual(shape, DriftShape.MISSING_TIERS)

    def test_missing_channels_tier_detected(self):
        shape = classify_drift(
            labels_md=None,
            triage_labels_md=_TRIAGE_MISSING_CHANNELS,
        )
        self.assertEqual(shape, DriftShape.MISSING_TIERS)

    def test_missing_all_tiers_in_stub_detected(self):
        shape = classify_drift(
            labels_md=None,
            triage_labels_md=_TRIAGE_STUB,
        )
        self.assertEqual(shape, DriftShape.MISSING_TIERS)

    def test_canonical_triage_is_clean(self):
        shape = classify_drift(
            labels_md=None,
            triage_labels_md=_CANONICAL_TRIAGE,
        )
        self.assertIsNone(shape)

    # -----------------------------------------------------------------------
    # Shape 3: only labels.md present (triage-labels.md absent)
    # -----------------------------------------------------------------------

    def test_labels_md_only_detected(self):
        shape = classify_drift(
            labels_md=_TRIAGE_STUB,
            triage_labels_md=None,
        )
        self.assertEqual(shape, DriftShape.LABELS_MD_ONLY)

    # -----------------------------------------------------------------------
    # Shape 4: both files absent
    # -----------------------------------------------------------------------

    def test_both_missing_detected(self):
        shape = classify_drift(
            labels_md=None,
            triage_labels_md=None,
        )
        self.assertEqual(shape, DriftShape.BOTH_MISSING)

    # -----------------------------------------------------------------------
    # Clean repo — no drift
    # -----------------------------------------------------------------------

    def test_clean_repo_returns_none(self):
        shape = classify_drift(
            labels_md=None,
            triage_labels_md=_CANONICAL_TRIAGE,
        )
        self.assertIsNone(shape)


class TestTierMarkers(unittest.TestCase):
    """TIER_MARKERS must include substrings that identify each required section."""

    def test_core_marker_present(self):
        self.assertTrue(any("CORE" in m for m in TIER_MARKERS))

    def test_loop_network_marker_present(self):
        self.assertTrue(any("LOOP" in m for m in TIER_MARKERS))

    def test_channels_marker_present(self):
        self.assertTrue(any("CHANNELS" in m for m in TIER_MARKERS))

    def test_canonical_doc_contains_all_markers(self):
        for marker in TIER_MARKERS:
            self.assertIn(marker, _CANONICAL_TRIAGE, f"Missing marker: {marker!r}")


class TestIssueTitle(unittest.TestCase):
    def test_deterministic_format(self):
        self.assertEqual(
            _issue_title("dividedby/moodreader"),
            "[label-drift] moodreader: label-convention doc has drifted",
        )

    def test_consistent_across_calls(self):
        self.assertEqual(
            _issue_title("dividedby/agent-research"),
            _issue_title("dividedby/agent-research"),
        )


class TestBuildIssueBody(unittest.TestCase):
    """build_issue_body returns a non-empty string mentioning setup-dividedby-skills."""

    def _body(self, shape: DriftShape) -> str:
        return build_issue_body("dividedby/moodreader", shape, [])

    def test_mentions_setup_skill(self):
        for shape in DriftShape:
            with self.subTest(shape=shape):
                body = self._body(shape)
                self.assertIn("setup-dividedby-skills", body)

    def test_stray_body_mentions_labels_md(self):
        body = self._body(DriftShape.STRAY_LABELS_MD)
        self.assertIn(LABELS_PATH, body)

    def test_missing_tiers_body_mentions_triage_labels(self):
        # missing_tiers names use hyphen form (LOOP-NETWORK) — matches repo prose convention.
        body = build_issue_body(
            "dividedby/moodreader",
            DriftShape.MISSING_TIERS,
            missing_tiers=["LOOP-NETWORK", "CHANNELS"],
        )
        self.assertIn(TRIAGE_LABELS_PATH, body)
        self.assertIn("LOOP-NETWORK", body)

    def test_both_missing_body_mentions_both_paths(self):
        body = self._body(DriftShape.BOTH_MISSING)
        self.assertIn(LABELS_PATH, body)
        self.assertIn(TRIAGE_LABELS_PATH, body)

    def test_labels_md_only_body_mentions_triage_labels(self):
        body = self._body(DriftShape.LABELS_MD_ONLY)
        self.assertIn(TRIAGE_LABELS_PATH, body)


class TestGrounding(unittest.TestCase):
    """Pin the detector to the real canonical doc so heading renames are caught."""

    def test_real_labels_md_is_clean(self):
        """docs/agents/labels.md (the canonical source) must pass as clean triage-labels.md.

        Walks up from this file to the repo root; reads labels.md from disk.
        If a tier heading is ever renamed in labels.md, or if TIER_MARKERS is
        tightened incorrectly, this test fails — that's the intent.
        """
        import os
        # test file lives at tools/test_check_label_drift.py → repo root is one level up
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        labels_path = os.path.join(repo_root, "docs", "agents", "labels.md")
        with open(labels_path, encoding="utf-8") as fh:
            content = fh.read()
        shape = classify_drift(labels_md=None, triage_labels_md=content)
        self.assertIsNone(
            shape,
            f"docs/agents/labels.md should be clean when treated as triage-labels.md, "
            f"but classify_drift returned {shape!r}. "
            f"Check TIER_MARKERS against the actual headings in labels.md.",
        )


class TestGracefulNoSecret(unittest.TestCase):
    """When --read-token is empty, main() exits 0 with a clear message."""

    def test_no_token_exits_zero(self):
        import sys
        from io import StringIO
        from unittest.mock import patch

        # Patch sys.argv so argparse gets no tokens.
        with patch("sys.argv", ["check_label_drift.py"]):
            with patch("sys.stderr", new_callable=StringIO) as mock_err:
                with self.assertRaises(SystemExit) as cm:
                    from tools.check_label_drift import main
                    main(["--read-token", ""])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("NOTICE", mock_err.getvalue())


if __name__ == "__main__":
    unittest.main()
