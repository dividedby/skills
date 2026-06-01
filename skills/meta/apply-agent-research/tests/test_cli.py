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
import unittest
from contextlib import redirect_stdout

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


if __name__ == "__main__":
    unittest.main()
