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


# ---------------------------------------------------------------------------
# Tests: four-state model + must-fix + force-canonical (ADR 0027 / issue #393)
#
# The setup-dividedby-skills skill is prose (an LLM orchestrator), not an
# executable validator. These tests lock the convention-classification table,
# the must-fix drift shapes, and the force-canonical scope rules by asserting
# that the authoritative text in SKILL.md contains the required terms and
# structures.  If SKILL.md is edited in a way that removes or weakens these
# guarantees, the tests fail and require a conscious decision.
# ---------------------------------------------------------------------------

SKILL_MD = Path(__file__).resolve().parent / "SKILL.md"


class TestSkillMdFourStateModel(unittest.TestCase):
    """SKILL.md must describe all four outcome states from ADR 0027."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text(encoding="utf-8")

    def test_skill_md_present(self):
        self.assertTrue(SKILL_MD.exists(), f"SKILL.md not found at {SKILL_MD}")

    def test_four_states_create_present(self):
        self.assertIn(
            "create",
            self.text,
            "SKILL.md must mention the 'create' outcome state",
        )

    def test_four_states_update_present(self):
        self.assertIn(
            "update",
            self.text,
            "SKILL.md must mention the 'update' outcome state",
        )

    def test_four_states_skip_present(self):
        self.assertIn(
            "skip",
            self.text,
            "SKILL.md must mention the 'skip' outcome state",
        )

    def test_four_states_must_fix_present(self):
        self.assertIn(
            "must-fix",
            self.text,
            "SKILL.md must mention the 'must-fix' outcome state (ADR 0027)",
        )

    def test_skip_means_already_canonical(self):
        """'skip' must be redefined as 'already canonical', never 'left alone'."""
        self.assertIn(
            "already canonical",
            self.text,
            "SKILL.md must clarify that 'skip' means already canonical, not "
            "non-canonical-but-tolerated (ADR 0027)",
        )

    def test_four_state_posture_line(self):
        """The plan-building step must list all four states together."""
        self.assertIn(
            "must-fix",
            self.text,
            "The plan step must reference all four states including must-fix",
        )


class TestSkillMdMustFixDriftShapes(unittest.TestCase):
    """SKILL.md must enumerate the three known drift shapes that trigger must-fix."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text(encoding="utf-8")

    def test_drift_shape_stray_labels_md(self):
        """Stray labels.md (two-file split) must be identified as a must-fix shape."""
        self.assertIn(
            "labels.md",
            self.text,
            "SKILL.md must mention stray 'labels.md' as a must-fix drift shape",
        )

    def test_drift_shape_short_form_pointer(self):
        """Short-form/pointer triage-labels.md must be identified as a must-fix shape."""
        # The ADR uses the phrase "short-form" or "pointer" to describe this shape
        has_short_form = "short-form" in self.text
        has_pointer = "pointer" in self.text
        self.assertTrue(
            has_short_form or has_pointer,
            "SKILL.md must mention short-form or pointer triage-labels.md as a "
            "must-fix drift shape",
        )

    def test_drift_shape_labels_md_only(self):
        """labels.md-only repo (no triage-labels.md) must be identified as must-fix."""
        # Check that labels.md-only case is covered alongside the drift shapes
        self.assertIn(
            "labels.md",
            self.text,
            "SKILL.md must address the labels.md-only repo as a must-fix drift shape",
        )

    def test_must_fix_requires_confirmation(self):
        """must-fix actions must require explicit confirmation before applying."""
        text_lower = self.text.lower()
        has_confirm = "confirm" in text_lower
        self.assertTrue(
            has_confirm,
            "SKILL.md must require confirmation for must-fix items (ADR 0027 "
            "propose-only guarantee)",
        )

    def test_must_fix_surfaces_exact_diff(self):
        """must-fix must surface the exact destructive diff (what will be deleted/rewritten)."""
        text_lower = self.text.lower()
        has_diff = "diff" in text_lower or "destructive" in text_lower
        self.assertTrue(
            has_diff,
            "SKILL.md must state that must-fix surfaces the exact diff / "
            "destructive change before confirmation",
        )


