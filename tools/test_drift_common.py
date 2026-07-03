"""Tests for _drift_common — pins the three checkers to the shared I/O layer.

No network calls, no mocking. Each assertion is an identity check (``is``):
if a future edit re-inlines one of these functions back into a checker
script instead of importing it from _drift_common, the corresponding
checker module gets its own distinct function object and this test fails
loudly.

Run: python3 -m unittest tools.test_drift_common
"""

import unittest

from tools import _drift_common
from tools import check_idea_inbox_drift, check_label_drift, check_workflow_drift

CHECKERS = (check_workflow_drift, check_label_drift, check_idea_inbox_drift)


class TestSharedIOFunctions(unittest.TestCase):
    """Each checker imports _gh/fetch_file/ensure_label/open_issues, not its own copy."""

    def test_gh_is_shared(self):
        for checker in CHECKERS:
            with self.subTest(checker=checker.__name__):
                self.assertIs(checker._gh, _drift_common._gh)

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


if __name__ == "__main__":
    unittest.main()
