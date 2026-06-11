#!/usr/bin/env python3
"""Pins the census parser + drift computation in `roadmap-drift-nudge.py`
against a sample table (TEMPLATE — ships beside the hook). Run after editing
the config block to confirm ISSUE_COL / STATUS_COL / DONE_TOKEN match your
roadmap's column layout (run the file directly — the `.test.py` name is not a
`-m unittest` module path):

    python3 .claude/hooks/roadmap-drift-nudge.test.py

Stdlib only (ADR 0004). The hook's filename has hyphens, so it is loaded by
path rather than imported by name."""
import sys
sys.dont_write_bytecode = True  # don't leak __pycache__/ into a consumer's tracked hooks dir

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


# Same census with a `Points` column inserted after `Wave` (ADR 0026). Header
# auto-derivation resolves Status by name, so the inserted column shifts no index
# and the number→status mapping must be identical to the no-Points SAMPLE.
SAMPLE_WITH_POINTS = """\
## Master census (all open issues)
| # | Issue | Wave | Points | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ------ | ----- | -------- | ---- | ----- |
| 12 | first thing | W1 | 3 | **Next** | agent | `/tdd` | — | — |
| 34 | a closed one | W1 | 5 | Done | agent | `/tdd` | _#12_ | — |
| 56 | blocked thing | W2 | — | `Blocked` | human | — | #12 | wait on 12 |
"""


class TestParseCensus(unittest.TestCase):
    def test_extracts_number_and_status(self):
        rows = nudge.parse_census(SAMPLE)
        self.assertEqual(rows, {12: "next", 34: "done", 56: "blocked"})

    def test_skips_header_and_separator_rows(self):
        # Header ("#"/"Issue") and the `| - | --- |` row have no integer in ISSUE_COL.
        self.assertNotIn("issue", nudge.parse_census(SAMPLE))

    def test_strips_markdown_emphasis_from_status(self):
        table = ("| # | Issue | Wave | Status | a | b | c | d |\n"
                 "| 7 | x | W1 | **Next** | a | b | c | d |")
        rows = nudge.parse_census(table)
        self.assertEqual(rows[7], "next")

    def test_auto_derives_columns_from_default_header(self):
        # With ISSUE_COL/STATUS_COL left None, the columns are read from the header.
        self.assertEqual(nudge.resolve_cols(SAMPLE), (0, 3))

    def test_inserted_points_column_does_not_change_status_mapping(self):
        # A `Points` column after `Wave` (ADR 0026) is absorbed by header
        # auto-derivation: Status resolves to index 4 here vs 3 in SAMPLE, but the
        # number→status mapping is identical — the insertion breaks no parse.
        self.assertEqual(nudge.resolve_cols(SAMPLE_WITH_POINTS), (0, 4))
        self.assertEqual(nudge.parse_census(SAMPLE_WITH_POINTS),
                         nudge.parse_census(SAMPLE))


# A real-world divergent census: 9 columns, status LAST (index 8), `✅` = done,
# and the issue column lives at index 1 under an `Issue` header (not `#`).
EMOJI_SAMPLE = """\
## Master census
| Row | Issue | Wave | Owner | Skill(s) | Deps | Cluster | Notes | Status |
| --- | ----- | ---- | ----- | -------- | ---- | ------- | ----- | ------ |
| a | #12 | W1 | agent | `/tdd` | — | core | — | **Next** |
| b | #34 | W1 | agent | `/tdd` | — | core | — | ✅ |
"""


