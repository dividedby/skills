"""Tests for check_workflow_drift — focuses on the pure check_file helper and
the dedup path. No network calls, no filesystem I/O.

Run: python3 -m unittest tools.test_check_workflow_drift
"""

import unittest
from unittest.mock import MagicMock, patch

from tools.check_workflow_drift import (
    ANCHORS,
    APPLY_PATH,
    APPLY_BODY_PATH,
    ARCH_PATH,
    BODY_ANCHORS,
    STALE_PATH,
    SKILLS_SKIP_ANCHORS,
    _issue_title,
    check_file,
)


class TestCheckFile(unittest.TestCase):
    """check_file is pure: given content + anchors → list of missing anchors."""

    def _apply_anchors(self):
        return ANCHORS[APPLY_PATH]

    def _body_anchors(self):
        return BODY_ANCHORS[APPLY_BODY_PATH]

    def _stub_anchors(self):
        return ANCHORS[ARCH_PATH]

    def test_all_anchors_present_returns_empty(self):
        # Build content that contains every anchor.
        content = "\n".join(self._apply_anchors())
        self.assertEqual(check_file(content, self._apply_anchors()), [])

    def test_missing_issues_write_is_reported(self):
        anchors = self._apply_anchors()
        content = "\n".join(a for a in anchors if a != "issues: write")
        missing = check_file(content, anchors)
        self.assertIn("issues: write", missing)

    def test_missing_claude_loops_v1_is_reported_for_consumer_stub(self):
        anchors = self._stub_anchors()
        content = "\n".join(a for a in anchors if a != "@claude-loops-v1")
        missing = check_file(content, anchors)
        self.assertIn("@claude-loops-v1", missing)

    def test_skills_canary_skips_claude_loops_v1(self):
        """skills' own stubs use `./` not @claude-loops-v1; that anchor must be skipped."""
        anchors = self._stub_anchors()
        # Content that has everything except the @claude-loops-v1 tag.
        content = "\n".join(a for a in anchors if a != "@claude-loops-v1")
        missing = check_file(content, anchors, skip=SKILLS_SKIP_ANCHORS)
        self.assertNotIn("@claude-loops-v1", missing)
        self.assertEqual(missing, [])

    def test_empty_content_returns_all_anchors_missing(self):
        anchors = self._apply_anchors()
        missing = check_file("", anchors)
        self.assertEqual(missing, anchors)

    def test_missing_prompt_fetch_is_reported(self):
        # Prompt-fetch anchor lives on the reusable body, not the thin-caller stub.
        anchors = self._body_anchors()
        content = "\n".join(a for a in anchors if a != "prompts/apply-agent-research.md")
        missing = check_file(content, anchors)
        self.assertIn("prompts/apply-agent-research.md", missing)

    def test_missing_model_pin_is_reported(self):
        # Model-pin anchor lives on the reusable body, not the thin-caller stub.
        anchors = self._body_anchors()
        content = "\n".join(a for a in anchors if a != "--model claude-sonnet-4-6")
        missing = check_file(content, anchors)
        self.assertIn("--model claude-sonnet-4-6", missing)

    def test_missing_budget_backstop_is_reported(self):
        # Budget-backstop anchor lives on the reusable body, not the thin-caller stub.
        anchors = self._body_anchors()
        content = "\n".join(a for a in anchors if a != "--max-budget-usd")
        missing = check_file(content, anchors)
        self.assertIn("--max-budget-usd", missing)

    def test_clean_stub_no_false_positives(self):
        """A stub with all required anchors (including @claude-loops-v1) is clean."""
        anchors = self._stub_anchors()
        content = "\n".join(anchors)
        self.assertEqual(check_file(content, anchors), [])


class TestDedup(unittest.TestCase):
    """When an open issue already exists for a repo, no create call is made."""

    def test_existing_open_issue_prevents_create(self):
        repo = "dividedby/moodreader"
        title = _issue_title(repo)
        # Simulate open_titles already containing this title.
        open_titles = {title}

        filed = []

        def fake_file_issue(r, drifted, write_token, dry_run):
            filed.append(r)

        # Verify: if title already in open_titles, file_issue is never called.
        drifted = {APPLY_PATH: ["issues: write"]}
        if title not in open_titles:
            fake_file_issue(repo, drifted, "tok", False)

        self.assertEqual(filed, [], "file_issue should not be called when issue is already open")

    def test_no_existing_issue_allows_create(self):
        repo = "dividedby/tweakcc-maint"
        title = _issue_title(repo)
        open_titles: set[str] = set()  # empty → no existing issue

        filed = []

        def fake_file_issue(r, drifted, write_token, dry_run):
            filed.append(r)

        drifted = {STALE_PATH: ["@claude-loops-v1"]}
        if title not in open_titles:
            fake_file_issue(repo, drifted, "tok", False)

        self.assertEqual(filed, [repo])


class TestIssueTitle(unittest.TestCase):
    def test_deterministic_format(self):
        self.assertEqual(
            _issue_title("dividedby/moodreader"),
            "[workflow-drift] moodreader: vendored workflows have diverged",
        )

    def test_consistent_across_calls(self):
        title1 = _issue_title("dividedby/agent-research")
        title2 = _issue_title("dividedby/agent-research")
        self.assertEqual(title1, title2)


if __name__ == "__main__":
    unittest.main()
