#!/usr/bin/env python3
"""Pins the PreToolUse commit guard in `roadmap-guard.py` (TEMPLATE — ships
beside the hook). Run after editing the config block to confirm ROADMAP and
BASE_BRANCH match your repo (run the file directly — the `.test.py` name is not
a `-m unittest` module path):

    python3 .claude/hooks/roadmap-guard.test.py

Stdlib only (ADR 0004). The hook's filename has hyphens, so it is loaded by
path rather than imported by name."""
import sys
sys.dont_write_bytecode = True  # don't leak __pycache__/ into a consumer's tracked hooks dir

import importlib.util
import io
import json
import os
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "roadmap_guard", os.path.join(_HERE, "roadmap-guard.py"))
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

ROADMAP = guard.ROADMAP


def _run_main(cmd, changed):
    """Drive main() end-to-end: feed a PreToolUse payload on stdin and stub the
    git-backed `_changed()` with a fixed file set. Returns the exit code."""
    payload = json.dumps({"tool_input": {"command": cmd}})
    with mock.patch.object(guard, "_changed", return_value=set(changed)), \
            mock.patch.object(sys, "stdin", io.StringIO(payload)), \
            mock.patch.object(sys, "stderr", io.StringIO()):
        return guard.main()


class TestDecision(unittest.TestCase):
    def test_no_issue_ref_allows(self):
        # A commit with no #NN is never enforced.
        self.assertEqual(_run_main('git commit -m "chore: tidy"', set()), 0)

    def test_issue_ref_roadmap_untouched_denies(self):
        self.assertEqual(_run_main('git commit -m "fix #12"', {"src/a.py"}), 2)

    def test_issue_ref_roadmap_staged_allows(self):
        self.assertEqual(_run_main('git commit -m "fix #12"', {ROADMAP}), 0)

    def test_non_commit_command_allows(self):
        # Even with a #NN, a non-commit command (e.g. git log) is not enforced.
        self.assertEqual(_run_main("git log --grep '#12'", set()), 0)


class TestFailOpen(unittest.TestCase):
    def test_malformed_stdin_fails_open(self):
        with mock.patch.object(sys, "stdin", io.StringIO("not json")):
            self.assertEqual(guard.main(), 0)

    def test_git_failure_returns_none(self):
        # When every git probe fails, _changed() signals "undeterminable" (None),
        # not an empty set, so the caller can fail open rather than deny.
        with mock.patch("subprocess.check_output", side_effect=OSError("no git")):
            self.assertIsNone(guard._changed())  # no crash

    def test_git_failure_fails_open_end_to_end(self):
        # An enforced #NN commit with git unusable must allow (exit 0), not deny.
        with mock.patch.object(guard, "_changed", return_value=None), \
                mock.patch.object(sys, "stdin",
                                  io.StringIO(json.dumps(
                                      {"tool_input": {"command": "git commit -m '#12'"}}))):
            self.assertEqual(guard.main(), 0)

    def test_decide_is_pure_allow_when_roadmap_present(self):
        self.assertEqual(guard.decide("git commit -m '#9'", {ROADMAP}), 0)

    def test_decide_is_pure_deny_when_absent(self):
        self.assertEqual(guard.decide("git commit -m '#9'", {"x"}), 2)

    def test_decide_none_fails_open(self):
        self.assertEqual(guard.decide("git commit -m '#9'", None), 0)


class TestBaseBranchList(unittest.TestCase):
    def test_string_base_normalized_to_list(self):
        with mock.patch.object(guard, "BASE_BRANCH", "main"):
            self.assertEqual(guard._base_branches(), ["main"])

    def test_list_base_preserved(self):
        with mock.patch.object(guard, "BASE_BRANCH", ["staging", "main"]):
            self.assertEqual(guard._base_branches(), ["staging", "main"])

    def test_changed_diffs_against_every_base(self):
        # _changed() must run a `git diff <base>...HEAD` for each base, so any
        # base where the roadmap moved satisfies the in-branch check.
        calls = []

        def fake_check_output(args, **kw):
            calls.append(args)
            # Roadmap only shows up vs the second base ("main"), not "staging".
            if args[:2] == ["git", "diff"] and args[-1] == "main...HEAD":
                return ROADMAP + "\n"
            return ""

        with mock.patch.object(guard, "BASE_BRANCH", ["staging", "main"]), \
                mock.patch("subprocess.check_output", side_effect=fake_check_output):
            changed = guard._changed()
        bases_diffed = [a[-1] for a in calls if a[-1].endswith("...HEAD")]
        self.assertEqual(bases_diffed, ["staging...HEAD", "main...HEAD"])
        self.assertIn(ROADMAP, changed)  # matched via the second base


if __name__ == "__main__":
    unittest.main()
