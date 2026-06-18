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


_HEX_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")


def _label_names(section_text: str) -> set[str]:
    """Extract backtick-quoted label names from a markdown table section.

    Strips hex color codes that appear in the Color column of the table
    (they are also backtick-quoted but are not label names).
    """
    candidates = re.findall(r"`([^`]+)`", section_text)
    return {c for c in candidates if not _HEX_COLOR.match(c)}


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
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        self.assertIn("needs-triage", _label_names(state))

    def test_core_state_contains_ready_for_agent(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        self.assertIn("ready-for-agent", _label_names(state))

    def test_core_state_contains_ready_for_human(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        self.assertIn("ready-for-human", _label_names(state))

    def test_core_state_contains_blocked(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        self.assertIn("blocked", _label_names(state))

    def test_core_state_contains_wontfix(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        self.assertIn("wontfix", _label_names(state))

    def test_core_state_contains_idea_inbox(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        self.assertIn("idea-inbox", _label_names(state))

    # --- CORE must NOT contain needs-info (dividedby posture suppresses it) ---

    def test_core_state_does_not_contain_needs_info(self):
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        self.assertNotIn(
            "needs-info",
            _label_names(state),
            "needs-info must not appear in CORE State — Matt's setup installs it; "
            "the dividedby composed layer removes it",
        )

    def test_core_category_does_not_contain_needs_info(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertTrue(cat.strip(), "CORE — Category (all repos) section is missing or empty")
        self.assertNotIn(
            "needs-info",
            _label_names(cat),
            "needs-info must not appear in CORE Category",
        )

    def test_core_size_does_not_contain_needs_info(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertTrue(size.strip(), "CORE — Size (all repos) section is missing or empty")
        self.assertNotIn(
            "needs-info",
            _label_names(size),
            "needs-info must not appear in CORE Size",
        )

    # --- CORE Category ---

    def test_core_category_contains_bug(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertTrue(cat.strip(), "CORE — Category (all repos) section is missing or empty")
        self.assertIn("bug", _label_names(cat))

    def test_core_category_contains_enhancement(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertTrue(cat.strip(), "CORE — Category (all repos) section is missing or empty")
        self.assertIn("enhancement", _label_names(cat))

    def test_core_category_contains_chore(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertTrue(cat.strip(), "CORE — Category (all repos) section is missing or empty")
        self.assertIn("chore", _label_names(cat))

    def test_core_category_contains_epic(self):
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertTrue(cat.strip(), "CORE — Category (all repos) section is missing or empty")
        self.assertIn("epic", _label_names(cat))

    # --- CORE Size ---

    def test_core_size_contains_size_s(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertTrue(size.strip(), "CORE — Size (all repos) section is missing or empty")
        self.assertIn("size:S", _label_names(size))

    def test_core_size_contains_size_m(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertTrue(size.strip(), "CORE — Size (all repos) section is missing or empty")
        self.assertIn("size:M", _label_names(size))

    def test_core_size_contains_size_l(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertTrue(size.strip(), "CORE — Size (all repos) section is missing or empty")
        self.assertIn("size:L", _label_names(size))

    def test_core_size_contains_size_xl(self):
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertTrue(size.strip(), "CORE — Size (all repos) section is missing or empty")
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
        self.assertTrue(loop.strip(), "LOOP/NETWORK section is missing or empty")
        loop_labels = _label_names(loop)
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        core_state_labels = _label_names(state)
        overlap = loop_labels & core_state_labels
        self.assertEqual(
            overlap,
            set(),
            f"LOOP/NETWORK labels leaked into CORE State: {overlap}",
        )

    def test_loop_labels_not_in_core_category(self):
        loop = _extract_section(self.text, "LOOP/NETWORK (full-tier repos)")
        self.assertTrue(loop.strip(), "LOOP/NETWORK section is missing or empty")
        loop_labels = _label_names(loop)
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertTrue(cat.strip(), "CORE — Category (all repos) section is missing or empty")
        core_cat_labels = _label_names(cat)
        overlap = loop_labels & core_cat_labels
        self.assertEqual(
            overlap,
            set(),
            f"LOOP/NETWORK labels leaked into CORE Category: {overlap}",
        )

    # --- CHANNELS section present and does not bleed into CORE ---

    def test_channels_section_present(self):
        channels = _extract_section(self.text, "CHANNELS (owned by `dividedby/skills`, applied by consumers)")
        self.assertTrue(
            channels.strip(),
            "CHANNELS section is missing from docs/agents/labels.md",
        )

    def test_channels_labels_not_in_core_state(self):
        channels = _extract_section(self.text, "CHANNELS (owned by `dividedby/skills`, applied by consumers)")
        self.assertTrue(channels.strip(), "CHANNELS section is missing or empty")
        channels_labels = _label_names(channels)
        state = _extract_section(self.text, "CORE — State (all repos)")
        self.assertTrue(state.strip(), "CORE — State (all repos) section is missing or empty")
        overlap = channels_labels & _label_names(state)
        self.assertEqual(
            overlap,
            set(),
            f"CHANNELS labels leaked into CORE State: {overlap}",
        )

    def test_channels_labels_not_in_core_category(self):
        channels = _extract_section(self.text, "CHANNELS (owned by `dividedby/skills`, applied by consumers)")
        self.assertTrue(channels.strip(), "CHANNELS section is missing or empty")
        channels_labels = _label_names(channels)
        cat = _extract_section(self.text, "CORE — Category (all repos)")
        self.assertTrue(cat.strip(), "CORE — Category (all repos) section is missing or empty")
        overlap = channels_labels & _label_names(cat)
        self.assertEqual(
            overlap,
            set(),
            f"CHANNELS labels leaked into CORE Category: {overlap}",
        )

    def test_channels_labels_not_in_core_size(self):
        channels = _extract_section(self.text, "CHANNELS (owned by `dividedby/skills`, applied by consumers)")
        self.assertTrue(channels.strip(), "CHANNELS section is missing or empty")
        channels_labels = _label_names(channels)
        size = _extract_section(self.text, "CORE — Size (all repos)")
        self.assertTrue(size.strip(), "CORE — Size (all repos) section is missing or empty")
        overlap = channels_labels & _label_names(size)
        self.assertEqual(
            overlap,
            set(),
            f"CHANNELS labels leaked into CORE Size: {overlap}",
        )

    # --- Tiering rule section present ---

    def test_tiering_rule_section_present(self):
        self.assertIn("## Tiering rule", self.text)


if __name__ == "__main__":
    unittest.main()
