"""Tests for check_workflow_drift — focuses on the pure check_file helper and
the dedup path. No network calls, no filesystem I/O.

Run: python3 -m unittest tools.test_check_workflow_drift
"""

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from tools.check_workflow_drift import (
    ANCHORS,
    APPLY_PATH,
    APPLY_BODY_PATH,
    ARCH_PATH,
    BODY_ANCHORS,
    REPO_SKIP_ANCHORS,
    STALE_BODY_PATH,
    STALE_PATH,
    SKILLS_SKIP_ANCHORS,
    TAG_NAME,
    _issue_title,
    _tag_issue_title,
    body_diff,
    check_file,
    extract_pin,
    is_sha_pin,
    resolve_effective_ref,
    tag_age_days,
)

TAG_SHA = "559431b5ec587899b1c88b6ad31c5283df82bd7d"


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
        content = "\n".join(a for a in anchors if a != "--model claude-sonnet-5")
        missing = check_file(content, anchors)
        self.assertIn("--model claude-sonnet-5", missing)

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


class TestRepoSkipAnchors(unittest.TestCase):
    """REPO_SKIP_ANCHORS is empty: every consumer carries the `@claude-loops-v1`
    tag literal, so a missing literal is a finding everywhere. agent-research
    used to be the lone exception (SHA-pinned by #470), but it floated its pin
    back to the tag literal (goodreads-bot#668 follow-on), so it now enforces the
    anchor like moodreader/goodreads-bot."""

    def test_agent_research_no_longer_skips_claude_loops_v1_literal(self):
        anchors = ANCHORS[APPLY_PATH]
        content = "\n".join(a for a in anchors if a != "@claude-loops-v1")
        skip = REPO_SKIP_ANCHORS.get("dividedby/agent-research", set())
        self.assertIn("@claude-loops-v1", check_file(content, anchors, skip=skip))

    def test_moodreader_still_requires_claude_loops_v1_literal(self):
        anchors = ANCHORS[APPLY_PATH]
        content = "\n".join(a for a in anchors if a != "@claude-loops-v1")
        skip = REPO_SKIP_ANCHORS.get("dividedby/moodreader", set())
        self.assertIn("@claude-loops-v1", check_file(content, anchors, skip=skip))


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
        repo = "dividedby/goodreads-bot"
        title = _issue_title(repo)
        open_titles: set[str] = set()  # empty → no existing issue

        filed = []

        def fake_file_issue(r, drifted, write_token, dry_run):
            filed.append(r)

        drifted = {STALE_PATH: ["@claude-loops-v1"]}
        if title not in open_titles:
            fake_file_issue(repo, drifted, "tok", False)

        self.assertEqual(filed, [repo])


class TestExtractPin(unittest.TestCase):
    """extract_pin is pure: stub content + body filename -> pin string or None."""

    def _stub(self, uses_line: str) -> str:
        return f"    {uses_line}\n"

    def test_extracts_tag_literal_pin(self):
        filename = os.path.basename(APPLY_BODY_PATH)
        content = self._stub(
            f"uses: dividedby/skills/.github/workflows/{filename}@{TAG_NAME}"
        )
        self.assertEqual(extract_pin(content, filename), TAG_NAME)

    def test_extracts_sha_pin_ignoring_trailing_comment(self):
        filename = os.path.basename(APPLY_BODY_PATH)
        content = self._stub(
            f"uses: dividedby/skills/.github/workflows/{filename}@{TAG_SHA} # {TAG_NAME}"
        )
        self.assertEqual(extract_pin(content, filename), TAG_SHA)

    def test_returns_none_when_unparsable(self):
        filename = os.path.basename(APPLY_BODY_PATH)
        content = "no uses: line in here at all\n"
        self.assertIsNone(extract_pin(content, filename))

    def test_cross_match_guard_does_not_match_a_different_body_file(self):
        # Content only has a `uses:` line for the staleness body; asking for
        # the apply body's pin must not falsely match it.
        stale_filename = os.path.basename(STALE_BODY_PATH)
        apply_filename = os.path.basename(APPLY_BODY_PATH)
        content = self._stub(
            f"uses: dividedby/skills/.github/workflows/{stale_filename}@{TAG_NAME}"
        )
        self.assertIsNone(extract_pin(content, apply_filename))


class TestIsShaPin(unittest.TestCase):
    """is_sha_pin is pure: full 40-char lowercase hex vs anything else."""

    def test_full_40_char_hex_is_sha_pin(self):
        self.assertTrue(is_sha_pin(TAG_SHA))

    def test_tag_literal_is_not_sha_pin(self):
        self.assertFalse(is_sha_pin(TAG_NAME))

    def test_short_hex_abbreviation_is_not_sha_pin(self):
        self.assertFalse(is_sha_pin(TAG_SHA[:7]))


