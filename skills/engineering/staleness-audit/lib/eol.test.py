#!/usr/bin/env python3
"""Table-driven tests for the EOL-pastness decision (ADR 0004)."""
import datetime
import unittest

from eol import is_past_eol

TODAY = datetime.date(2026, 6, 6)


class TestIsPastEol(unittest.TestCase):
    CASES = [
        # eol_date,      today,  -> past?
        ("2023-09-11", TODAY, True),    # Node 16 — well past
        ("2025-04-30", TODAY, True),    # Node 18 — past today though it looks "recent"
        ("2026-06-05", TODAY, True),    # yesterday — past
        ("2026-06-06", TODAY, False),   # today — EOL is the last supported day, not yet past
        ("2026-06-07", TODAY, False),   # tomorrow — supported
        ("2030-04-30", TODAY, False),   # far future — supported
    ]

    def test_cases(self):
        for eol_date, today, expected in self.CASES:
            with self.subTest(eol_date=eol_date):
                self.assertEqual(is_past_eol(eol_date, today), expected)

    def test_accepts_a_date_object(self):
        self.assertTrue(is_past_eol(datetime.date(2020, 1, 1), TODAY))

    def test_unknown_eol_is_not_past(self):
        # no web data / unverified -> never treat as past (cannot manufacture urgency)
        self.assertFalse(is_past_eol(None, TODAY))
        self.assertFalse(is_past_eol("", TODAY))
        self.assertFalse(is_past_eol("unverified", TODAY))

    def test_defaults_today_to_real_today(self):
        # called with a long-past date and no `today` -> must be past
        self.assertTrue(is_past_eol("2000-01-01"))


if __name__ == "__main__":
    unittest.main()
