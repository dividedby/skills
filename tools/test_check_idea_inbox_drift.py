"""Tests for check_idea_inbox_drift — pure seam and graceful-no-op check.

No network calls. All carrier content supplied via in-memory fixtures.

Run: python3 -m unittest tools.test_check_idea_inbox_drift
"""

import os
import unittest
from io import StringIO
from unittest.mock import patch

from tools.check_idea_inbox_drift import classify_drift, main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# A minimal canonical idea-inbox.md — contains all eight structural anchors.
_CANONICAL = """\
<!-- agent-protocol: drain=docs/agents/idea-inbox.md -->

## Drain

1. **Dedup / relate** — before acting, review the OPEN issues in this repo.
2. **Decision-map** — when the idea is loose or tangled, decompose it.
3. **Pick only the steps it needs** — do not run the whole pipeline by rote.
4. **Labels** — apply labels from `docs/agents/labels.md`.
5. **Aim for a strong agent brief** — strive to emit a ready-for-agent issue.
6. **Move to Actioned** — once the idea becomes an issue/PR, move it.

## Actioned rolling window (default 8)

Rolling window of recent actioned items.
"""

# Identical to canonical except it references triage-labels.md instead of
# labels.md — label-doc filename variance MUST be tolerated (not flagged).
_CANONICAL_TRIAGE_LABELS_REF = _CANONICAL.replace(
    "`docs/agents/labels.md`",
    "`docs/agents/triage-labels.md`",
)

# Missing only Decision-map (step 2 removed).
_MISSING_DECISION_MAP = """\
<!-- agent-protocol: drain=docs/agents/idea-inbox.md -->

## Drain

1. **Dedup / relate** — before acting, review the OPEN issues in this repo.
2. **Pick only the steps it needs** — do not run the whole pipeline by rote.
3. **Labels** — apply labels from `docs/agents/labels.md`.
4. **Aim for a strong agent brief** — strive to emit a ready-for-agent issue.
5. **Move to Actioned** — once the idea becomes an issue/PR, move it.

## Actioned rolling window (default 8)

Rolling window of recent actioned items.
"""

# agent-research-style content: no breadcrumb, no Decision-map, no rolling-window
# section.  Codifies the #489 oracle: agent-research is missing exactly these
# three anchors while most others are missing Decision-map only.
_AGENT_RESEARCH_STYLE = """\
## Drain

1. **Dedup / relate** — before acting, review the OPEN issues in this repo.
2. **Pick only the steps it needs** — do not run the whole pipeline by rote.
3. **Labels** — apply labels from `docs/agents/labels.md`.
4. **Aim for a strong agent brief** — strive to emit a ready-for-agent issue.
5. **Move to Actioned** — once the idea becomes an issue/PR, move it.
"""


# ---------------------------------------------------------------------------
# Tests for the pure classify_drift() seam
# ---------------------------------------------------------------------------


class TestClassifyDrift(unittest.TestCase):
    """classify_drift(content) → list[str] of missing anchor names."""

    def test_canonical_returns_empty(self):
        self.assertEqual(classify_drift(_CANONICAL), [])

    def test_missing_decision_map(self):
        missing = classify_drift(_MISSING_DECISION_MAP)
        self.assertEqual(missing, ["drain step 2 (Decision-map)"])

    def test_agent_research_style_exactly_three_missing(self):
        """agent-research shape: breadcrumb + Decision-map + Actioned absent."""
        missing = classify_drift(_AGENT_RESEARCH_STYLE)
        self.assertEqual(missing, [
            "agent-protocol breadcrumb",
            "drain step 2 (Decision-map)",
            "Actioned rolling-window section",
        ])

    def test_label_doc_variance_tolerated(self):
        """triage-labels.md reference instead of labels.md must NOT be flagged."""
        self.assertEqual(classify_drift(_CANONICAL_TRIAGE_LABELS_REF), [])


# ---------------------------------------------------------------------------
# TestGrounding: real in-repo canonical doc must be clean
# ---------------------------------------------------------------------------


class TestGrounding(unittest.TestCase):
    """Pin the detector to the real docs/agents/idea-inbox.md on disk.

    If a canonical marker is ever renamed, this test fails — catching the
    mismatch before the live job silently fires false positives.
    """

    def test_real_idea_inbox_is_clean(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(repo_root, "docs", "agents", "idea-inbox.md")
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        missing = classify_drift(content)
        self.assertEqual(
            missing,
            [],
            f"docs/agents/idea-inbox.md should have all anchors but is missing: {missing}. "
            f"Check ANCHORS in check_idea_inbox_drift.py against the real doc.",
        )


# ---------------------------------------------------------------------------
# TestGracefulNoSecret
# ---------------------------------------------------------------------------


class TestGracefulNoSecret(unittest.TestCase):
    """Empty --read-token must exit 0 with a NOTICE on stderr."""

    def test_no_token_exits_zero(self):
        with patch("sys.stderr", new_callable=StringIO) as mock_err:
            with self.assertRaises(SystemExit) as cm:
                main(["--read-token", ""])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("NOTICE", mock_err.getvalue())


if __name__ == "__main__":
    unittest.main()