class TestResolveEffectiveRef(unittest.TestCase):
    """resolve_effective_ref: SHA -> itself, exact tag -> tag_sha, else -> None (loud)."""

    def test_sha_pin_resolves_to_itself(self):
        self.assertEqual(resolve_effective_ref(TAG_SHA, "deadbeef" * 5), TAG_SHA)

    def test_tag_pin_resolves_to_tag_sha(self):
        self.assertEqual(resolve_effective_ref(TAG_NAME, TAG_SHA), TAG_SHA)

    def test_similar_tag_name_is_not_silently_treated_as_the_tag(self):
        # claude-loops-v10 is a distinct tag; must not fall back to tag_sha.
        self.assertIsNone(resolve_effective_ref("claude-loops-v10", TAG_SHA))

    def test_uppercase_hex_is_not_silently_treated_as_the_tag(self):
        # Uppercase hex isn't a valid SHA pin (GitHub SHAs are lowercase) and
        # isn't the tag literal either — must not resolve to tag_sha.
        self.assertIsNone(resolve_effective_ref(TAG_SHA.upper(), TAG_SHA))


class TestTagAgeDays(unittest.TestCase):
    """tag_age_days is pure: ISO commit date + injectable now -> whole days."""

    def test_zero_days_same_instant(self):
        now = datetime(2026, 7, 3, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(tag_age_days("2026-07-03T12:00:00Z", now=now), 0)

    def test_positive_days_with_injected_now(self):
        now = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(tag_age_days("2026-07-03T12:00:00Z", now=now), 7)

    def test_handles_z_suffix(self):
        # fromisoformat needs "+00:00", not a bare "Z" — regression guard.
        now = datetime(2026, 7, 4, 0, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(tag_age_days("2026-07-03T00:00:00Z", now=now), 1)


class TestBodyDiff(unittest.TestCase):
    """body_diff is pure: unified diff of other vs main, "" if identical."""

    def test_identical_content_returns_empty_string(self):
        self.assertEqual(body_diff("same\n", "same\n", APPLY_BODY_PATH), "")

    def test_differing_content_returns_unified_diff_with_labels(self):
        diff = body_diff("line one\n", "line two\n", APPLY_BODY_PATH)
        self.assertIn(f"main:{APPLY_BODY_PATH}", diff)
        self.assertIn(f"{TAG_NAME}:{APPLY_BODY_PATH}", diff)
        self.assertIn("-line one", diff)
        self.assertIn("+line two", diff)

    def test_other_label_overrides_default_tag_name_in_diff_header(self):
        # A pin-lane diff against a non-tag SHA shouldn't be mislabeled as
        # the tag in the diff header.
        diff = body_diff("a\n", "b\n", APPLY_BODY_PATH, other_label="abc1234")
        self.assertIn(f"abc1234:{APPLY_BODY_PATH}", diff)
        self.assertNotIn(f"{TAG_NAME}:{APPLY_BODY_PATH}", diff)


class TestPinDriftPureChain(unittest.TestCase):
    """extract_pin -> resolve_effective_ref -> body_diff, wired end to end with no I/O."""

    def test_sha_pin_matching_tag_no_drift(self):
        # No consumer SHA-pins now, but the resolver must still handle a stray
        # SHA pin: one equal to the tag's current SHA, body unchanged -> no drift.
        filename = os.path.basename(APPLY_BODY_PATH)
        stub_content = (
            f"uses: dividedby/skills/.github/workflows/{filename}@{TAG_SHA} # {TAG_NAME}\n"
        )
        pin = extract_pin(stub_content, filename)
        effective_ref = resolve_effective_ref(pin, TAG_SHA)
        self.assertEqual(effective_ref, TAG_SHA)
        self.assertEqual(body_diff("main body\n", "main body\n", APPLY_BODY_PATH), "")

    def test_tag_literal_pin_diff_detected(self):
        # moodreader-style: tag-literal pin resolves to tag_sha; body has drifted.
        filename = os.path.basename(APPLY_BODY_PATH)
        stub_content = f"uses: dividedby/skills/.github/workflows/{filename}@{TAG_NAME}\n"
        pin = extract_pin(stub_content, filename)
        effective_ref = resolve_effective_ref(pin, TAG_SHA)
        self.assertEqual(effective_ref, TAG_SHA)
        diff = body_diff("main body\n", "old tag body\n", APPLY_BODY_PATH)
        self.assertNotEqual(diff, "")

    def test_stale_sha_pin_diff_detected(self):
        # A SHA pin that predates the current tag: effective_ref != tag_sha,
        # and its body content differs from main.
        filename = os.path.basename(APPLY_BODY_PATH)
        stale_sha = "a" * 40
        stub_content = (
            f"uses: dividedby/skills/.github/workflows/{filename}@{stale_sha} # {TAG_NAME}\n"
        )
        pin = extract_pin(stub_content, filename)
        effective_ref = resolve_effective_ref(pin, TAG_SHA)
        self.assertEqual(effective_ref, stale_sha)
        diff = body_diff("main body\n", "stale pinned body\n", APPLY_BODY_PATH)
        self.assertNotEqual(diff, "")


class TestTagIssueTitle(unittest.TestCase):
    """_tag_issue_title is pure and deterministic (no args)."""

    def test_deterministic_format(self):
        expected = (
            f"[workflow-drift] {TAG_NAME} tag: reusable body has diverged from main"
        )
        self.assertEqual(_tag_issue_title(), expected)
        self.assertEqual(_tag_issue_title(), _tag_issue_title())


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
