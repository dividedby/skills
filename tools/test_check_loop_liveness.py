"""Tests for check_loop_liveness — pure cadence/staleness logic + graceful no-op.

No network calls; run history and cron content are supplied via fixtures.

Run: python3 -m unittest tools.test_check_loop_liveness
"""

import unittest
from datetime import datetime, timezone
from io import StringIO
from unittest.mock import patch

from tools.check_loop_liveness import (
    check_liveness,
    cron_cadence_days,
    extract_cron,
    main,
)


class TestExtractCron(unittest.TestCase):
    def test_extracts_cron_from_workflow_yaml(self):
        content = 'on:\n  schedule:\n    - cron: "5 0 * * 1,3,6"\n'
        self.assertEqual(extract_cron(content), "5 0 * * 1,3,6")

    def test_returns_none_when_no_cron_present(self):
        self.assertIsNone(extract_cron("on:\n  workflow_dispatch:\n"))


class TestCronCadenceDays(unittest.TestCase):
    """Cadence parsed from the day-of-week field's comma count."""

    def test_three_days_a_week_cadence(self):
        # Mon/Wed/Sat, e.g. improve-codebase-architecture / apply-agent-research.
        self.assertAlmostEqual(cron_cadence_days("5 0 * * 1,3,6"), 7 / 3)

    def test_weekly_single_day_cadence(self):
        # e.g. changelog-health: Thursdays only.
        self.assertEqual(cron_cadence_days("33 1 * * 4"), 7.0)

    def test_daily_wildcard_dow_cadence(self):
        self.assertEqual(cron_cadence_days("0 4 * * *"), 1.0)

    def test_first_monday_marker_overrides_weekly_reading(self):
        # staleness-review's cron reads as weekly (dow=1) but the caller
        # stub's own comment documents the reusable body's job-level
        # first-Monday-of-month gate — that overrides the naive reading.
        content = "# Cron: first Monday of the month, 13:08 UTC = 08:08 CT.\n"
        self.assertEqual(cron_cadence_days("8 13 * * 1", content=content), 30.0)

    def test_unparsable_cron_returns_none(self):
        self.assertIsNone(cron_cadence_days("not a cron"))


class TestCheckLiveness(unittest.TestCase):
    """check_liveness: cadence + last-run info -> flag reason or None."""

    NOW = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc)

    def test_within_cadence_is_healthy(self):
        # 2 days old against a 2.33-day cadence (Mon/Wed/Sat loop) — inside 2x.
        reason = check_liveness(7 / 3, "2026-07-02T12:00:00Z", "success", now=self.NOW)
        self.assertIsNone(reason)

    def test_more_than_2x_cadence_flags(self):
        # ~33 days old against the same 2.33-day cadence — well past 2x.
        reason = check_liveness(7 / 3, "2026-06-01T12:00:00Z", "success", now=self.NOW)
        self.assertIsNotNone(reason)
        self.assertIn("no completed run", reason)

    def test_no_runs_at_all_flags(self):
        reason = check_liveness(7.0, None, None, now=self.NOW)
        self.assertEqual(reason, "no scheduled run found")

    def test_last_run_failed_flags_even_if_recent(self):
        reason = check_liveness(7.0, "2026-07-04T12:00:00Z", "failure", now=self.NOW)
        self.assertIsNotNone(reason)
        self.assertIn("failed", reason)

    def test_exactly_at_2x_threshold_is_still_healthy(self):
        # Boundary: age == 2x cadence exactly must not flag (strictly-greater rule).
        reason = check_liveness(7.0, "2026-06-20T12:00:00Z", "success", now=self.NOW)
        self.assertIsNone(reason)


class TestGracefulNoSecret(unittest.TestCase):
    """Empty --read-token must exit 0 with a NOTICE on stderr."""

    def test_no_token_exits_zero(self):
        with patch("sys.stderr", new_callable=StringIO) as mock_err:
            with self.assertRaises(SystemExit) as cm:
                main(["--read-token", ""])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("NOTICE", mock_err.getvalue())


if __name__ == "__main__":
    unittest.main()
