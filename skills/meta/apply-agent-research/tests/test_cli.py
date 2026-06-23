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
from contextlib import redirect_stderr, redirect_stdout
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
    def test_emits_the_chosen_candidates_as_json(self):
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
        self.assertEqual([c["dedup_key"] for c in result["file"]], ["deepen-x"])

    def test_honors_budget(self):
        payload = {
            "candidates": [
                {"dedup_key": "deepen-x", "priority": 3},
                {"dedup_key": "deepen-y", "priority": 2},
                {"dedup_key": "deepen-z", "priority": 1},
            ],
            "open_issues": [],
            "budget": 2,
        }
        code, out = _run(["gate"], stdin=json.dumps(payload))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(
            [c["dedup_key"] for c in result["file"]], ["deepen-x", "deepen-y"]
        )

    def test_files_nothing_when_candidate_already_open(self):
        payload = {
            "candidates": [{"dedup_key": "deepen-x", "priority": 3}],
            "open_issues": ["deepen-x"],
        }
        code, out = _run(["gate"], stdin=json.dumps(payload))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["file"], [])

    def test_honors_min_priority(self):
        payload = {
            "candidates": [{"dedup_key": "weak", "priority": 1}],
            "open_issues": [],
            "min_priority": 3,
        }
        _, out = _run(["gate"], stdin=json.dumps(payload))
        self.assertEqual(json.loads(out)["file"], [])

    def test_repairs_malformed_json_with_warning(self):
        # Trailing commas (one malformed blob) used to drop every channel's
        # candidates for the run (#369); now repaired with a loud warning.
        payload = '{"candidates": [{"dedup_key": "deepen-x", "priority": 3},], "open_issues": [],}'
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["gate"], stdin=io.StringIO(payload))
        self.assertEqual(code, 0)
        self.assertEqual(
            [c["dedup_key"] for c in json.loads(out.getvalue())["file"]], ["deepen-x"]
        )
        self.assertIn("::warning::", err.getvalue())
        self.assertIn("deterministic repair", err.getvalue())

    def test_unrepairable_json_fails_loudly(self):
        # Double-comma is NOT fully repaired in one pass -> fail loud (clear
        # message, non-zero exit), file nothing. ADR 0025 fail-loud floor.
        payload = '{"candidates": [{"dedup_key": "x", "priority": 1},,], "open_issues": []}'
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["gate"], stdin=io.StringIO(payload))
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("ERROR", err.getvalue())


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

    def test_file_cross_repo_injects_pat(self):
        """file --repo dividedby/skills with SKILLS_TRACKER_TOKEN set → GH_TOKEN == PAT."""
        body = self._body("A generalized improvement, no leaks.")
        with mock.patch.dict(os.environ, {"SKILLS_TRACKER_TOKEN": "PAT-xyz"}):
            with mock.patch(
                "cli.subprocess.run", return_value=SimpleNamespace(returncode=0)
            ) as run:
                self._file(
                    ["file", "--title", "t", "--body-file", body,
                     "--label", "skill-request", "--repo", "dividedby/skills"]
                )
        env_passed = run.call_args.kwargs["env"]
        self.assertEqual(env_passed["GH_TOKEN"], "PAT-xyz")

    def test_file_own_repo_does_not_get_pat(self):
        """file with no --repo should NOT override GH_TOKEN even when PAT is set."""
        body = self._body("A generalized improvement, no leaks.")
        with mock.patch.dict(os.environ, {"SKILLS_TRACKER_TOKEN": "PAT-xyz"}, clear=False):
            # Ensure GH_TOKEN is absent so we can confirm no injection occurred.
            os.environ.pop("GH_TOKEN", None)
            with mock.patch(
                "cli.subprocess.run", return_value=SimpleNamespace(returncode=0)
            ) as run:
                self._file(
                    ["file", "--title", "t", "--body-file", body,
                     "--label", "source:agent-research"]
                )
        env_passed = run.call_args.kwargs["env"]
        self.assertNotEqual(env_passed.get("GH_TOKEN", ""), "PAT-xyz")

    def test_file_other_repo_does_not_get_pat(self):
        """file --repo someone/evil with PAT set → PAT NOT injected."""
        body = self._body("A generalized improvement, no leaks.")
        with mock.patch.dict(os.environ, {"SKILLS_TRACKER_TOKEN": "PAT-xyz"}):
            os.environ.pop("GH_TOKEN", None)
            with mock.patch(
                "cli.subprocess.run", return_value=SimpleNamespace(returncode=0)
            ) as run:
                self._file(
                    ["file", "--title", "t", "--body-file", body,
                     "--repo", "someone/evil"]
                )
        env_passed = run.call_args.kwargs["env"]
        self.assertNotEqual(env_passed.get("GH_TOKEN", ""), "PAT-xyz")

    def test_file_cross_repo_pat_absent_no_override(self):
        """SKILLS_TRACKER_TOKEN unset, file --repo dividedby/skills → no PAT override."""
        body = self._body("A generalized improvement, no leaks.")
        env_without_pat = {k: v for k, v in os.environ.items()
                          if k not in ("SKILLS_TRACKER_TOKEN", "GH_TOKEN")}
        with mock.patch.dict(os.environ, env_without_pat, clear=True):
            with mock.patch(
                "cli.subprocess.run", return_value=SimpleNamespace(returncode=0)
            ) as run:
                self._file(
                    ["file", "--title", "t", "--body-file", body,
                     "--repo", "dividedby/skills"]
                )
        env_passed = run.call_args.kwargs["env"]
        self.assertNotIn("GH_TOKEN", env_passed)

    def test_comment_cross_repo_injects_pat(self):
        """comment --repo dividedby/skills with SKILLS_TRACKER_TOKEN set → GH_TOKEN == PAT."""
        body = self._body("+1 — also wanted by example-repo.")
        with mock.patch.dict(os.environ, {"SKILLS_TRACKER_TOKEN": "PAT-xyz"}):
            with mock.patch(
                "cli.subprocess.run", return_value=SimpleNamespace(returncode=0)
            ) as run:
                self._file(
                    ["comment", "--issue", "42", "--body-file", body,
                     "--repo", "dividedby/skills"]
                )
        env_passed = run.call_args.kwargs["env"]
        self.assertEqual(env_passed["GH_TOKEN"], "PAT-xyz")

    def test_comment_own_repo_does_not_get_pat(self):
        """comment with no --repo should NOT override GH_TOKEN even when PAT is set."""
        body = self._body("+1 — also wanted by example-repo.")
        with mock.patch.dict(os.environ, {"SKILLS_TRACKER_TOKEN": "PAT-xyz"}, clear=False):
            os.environ.pop("GH_TOKEN", None)
            with mock.patch(
                "cli.subprocess.run", return_value=SimpleNamespace(returncode=0)
            ) as run:
                self._file(["comment", "--issue", "42", "--body-file", body])
        env_passed = run.call_args.kwargs["env"]
        self.assertNotEqual(env_passed.get("GH_TOKEN", ""), "PAT-xyz")

    def test_cross_repo_block_never_shells_to_gh(self):
        """file --repo dividedby/skills with a forbidden body → BLOCK, gh not called."""
        body = self._body("Leaky:\n```\nsecret()\n```\n")
        with mock.patch.dict(os.environ, {"SKILLS_TRACKER_TOKEN": "PAT-xyz"}):
            with mock.patch("cli.subprocess.run") as run:
                code, out = self._file(
                    ["file", "--title", "t", "--body-file", body,
                     "--label", "skill-request", "--repo", "dividedby/skills"]
                )
        self.assertEqual(code, 1)
        self.assertIn("BLOCK", out)
        run.assert_not_called()


