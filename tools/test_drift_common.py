"""Tests for _drift_common — pins the three checkers to the shared I/O layer.

Identity checks (``is``) use no network calls: if a future edit re-inlines
one of these functions back into a checker script instead of importing it
from _drift_common, the corresponding checker module gets its own distinct
function object and this test fails loudly. The behavior tests below mock
``subprocess.run`` to exercise _drift_common's own branch logic directly.

Run: python3 -m unittest tools.test_drift_common
"""

import base64
import subprocess
import unittest
from unittest import mock

from tools import _drift_common
from tools import check_idea_inbox_drift, check_label_drift, check_workflow_drift

CHECKERS = (check_workflow_drift, check_label_drift, check_idea_inbox_drift)


class TestSharedIOFunctions(unittest.TestCase):
    """Each checker imports fetch_file/ensure_label/open_issues, not its own copy."""

    def test_fetch_file_is_shared(self):
        for checker in CHECKERS:
            with self.subTest(checker=checker.__name__):
                self.assertIs(checker.fetch_file, _drift_common.fetch_file)

    def test_ensure_label_is_shared(self):
        for checker in CHECKERS:
            with self.subTest(checker=checker.__name__):
                self.assertIs(checker.ensure_label, _drift_common.ensure_label)

    def test_open_issues_is_shared(self):
        for checker in CHECKERS:
            with self.subTest(checker=checker.__name__):
                self.assertIs(checker.open_issues, _drift_common.open_issues)

    def test_file_issue_io_core_is_shared(self):
        # Each checker's own `file_issue` builds a checker-specific body/title
        # and delegates the actual gh-issue-create mechanics to the shared
        # core, imported under `_file_issue_io`.
        for checker in CHECKERS:
            with self.subTest(checker=checker.__name__):
                self.assertIs(checker._file_issue_io, _drift_common.file_issue)


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestFetchFile(unittest.TestCase):
    """fetch_file's branches: 404 -> None, other failure -> raise, success -> decode."""

    @mock.patch("tools._drift_common.subprocess.run")
    def test_404_returns_none(self, mock_run):
        mock_run.return_value = _completed(
            returncode=1, stderr="gh: Not Found (HTTP 404)"
        )
        self.assertIsNone(_drift_common.fetch_file("dividedby/x", "main", "f.md", "tok"))

    @mock.patch("tools._drift_common.subprocess.run")
    def test_other_failure_raises(self, mock_run):
        mock_run.return_value = _completed(
            returncode=1, stderr="gh: unauthorized (HTTP 401)"
        )
        with self.assertRaises(RuntimeError):
            _drift_common.fetch_file("dividedby/x", "main", "f.md", "tok")

    @mock.patch("tools._drift_common.subprocess.run")
    def test_success_decodes_base64(self, mock_run):
        encoded = base64.b64encode(b"hello world").decode("utf-8")
        mock_run.return_value = _completed(returncode=0, stdout=encoded)
        self.assertEqual(
            _drift_common.fetch_file("dividedby/x", "main", "f.md", "tok"), "hello world"
        )


class TestResolveTagSha(unittest.TestCase):
    """resolve_tag_sha: lightweight/annotated tags, exact-match filtering, failures."""

    @mock.patch("tools._drift_common.subprocess.run")
    def test_lightweight_tag(self, mock_run):
        matching_refs = '[{"ref": "refs/tags/claude-loops-v1", "object": {"sha": "aaa1", "type": "commit"}}]'
        commit = '{"committer": {"date": "2026-06-20T12:00:00Z"}}'
        mock_run.side_effect = [
            _completed(stdout=matching_refs),
            _completed(stdout=commit),
        ]
        sha, date = _drift_common.resolve_tag_sha("dividedby/skills", "claude-loops-v1", "tok")
        self.assertEqual(sha, "aaa1")
        self.assertEqual(date, "2026-06-20T12:00:00Z")
        self.assertEqual(mock_run.call_count, 2)

    @mock.patch("tools._drift_common.subprocess.run")
    def test_annotated_tag_dereferenced(self, mock_run):
        matching_refs = '[{"ref": "refs/tags/claude-loops-v1", "object": {"sha": "tagobj1", "type": "tag"}}]'
        tag_obj = '{"object": {"sha": "commit1", "type": "commit"}}'
        commit = '{"committer": {"date": "2026-06-21T00:00:00Z"}}'
        mock_run.side_effect = [
            _completed(stdout=matching_refs),
            _completed(stdout=tag_obj),
            _completed(stdout=commit),
        ]
        sha, date = _drift_common.resolve_tag_sha("dividedby/skills", "claude-loops-v1", "tok")
        self.assertEqual(sha, "commit1")
        self.assertEqual(date, "2026-06-21T00:00:00Z")
        self.assertEqual(mock_run.call_count, 3)

    @mock.patch("tools._drift_common.subprocess.run")
    def test_exact_match_among_prefix_matches(self, mock_run):
        # matching-refs is a prefix match: claude-loops-v1 also matches
        # claude-loops-v10. The exact ref must be selected, not the first hit.
        matching_refs = (
            '[{"ref": "refs/tags/claude-loops-v10", "object": {"sha": "wrong", "type": "commit"}}, '
            '{"ref": "refs/tags/claude-loops-v1", "object": {"sha": "right", "type": "commit"}}]'
        )
        commit = '{"committer": {"date": "2026-06-22T00:00:00Z"}}'
        mock_run.side_effect = [
            _completed(stdout=matching_refs),
            _completed(stdout=commit),
        ]
        sha, _ = _drift_common.resolve_tag_sha("dividedby/skills", "claude-loops-v1", "tok")
        self.assertEqual(sha, "right")

    @mock.patch("tools._drift_common.subprocess.run")
    def test_missing_tag_raises(self, mock_run):
        mock_run.return_value = _completed(stdout="[]")
        with self.assertRaises(RuntimeError):
            _drift_common.resolve_tag_sha("dividedby/skills", "claude-loops-v1", "tok")

    @mock.patch("tools._drift_common.subprocess.run")
    def test_api_failure_raises(self, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="gh: rate limited")
        with self.assertRaises(RuntimeError):
            _drift_common.resolve_tag_sha("dividedby/skills", "claude-loops-v1", "tok")


class TestOpenIssues(unittest.TestCase):
    """open_issues' lossy fallback: a gh failure is treated as no open issues."""

    @mock.patch("tools._drift_common.subprocess.run")
    def test_gh_failure_returns_empty_set(self, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="gh: rate limited")
        self.assertEqual(_drift_common.open_issues("label-drift", "tok"), set())


if __name__ == "__main__":
    unittest.main()
