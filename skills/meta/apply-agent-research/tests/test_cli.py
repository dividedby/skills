"""Tests for the CLI seam over the surviving pure helpers.

The ``apply-agent-research`` skill runs unattended in GitHub Actions and must
invoke the *real* ``sanitizer`` and ``proposal_gate`` mechanically, not by prompt
discipline. This CLI is that seam: stdin in, decision on stdout + exit code out,
so the workflow can gate on it from Bash. The decisions themselves are tested in
``test_sanitizer`` / ``test_proposal_gate``; here we only test the wiring.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import cli  # noqa: E402  (after sys.path bootstrap)


def _run(argv, stdin=""):
    """Invoke the CLI with a fake stdin, capturing (exit_code, stdout)."""
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(argv, stdin=io.StringIO(stdin))
    return code, out.getvalue()


class SanitizeCommandTest(unittest.TestCase):
    def test_allows_a_clean_body(self):
        code, out = _run(["sanitize"], stdin="A generalized improvement idea.")
        self.assertEqual(code, 0)
        self.assertIn("ALLOW", out)

    def test_blocks_a_fenced_code_block(self):
        code, out = _run(["sanitize"], stdin="Look:\n```\nsecret()\n```\n")
        self.assertEqual(code, 1)
        self.assertIn("BLOCK", out)

    def test_blocks_a_configured_private_marker(self):
        code, out = _run(
            ["sanitize", "--marker", "acme-private"],
            stdin="This references acme-private internals.",
        )
        self.assertEqual(code, 1)
        self.assertIn("acme-private", out)

    def test_markers_are_optional(self):
        code, _ = _run(["sanitize"], stdin="No markers supplied; structural only.")
        self.assertEqual(code, 0)


class GateCommandTest(unittest.TestCase):
    def test_emits_the_chosen_candidate_as_json(self):
        payload = {
            "candidates": [
                {"dedup_key": "deepen-x", "priority": 3, "title": "x"},
                {"dedup_key": "deepen-y", "priority": 1, "title": "y"},
            ],
            "open_issues": [],
        }
        code, out = _run(["gate"], stdin=json.dumps(payload))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["file"]["dedup_key"], "deepen-x")

    def test_files_nothing_when_candidate_already_open(self):
        payload = {
            "candidates": [{"dedup_key": "deepen-x", "priority": 3}],
            "open_issues": ["deepen-x"],
        }
        code, out = _run(["gate"], stdin=json.dumps(payload))
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(out)["file"])

    def test_honors_min_priority(self):
        payload = {
            "candidates": [{"dedup_key": "weak", "priority": 1}],
            "open_issues": [],
            "min_priority": 3,
        }
        _, out = _run(["gate"], stdin=json.dumps(payload))
        self.assertIsNone(json.loads(out)["file"])


class GuardedFilingTest(unittest.TestCase):
    """The ``file`` / ``comment`` seam: the guard wraps the ``gh`` write, so a
    blocked body must NEVER reach ``gh``, and an allowed one must shell out with
    the right argv. ``gh`` is mocked — we test the gating, not the network."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".md")
        os.close(fd)
        self.addCleanup(os.unlink, self.path)

    def _body(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return self.path

    def _file(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(argv)
        return code, out.getvalue()

    def test_file_creates_issue_on_clean_body(self):
        body = self._body("A generalized improvement, no leaks.")
        with mock.patch("cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run:
            code, _ = self._file(
                ["file", "--title", "deepening: sharpen X", "--body-file", body,
                 "--label", "source:agent-research"]
            )
        self.assertEqual(code, 0)
        run.assert_called_once()
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["gh", "issue", "create"])
        self.assertIn("source:agent-research", cmd)
        self.assertIn(body, cmd)

    def test_file_blocks_and_never_shells_to_gh(self):
        body = self._body("Leaky:\n```\nsecret()\n```\n")
        with mock.patch("cli.subprocess.run") as run:
            code, out = self._file(
                ["file", "--title", "t", "--body-file", body, "--label", "source:agent-research"]
            )
        self.assertEqual(code, 1)
        self.assertIn("BLOCK", out)
        run.assert_not_called()

    def test_file_guards_the_title_not_just_the_body(self):
        body = self._body("Clean body, nothing structural here.")
        with mock.patch("cli.subprocess.run") as run:
            code, out = self._file(
                ["file", "--title", "see config/app.yml", "--body-file", body]
            )
        self.assertEqual(code, 1)
        self.assertIn("BLOCK", out)
        run.assert_not_called()

    def test_file_passes_private_markers_to_the_guard(self):
        body = self._body("References acme-private internals.")
        with mock.patch("cli.subprocess.run") as run:
            code, out = self._file(
                ["file", "--title", "t", "--body-file", body, "--marker", "acme-private"]
            )
        self.assertEqual(code, 1)
        self.assertIn("acme-private", out)
        run.assert_not_called()

    def test_comment_posts_on_clean_body(self):
        body = self._body("+1 — also wanted by example-repo, motivated by note Y.")
        with mock.patch("cli.subprocess.run", return_value=SimpleNamespace(returncode=0)) as run:
            code, _ = self._file(
                ["comment", "--issue", "42", "--body-file", body, "--repo", "dividedby/skills"]
            )
        self.assertEqual(code, 0)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["gh", "issue", "comment"])
        self.assertIn("dividedby/skills", cmd)

    def test_comment_blocks_and_never_shells_to_gh(self):
        body = self._body("Mentions acme-secret in passing.")
        with mock.patch("cli.subprocess.run") as run:
            code, out = self._file(
                ["comment", "--issue", "42", "--body-file", body, "--marker", "acme-secret"]
            )
        self.assertEqual(code, 1)
        self.assertIn("BLOCK", out)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