class TestAutoDeriveAndEmoji(unittest.TestCase):
    def test_derives_non_default_columns_from_header(self):
        # Issue under "Issue" header at index 1; "Status" header last at index 8.
        self.assertEqual(nudge.resolve_cols(EMOJI_SAMPLE), (1, 8))

    def test_parses_emoji_status_census(self):
        rows = nudge.parse_census(EMOJI_SAMPLE)
        self.assertEqual(rows, {12: "next", 34: "✅"})

    def test_emoji_done_token_marks_closed_as_not_stale(self):
        rows = nudge.parse_census(EMOJI_SAMPLE)
        states = {12: "open", 34: "closed"}
        original = nudge.DONE_TOKEN
        nudge.DONE_TOKEN = "✅"
        try:
            stale, unfiled = nudge.compute_drift(rows, states)
        finally:
            nudge.DONE_TOKEN = original
        self.assertEqual(stale, [])  # 34 is ✅ in census, GitHub-closed — in sync
        self.assertEqual(unfiled, [])

    def test_explicit_override_wins_over_header(self):
        original = (nudge.ISSUE_COL, nudge.STATUS_COL)
        nudge.ISSUE_COL, nudge.STATUS_COL = 1, 8
        try:
            self.assertEqual(nudge.resolve_cols(EMOJI_SAMPLE), (1, 8))
            self.assertEqual(nudge.parse_census(EMOJI_SAMPLE), {12: "next", 34: "✅"})
        finally:
            nudge.ISSUE_COL, nudge.STATUS_COL = original

    def test_no_matching_header_yields_empty(self):
        no_header = "| a | b |\n| 12 | next |"
        self.assertIsNone(nudge.resolve_cols(no_header))
        self.assertEqual(nudge.parse_census(no_header), {})


# A census with a collapsed closed wave (ADR 0023 progressive-disclosure): the
# `<details>`/`<summary>` and prose lines are non-table, and the closed rows inside
# the `<details>` are ordinary `| … |` rows. The parser keys off the leading `|`
# (and an integer issue cell), so the markup is ignored and the wrapped closed rows
# parse exactly as inline rows would — they must not be miscounted.
COLLAPSED_WAVE_SAMPLE = """\
## Master census (active waves inline)
| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ----- | -------- | ---- | ----- |
| 12 | open thing | W2 | **Next** | agent | `/tdd` | — | — |

<details>
<summary>Closed wave W1 — &lt;theme&gt;</summary>

W1 shipped the thing. Rows kept inline here until a newer wave supersedes them.

| 34 | a closed one | W1 | Done | agent | `/tdd` | _#12_ | — |
| 56 | another closed | W1 | Done | agent | — | — | — |

</details>
"""


class TestCollapsedClosedWave(unittest.TestCase):
    def test_parses_rows_inside_details_unchanged(self):
        # The `<details>`/`<summary>`/prose lines are skipped (no leading `|` or no
        # integer issue cell); the wrapped closed rows parse as normal Done rows.
        rows = nudge.parse_census(COLLAPSED_WAVE_SAMPLE)
        self.assertEqual(rows, {12: "next", 34: "done", 56: "done"})

    def test_collapsed_closed_rows_are_not_drift(self):
        # Both closed-and-Done rows inside the `<details>` are in sync with GitHub,
        # so neither shows as stale, and the lone open row is filed → no drift.
        rows = nudge.parse_census(COLLAPSED_WAVE_SAMPLE)
        states = {12: "open", 34: "closed", 56: "closed"}
        self.assertEqual(nudge.compute_drift(rows, states), ([], []))

    def test_pruned_closed_wave_does_not_resurface_as_unfiled(self):
        # After a wave is pruned (its rows gone), its closed issues have no census
        # row. compute_drift only flags *open* issues with no row, so closed pruned
        # issues stay silent — the prune is safe against the nudge (ADR 0023).
        rows = {12: "next"}  # W1 rows pruned; only the active W2 row remains
        states = {12: "open", 34: "closed", 56: "closed"}
        self.assertEqual(nudge.compute_drift(rows, states), ([], []))


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

    def test_aggregate_covered_excluded_from_unfiled(self):
        # Children tracked by an aggregate/epic row (no bare-integer row of their
        # own) must not read as "unfiled" once listed in AGGREGATE_COVERED.
        rows = {12: "next"}
        states = {12: "open", 298: "open", 299: "open", 99: "open"}
        original = nudge.AGGREGATE_COVERED
        nudge.AGGREGATE_COVERED = {298, 299}
        try:
            stale, unfiled = nudge.compute_drift(rows, states)
        finally:
            nudge.AGGREGATE_COVERED = original
        self.assertEqual(stale, [])
        self.assertEqual(unfiled, [99])  # 298/299 suppressed; 99 is genuine drift


if __name__ == "__main__":
    unittest.main()
