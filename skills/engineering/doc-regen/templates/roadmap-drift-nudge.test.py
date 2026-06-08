#!/usr/bin/env python3
"""Pins the census parser + drift computation in `roadmap-drift-nudge.py`
against a sample table (TEMPLATE — ships beside the hook). Run after editing
the config block to confirm ISSUE_COL / STATUS_COL / DONE_TOKEN match your
roadmap's column layout (run the file directly — the `.test.py` name is not a
`-m unittest` module path):

    python3 .claude/hooks/roadmap-drift-nudge.test.py

Stdlib only (ADR 0004). The hook's filename has hyphens, so it is loaded by
path rather than imported by name."""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "roadmap_drift_nudge", os.path.join(_HERE, "roadmap-drift-nudge.py"))
nudge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nudge)

# Default census schema: | # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
SAMPLE = """\
## Master census (all open issues)
| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ----- | -------- | ---- | ----- |
| 12 | first thing | W1 | **Next** | agent | `/tdd` | — | — |
| 34 | a closed one | W1 | Done | agent | `/tdd` | _#12_ | — |
| 56 | blocked thing | W2 | `Blocked` | human | — | #12 | wait on 12 |
"""


class TestParseCensus(unittest.TestCase):
    def test_extracts_number_and_status(self):
        rows = nudge.parse_census(SAMPLE)
        self.assertEqual(rows, {12: "next", 34: "done", 56: "blocked"})

    def test_skips_header_and_separator_rows(self):
        # Header ("#"/"Issue") and the `| - | --- |` row have no integer in ISSUE_COL.
        self.assertNotIn("issue", nudge.parse_census(SAMPLE))

    def test_strips_markdown_emphasis_from_status(self):
        rows = nudge.parse_census("| 7 | x | W1 | **Next** | a | b | c | d |")
        self.assertEqual(rows[7], "next")


class TestComputeDrift(unittest.TestCase):
    def test_stale_closed_when_gh_closed_but_census_not_done(self):
        rows = {12: "next", 34: "done"}
        states = {12: "closed", 34: "closed"}
        stale, unfiled = nudge.compute_drift(rows, states)
        self.assertEqual(stale, [12])   # 34 is already Done — not stale
        self.assertEqual(unfiled, [])

    def test_unfiled_open_when_gh_open_but_no_row(self):
        rows = {12: "next"}
        states = {12: "open", 99: "open"}
        stale, unfiled = nudge.compute_drift(rows, states)
        self.assertEqual(stale, [])
        self.assertEqual(unfiled, [99])

    def test_clean_when_in_sync(self):
        rows = {12: "next", 34: "done"}
        states = {12: "open", 34: "closed"}
        self.assertEqual(nudge.compute_drift(rows, states), ([], []))


if __name__ == "__main__":
    unittest.main()
