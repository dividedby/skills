#!/usr/bin/env python3
"""Self-test for the roadmap mirror render + commit-if-changed adapter (TEMPLATE
— ships beside `roadmap-mirror.py`). Run the file directly (the `.test.py` name
is not a `-m unittest` module path):

    python3 -B skills/engineering/roadmap/templates/roadmap-mirror.test.py

Covers the pure render (read-only banner + census carried through) and the
commit-if-changed adapter idempotency: a faked gh-API seam means the suite never
makes a live call. No write when the rendered body equals the current body; a
write on any difference. Stdlib only (ADR 0004)."""
import sys
sys.dont_write_bytecode = True  # don't leak __pycache__/ into a consumer's tracked tree

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "roadmap_mirror", os.path.join(_HERE, "roadmap-mirror.py"))
mirror = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mirror)

# A representative roadmap.md fixture (trimmed; carries a census table + a row).
FIXTURE = """\
# acme — Execution Roadmap (source of record)

> **Status:** active · **Owner:** maintainer + agents

## Master census (all open issues)
| # | Issue | Wave | Status | Owner | Skill(s) | Deps | Notes |
| - | ----- | ---- | ------ | ----- | -------- | ---- | ----- |
| 42 | wire the thing | W1 | **Next** | agent | `/tdd` | — | — |
"""


class TestRender(unittest.TestCase):
    def test_render_carries_read_only_banner(self):
        body = mirror.render(FIXTURE)
        self.assertIn("read-only", body.lower())
        self.assertIn("edit the doc, not this issue", body.lower())

    def test_render_carries_census(self):
        body = mirror.render(FIXTURE)
        # The census content survives the render so the mirror is glanceable.
        self.assertIn("Master census", body)
        self.assertIn("wire the thing", body)
        self.assertIn("| 42 |", body)

    def test_render_banner_precedes_census(self):
        body = mirror.render(FIXTURE)
        self.assertLess(body.lower().index("read-only"),
                        body.index("Master census"))

    def test_render_is_pure_and_deterministic(self):
        # Same input → same output; no I/O, no clock, no randomness.
        self.assertEqual(mirror.render(FIXTURE), mirror.render(FIXTURE))


class _FakeGh:
    """A fake gh-API seam: records the body it would PATCH, hands back a
    configurable current body. Stands in for live `gh api` calls."""

    def __init__(self, current):
        self.current = current
        self.patched = None
        self.fetches = 0

    def fetch_body(self, issue):
        self.fetches += 1
        return self.current

    def patch_body(self, issue, body):
        self.patched = body


class TestCommitIfChanged(unittest.TestCase):
    def test_no_write_when_unchanged(self):
        rendered = mirror.render(FIXTURE)
        gh = _FakeGh(current=rendered)
        wrote = mirror.update_mirror(gh, issue=7, roadmap_text=FIXTURE)
        self.assertFalse(wrote)
        self.assertIsNone(gh.patched)  # never PATCHed
        self.assertEqual(gh.fetches, 1)  # but it did fetch to compare

    def test_write_on_difference(self):
        gh = _FakeGh(current="something stale")
        wrote = mirror.update_mirror(gh, issue=7, roadmap_text=FIXTURE)
        self.assertTrue(wrote)
        self.assertEqual(gh.patched, mirror.render(FIXTURE))

    def test_write_when_mirror_empty(self):
        gh = _FakeGh(current="")
        wrote = mirror.update_mirror(gh, issue=7, roadmap_text=FIXTURE)
        self.assertTrue(wrote)
        self.assertEqual(gh.patched, mirror.render(FIXTURE))


if __name__ == "__main__":
    unittest.main()