class TestSkillMdForceCanonical(unittest.TestCase):
    """SKILL.md must describe force-canonical mode and its convention-only scope."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text(encoding="utf-8")

    def test_force_canonical_mode_present(self):
        self.assertIn(
            "force-canonical",
            self.text,
            "SKILL.md must describe the force-canonical opt-in mode (ADR 0027)",
        )

    def test_force_canonical_applies_without_per_item_prompt(self):
        """force-canonical applies must-fix items without per-deviation prompts."""
        text_lower = self.text.lower()
        # Should mention skipping per-item prompts or "no prompt" in force mode
        has_no_prompt = (
            "no per" in text_lower
            or "without per" in text_lower
            or "without prompting" in text_lower
            or "no prompt" in text_lower
        )
        self.assertTrue(
            has_no_prompt,
            "SKILL.md must state that force-canonical bypasses per-item prompts "
            "for convention-only must-fix items",
        )

    def test_force_canonical_scope_convention_only(self):
        """force-canonical must be restricted to convention-only items."""
        self.assertIn(
            "convention-only",
            self.text,
            "SKILL.md must state force-canonical is convention-only in scope (ADR 0027)",
        )

    def test_force_canonical_never_applies_judgment_bearing(self):
        """judgment-bearing items must always prompt, even in force-canonical mode."""
        self.assertIn(
            "judgment-bearing",
            self.text,
            "SKILL.md must define judgment-bearing items and state they always prompt",
        )

    def test_judgment_bearing_always_prompts(self):
        """The text must explicitly say judgment-bearing always prompts in force mode."""
        text_lower = self.text.lower()
        # "always prompts" or "still prompts" covering judgment-bearing in force mode
        has_always = (
            "always prompt" in text_lower
            or "still prompt" in text_lower
            or "never auto" in text_lower
        )
        self.assertTrue(
            has_always,
            "SKILL.md must explicitly state judgment-bearing items always prompt "
            "even in force-canonical mode",
        )


class TestSkillMdConventionClassification(unittest.TestCase):
    """SKILL.md must contain a convention-only vs judgment-bearing classification table."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text(encoding="utf-8")

    def test_classification_table_present(self):
        """A classification section or table must exist."""
        has_classification = (
            "convention-only" in self.text and "judgment-bearing" in self.text
        )
        self.assertTrue(
            has_classification,
            "SKILL.md must contain both 'convention-only' and 'judgment-bearing' "
            "classifications (ADR 0027)",
        )

    def test_concern_c_labels_classified_convention_only(self):
        """Concern C (GitHub labels: name/color/description) is convention-only."""
        # The label mechanics (name, color, description) are mechanical — no judgment
        self.assertIn(
            "convention-only",
            self.text,
            "SKILL.md must classify at least one concern as convention-only",
        )

    def test_concern_d_label_doc_form_classified_convention_only(self):
        """Concern D label-doc drift shapes (file layout) are convention-only."""
        # File layout (single vs split, full vs pointer) is purely mechanical
        self.assertIn(
            "convention-only",
            self.text,
            "SKILL.md must classify the label-doc file-form concerns as convention-only",
        )

    def test_concern_f_branching_classified_judgment_bearing(self):
        """Concern F (branching role classification) is judgment-bearing."""
        # Role classification (library/app) requires human judgment
        self.assertIn(
            "judgment-bearing",
            self.text,
            "SKILL.md must classify at least one concern (e.g. branching role) as "
            "judgment-bearing",
        )

    def test_new_conventions_must_declare_classification(self):
        """SKILL.md must state that new conventions must declare their classification."""
        text_lower = self.text.lower()
        has_declare = (
            "declare" in text_lower
            or "new convention" in text_lower
            or "must classify" in text_lower
        )
        self.assertTrue(
            has_declare,
            "SKILL.md must state that new conventions must declare whether they are "
            "convention-only or judgment-bearing (ADR 0027)",
        )


if __name__ == "__main__":
    unittest.main()
