#!/usr/bin/env python3
"""Registry test for docs/agents/labels.md.

Guards the canonical label registry against accidental mutation of the
CORE/LOOP split and the dividedby-specific posture (no needs-info in CORE).

Run: python3 skills/config/setup-dividedby-skills/labels.test.py
"""
import re
import sys
import unittest
from pathlib import Path

# Resolve from repo root regardless of cwd
REPO_ROOT = Path(__file__).resolve().parents[3]
LABELS_MD = REPO_ROOT / "docs" / "agents" / "labels.md"

# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------

def _extract_section(text: str, heading: str) -> str:
    """Return the text of the section under `heading` (up to the next ## heading)."""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r".*?\n(.+?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


def _label_names(section_text: str) -> set[str]:
    """Extract backtick-quoted label names from a markdown table section."""
    return set(re.findall(r"`([^`]+)`", section_text))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLabelsFileExists(unittest.TestCase):
    def test_labels_md_present(self):
        self.assertTrue(
            LABELS_MD.exists(),
            f"docs/agents/labels.md not found at {LABELS_MD}",
        )


class TestCoreSplit(unittest.TestCase):
    """CORE sections carry the right labels; LOOP/NETWORK stays separate."""

    @classmethod
    def setUpClass(cls):
        cls.text = LABELS_MD.read_text(encoding="utf-8")

    # --- CORE State ---

    def test_core_state_contains_needs_triage(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertIn("needs-triage", _label_names(state))

    def test_core_state_contains_ready_for_agent(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertIn("ready-for-agent", _label_names(state))

    def test_core_state_contains_ready_for_human(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertIn("ready-for-human", _label_names(state))

    def test_core_state_contains_blocked(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertIn("blocked", _label_names(state))

    def test_core_state_contains_wontfix(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertIn("wontfix", _label_names(state))

    def test_core_state_contains_idea_inbox(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertIn("idea-inbox", _label_names(state))

    # --- CORE must NOT contain needs-info (dividedby posture suppresses it) ---

    def test_core_state_does_not_contain_needs_info(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertNotIn(
            "needs-info",
            _label_names(state),
            "needs-info must not appear in CORE — Matt's setup installs it; "
            "the dividedby composed layer removes it",
        )

    # --- CORE Category ---

    def test_core_category_contains_bug(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertIn("bug", _label_names(cat))

    def test_core_category_contains_enhancement(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertIn("enhancement", _label_names(cat))

    def test_core_category_contains_chore(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertIn("chore", _label_names(cat))

    def test_core_category_contains_epic(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertIn("epic", _label_names(cat))

    # --- CORE Size ---

    def test_core_size_contains_size_s(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertIn("size:S", _label_names(size))

    def test_core_size_contains_size_m(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertIn("size:M", _label_names(size))

    def test_core_size_contains_size_l(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertIn("size:L", _label_names(size))

    def test_core_size_contains_size_xl(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertIn("size:XL", _label_names(size))

    # --- LOOP/NETWORK lives in its own section, not CORE ---

    def test_loop_section_present(self):
        loop = _extract_section(self.text, "LOOP/NETWORK (full-tier repos)")
        self.assertTrue(
            loop.strip(),
            "LOOP/NETWORK section is missing from docs/agents/labels.md",
        )

    def test_loop_labels_not_in_core_state(self):
        loop = _extract_section(self.text, "LOOP/NETWORK (full-tier repos)")
        loop_labels = _label_names(loop)
        state = _extract_section(self.text, "CORE — State (all repos)")
        core_state_labels = _label_names(state)
        overlap = loop_labels & core_state_labels
        self.assertEqual(
            overlap,
            set(),
            f"LOOP/NETWORK labels leaked into CORE State: {overlap}",
        )

    def test_loop_labels_not_in_core_category(self):
        loop = _extract_section(self.text, "LOOP/NETWORK (full-tier repos)")
        loop_labels = _label_names(loop)
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        core_cat_labels = _label_names(cat)
        overlap = loop_labels & core_cat_labels
        self.assertEqual(
            overlap,
            set(),
            f"LOOP/NETWORK labels leaked into CORE Category: {overlap}",
        )

    # --- CHANNELS section present ---

    def test_channels_section_present(self):
        channels = _extract_section(self.text, "CHANNELS (owned by `dividedby/skills`, applied by consumers)")
        self.assertTrue(
            channels.strip(),
            "CHANNELS section is missing from docs/agents/labels.md",
        )

    # --- Tiering rule section present ---

    def test_tiering_rule_section_present(self):
        self.assertIn("## Tiering rule", self.text)


if __name__ == "__main__":
    unittest.main()