class FindOpenCommandTest(unittest.TestCase):
    """Tests for the cross-repo dedup read subcommand."""

    def _run_find_open(self, argv, gh_stdout="", gh_returncode=0, gh_stderr=""):
        out = io.StringIO()
        err = io.StringIO()
        result_ns = SimpleNamespace(
            returncode=gh_returncode, stdout=gh_stdout, stderr=gh_stderr
        )
        with mock.patch("cli.subprocess.run", return_value=result_ns) as run:
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(argv)
        return code, out.getvalue(), err.getvalue(), run

    def _issues_json(self, issues):
        return json.dumps(issues)

    def test_match_prints_number_and_exits_zero(self):
        issues = [
            {"number": 42, "body": "some text\n<!-- capability: my-slug -->\nmore"},
        ]
        code, out, _, run = self._run_find_open(
            ["find-open", "--repo", "dividedby/skills",
             "--label", "skill-request", "--capability", "my-slug"],
            gh_stdout=self._issues_json(issues),
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "42")
        # confirm argv includes --state open and --json
        cmd = run.call_args.args[0]
        self.assertIn("--state", cmd)
        self.assertIn("open", cmd)
        self.assertIn("--json", cmd)

    def test_match_injects_pat_when_skills_repo(self):
        issues = [{"number": 7, "body": "<!-- capability: test-cap -->"}]
        with mock.patch.dict(os.environ, {"SKILLS_TRACKER_TOKEN": "PAT-xyz"}):
            _, _, _, run = self._run_find_open(
                ["find-open", "--repo", "dividedby/skills",
                 "--label", "skill-request", "--capability", "test-cap"],
                gh_stdout=self._issues_json(issues),
            )
        env_passed = run.call_args.kwargs["env"]
        self.assertEqual(env_passed["GH_TOKEN"], "PAT-xyz")

    def test_no_match_empty_stdout_exit_zero(self):
        issues = [
            {"number": 5, "body": "<!-- capability: other-slug -->"},
        ]
        code, out, _, _ = self._run_find_open(
            ["find-open", "--repo", "dividedby/skills",
             "--label", "skill-request", "--capability", "my-slug"],
            gh_stdout=self._issues_json(issues),
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")

    def test_gh_failure_exits_nonzero_not_silent(self):
        """A gh failure must exit non-zero — never collapse into the empty 'no match' signal."""
        code, out, err, _ = self._run_find_open(
            ["find-open", "--repo", "dividedby/skills",
             "--label", "skill-request", "--capability", "my-slug"],
            gh_stdout="",
            gh_returncode=1,
            gh_stderr="gh: HTTP 401 Unauthorized",
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(out.strip(), "")
        self.assertIn("401", err)

    def test_no_issues_empty_stdout_exit_zero(self):
        code, out, _, _ = self._run_find_open(
            ["find-open", "--repo", "dividedby/skills",
             "--label", "skill-request", "--capability", "my-slug"],
            gh_stdout=self._issues_json([]),
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")


if __name__ == "__main__":
    unittest.main()
