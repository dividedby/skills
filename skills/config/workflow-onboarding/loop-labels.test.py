#!/usr/bin/env python3
"""Install-plan test for the LOOP/NETWORK labels in docs/agents/labels.md.

Defines a pure function that parses the LOOP/NETWORK section of labels.md and
returns the install plan.  Guards the canonical set against accidental mutation.

Run: python3 -B skills/config/workflow-onboarding/loop-labels.test.py
"""
import re
import unittest
from pathlib import Path

# Resolve from repo root regardless of cwd
REPO_ROOT = Path(__file__).resolve().parents[3]
LABELS_MD = REPO_ROOT / "docs" / "agents" / "labels.md"

# ---------------------------------------------------------------------------
# Parse helpers (mirrored from setup-dividedby-skills/labels.test.py)
# ---------------------------------------------------------------------------

def _extract_section(text: str, heading: str) -> str:
    """Return the text of the section under `heading` (up to the next ## heading)."""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r".*?\n(.+?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


_HEX_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")

_TABLE_ROW = re.compile(
    r"^\|\s*`(?P<name>[^`]+)`\s*\|\s*`(?P<color>[^`]+)`\s*\|\s*(?P<description>[^|]+?)\s*\|",
    re.MULTILINE,
)


def _label_names(section_text: str) -> set[str]:
    """Extract backtick-quoted label names from a markdown table section.

    Strips hex color codes that appear in the Color column of the table
    (they are also backtick-quoted but are not label names).
    """
    candidates = re.findall(r"`([^`]+)`", section_text)
    return {c for c in candidates if not _HEX_COLOR.match(c)}


# ---------------------------------------------------------------------------
# Pure function — canonical install plan
# ---------------------------------------------------------------------------

LOOP_SECTION_HEADING = "LOOP/NETWORK (full-tier repos)"


def loop_label_install_plan(labels_md_text: str) -> list[dict]:
    """Parse the LOOP/NETWORK section of labels.md and return one install entry
    per label with keys: name, color, description.

    Pure function: text in → plan out.  No I/O, no side effects.
    """
    section = _extract_section(labels_md_text, LOOP_SECTION_HEADING)
    plan = []
    for m in _TABLE_ROW.finditer(section):
        name = m.group("name").strip()
        color = m.group("color").strip()
        description = m.group("description").strip()
        # Skip header separator rows and any non-label rows
        if _HEX_COLOR.match(name):
            continue
        plan.append({"name": name, "color": color, "description": description})
    return plan


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

CANONICAL_LOOP_LABELS = {
    "workflow-onboarding",
    "source:agent-research",
    "source:architecture-review",
    "source:staleness-review",
    "source:skill-audit",
    "source:changelog-health",
}

CORE_LABELS_SAMPLE = {"needs-triage", "bug", "size:M", "idea-inbox"}

CHANNELS_LABELS = {"skill-request", "skill-promotion", "awaiting-corroboration"}


class TestLabelsFileExists(unittest.TestCase):
    def test_labels_md_present(self):
        self.assertTrue(
            LABELS_MD.exists(),
            f"docs/agents/labels.md not found at {LABELS_MD}",
        )


class TestLoopLabelInstallPlan(unittest.TestCase):
    """Pure-function tests against the real registry."""

    @classmethod
    def setUpClass(cls):
        cls.text = LABELS_MD.read_text(encoding="utf-8")
        cls.plan = loop_label_install_plan(cls.text)
        cls.plan_names = {entry["name"] for entry in cls.plan}

    def test_plan_is_nonempty(self):
        self.assertTrue(self.plan, "loop_label_install_plan returned an empty list")

    def test_all_canonical_loop_labels_present(self):
        for name in CANONICAL_LOOP_LABELS:
            self.assertIn(
                name,
                self.plan_names,
                f"Canonical LOOP/NETWORK label '{name}' missing from install plan",
            )

    def test_no_core_labels_in_plan(self):
        for name in CORE_LABELS_SAMPLE:
            self.assertNotIn(
                name,
                self.plan_names,
                f"CORE label '{name}' must not appear in the LOOP/NETWORK install plan",
            )

    def test_no_channels_labels_in_plan(self):
        for name in CHANNELS_LABELS:
            self.assertNotIn(
                name,
                self.plan_names,
                f"CHANNELS label '{name}' must not appear in the LOOP/NETWORK install plan",
            )

    def test_each_entry_has_name(self):
        for entry in self.plan:
            self.assertTrue(entry.get("name"), f"Plan entry missing non-empty 'name': {entry}")

    def test_each_entry_has_color(self):
        for entry in self.plan:
            self.assertTrue(entry.get("color"), f"Plan entry missing non-empty 'color': {entry}")

    def test_each_entry_has_description(self):
        for entry in self.plan:
            self.assertTrue(
                entry.get("description"),
                f"Plan entry missing non-empty 'description': {entry}",
            )

    def test_plan_count_matches_canonical(self):
        self.assertEqual(
            len(self.plan),
            len(CANONICAL_LOOP_LABELS),
            f"Expected {len(CANONICAL_LOOP_LABELS)} entries in plan, got {len(self.plan)}: {self.plan_names}",
        )


if __name__ == "__main__":
    unittest.main()
