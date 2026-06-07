#!/usr/bin/env python3
"""Table-driven tests for the version-gap classifier (ADR 0004: pure, stdlib)."""
import unittest

from version_gap import classify, parse_version


class TestParseVersion(unittest.TestCase):
    CASES = [
        # raw                -> (major, minor, patch)
        ("18", (18, 0, 0)),
        ("18.17", (18, 17, 0)),
        ("18.17.1", (18, 17, 1)),
        ("v20.11.0", (20, 11, 0)),       # leading v
        (">=18.0.0", (18, 0, 0)),        # range operator
        ("^18.17.0", (18, 17, 0)),       # caret
        ("~18.17.0", (18, 17, 0)),       # tilde
        (" 18.17.1 ", (18, 17, 1)),      # whitespace
        ("20.x", (20, 0, 0)),            # x-range -> wildcard reads as 0
        ("lts/iron", None),              # codename, unparseable
        ("", None),
        ("not-a-version", None),
    ]

    def test_parse(self):
        for raw, expected in self.CASES:
            with self.subTest(raw=raw):
                self.assertEqual(parse_version(raw), expected)


class TestClassify(unittest.TestCase):
    CASES = [
        # current,    latest,    -> gap
        ("18.17.1", "18.17.1", "none"),    # equal
        ("18.17.1", "18.17.0", "none"),    # current ahead -> not stale
        ("18.17.1", "18.17.5", "patch"),   # patch behind
        ("18.17.1", "18.20.0", "minor"),   # minor behind
        ("18.17.1", "20.11.0", "major"),   # major behind
        ("18", "20", "major"),             # partial pins
        ("18", "18.17", "minor"),          # partial -> minor
        ("18.17", "18.17.4", "patch"),     # partial -> patch
        ("lts/iron", "20.11.0", "unknown"),  # unparseable current
        ("18.17.1", "garbage", "unknown"),   # unparseable latest
    ]

    def test_classify(self):
        for current, latest, expected in self.CASES:
            with self.subTest(current=current, latest=latest):
                self.assertEqual(classify(current, latest), expected)


if __name__ == "__main__":
    unittest.main()
