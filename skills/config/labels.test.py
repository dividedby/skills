#!/usr/bin/env python3
"""Source-registry guard for docs/agents/labels.md.

Asserts the canonical label set and tier boundaries for the SOURCE registry
(docs/agents/labels.md).  This is distinct from the scaffolded-copy test in
setup-dividedby-skills/labels.test.py, which guards the CORE/LOOP split logic
used when scaffolding a consumer repo.

Run: python3 -B skills/config/labels.test.py
"""
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LABELS_MD = REPO_ROOT / "docs" / "agents" / "labels.md"

# ---------------------------------------------------------------------------
# Parse helpers (identical pattern to setup-dividedby-skills/labels.test.py)
# ---------------------------------------------------------------------------

def _extract_section(text: str, heading: str) -> str:
    """Return the body of the ## section under `heading` (up to the next ##)."""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r".*?\n(.+?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


_HEX_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")


def _label_names(section_text: str) -> set:
    """Extract backtick-quoted label names, skipping hex color codes."""
    candidates = re.findall(r"`([^`]+)`", section_text)
    return {c for c in candidates if not _HEX_COLOR.match(c)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSourceRegistryExists(unittest.TestCase):
    def test_labels_md_present(self):
        self.assertTrue(
            LABELS_MD.exists(),
            f"docs/agents/labels.md not found at {LABELS_MD}",
        )


class TestCoreStateLabels(unittest.TestCase):
    """Every CORE State label is present in the source registry."""

    @classmethod
    def setUpClass(cls):
        cls.text = LABELS_MD.read_text(encoding="utf-8")
        cls.state = _extract_section(cls.text, "CORE — State (all repos)")

    def _names(self):
        return _label_names(self.state)

    def test_section_present(self):
        self.assertTrue(self.state.strip(), "CORE — State (all repos) section missing or empty")

    def test_needs_triage(self):
        self.assertIn("needs-triage", self._names())

    def test_ready_for_agent(self):
        self.assertIn("ready-for-agent", self._names())

    def test_ready_for_human(self):
        self.assertIn("ready-for-human", self._names())

    def test_blocked(self):
        self.assertIn("blocked", self._names())

    def test_wontfix(self):
        self.assertIn("wontfix", self._names())

    def test_idea_inbox(self):
        self.assertIn("idea-inbox", self._names())


class TestCoreCategoryLabels(unittest.TestCase):
    """Every CORE Category label is present in the source registry."""

    @classmethod
    def setUpClass(cls):
        cls.text = LABELS_MD.read_text(encoding="utf-8")
        cls.cat = _extract_section(cls.text, "CORE — Category (all repos)")

    def _names(self):
        return _label_names(self.cat)

    def test_section_present(self):
        self.assertTrue(self.cat.strip(), "CORE — Category (all repos) section missing or empty")

    def test_bug(self):
        self.assertIn("bug", self._names())

    def test_enhancement(self):
        self.assertIn("enhancement", self._names())

    def test_chore(self):
        self.assertIn("chore", self._names())

    def test_epic(self):
        self.assertIn("epic", self._names())


class TestCoreSizeLabels(unittest.TestCase):
    """Every CORE Size label is present in the source registry."""

    @classmethod
    def setUpClass(cls):
        cls.text = LABELS_MD.read_text(encoding="utf-8")
        cls.size = _extract_section(cls.text, "CORE — Size (all repos)")

    def _names(self):
        return _label_names(self.size)

    def test_section_present(self):
        self.assertTrue(self.size.strip(), "CORE — Size (all repos) section missing or empty")

    def test_size_s(self):
        self.assertIn("size:S", self._names())

    def test_size_m(self):
        self.assertIn("size:M", self._names())

    def test_size_l(self):
        self.assertIn("size:L", self._names())

    def test_size_xl(self):
        self.assertIn("size:XL", self._names())


class TestLoopNetworkLabels(unittest.TestCase):
    """LOOP/NETWORK section carries the right labels and does not leak into CORE tiers."""

    @classmethod
    def setUpClass(cls):
        cls.text = LABELS_MD.read_text(encoding="utf-8")
        cls.loop = _extract_section(cls.text, "LOOP/NETWORK (full-tier repos)")

    def _names(self):
        return _label_names(self.loop)

    def test_section_present(self):
        self.assertTrue(self.loop.strip(), "LOOP/NETWORK (full-tier repos) section missing or empty")

    def test_workflow_onboarding(self):
        self.assertIn("workflow-onboarding", self._names())

    def test_source_agent_research(self):
        self.assertIn("source:agent-research", self._names())

    def test_source_architecture_review(self):
        self.assertIn("source:architecture-review", self._names())

    def test_source_staleness_review(self):
        self.assertIn("source:staleness-review", self._names())

    def test_source_skill_audit(self):
        self.assertIn("source:skill-audit", self._names())

    def _assert_no_leak(self, core_heading: str, tier_label: str):
        core = _extract_section(self.text, core_heading)
        self.assertTrue(core.strip(), f"{core_heading} section missing or empty")
        overlap = self._names() & _label_names(core)
        self.assertEqual(overlap, set(), f"LOOP/NETWORK labels leaked into {tier_label}: {overlap}")

    def test_no_leak_into_core_state(self):
        self._assert_no_leak("CORE — State (all repos)", "CORE State")

    def test_no_leak_into_core_category(self):
        self._assert_no_leak("CORE — Category (all repos)", "CORE Category")

    def test_no_leak_into_core_size(self):
        self._assert_no_leak("CORE — Size (all repos)", "CORE Size")


class TestChannelsLabels(unittest.TestCase):
    """CHANNELS section carries the right labels and does not leak into CORE tiers."""

    _SECTION_HEADING = "CHANNELS (owned by `dividedby/skills`, applied by consumers)"

    @classmethod
    def setUpClass(cls):
        cls.text = LABELS_MD.read_text(encoding="utf-8")
        cls.channels = _extract_section(cls.text, cls._SECTION_HEADING)

    def _names(self):
        return _label_names(self.channels)

    def test_section_present(self):
        self.assertTrue(self.channels.strip(), "CHANNELS section missing or empty")

    def test_skill_request(self):
        self.assertIn("skill-request", self._names())

    def test_skill_promotion(self):
        self.assertIn("skill-promotion", self._names())

    def test_awaiting_corroboration(self):
        self.assertIn("awaiting-corroboration", self._names())

    def _assert_no_leak(self, core_heading: str, tier_label: str):
        core = _extract_section(self.text, core_heading)
        self.assertTrue(core.strip(), f"{core_heading} section missing or empty")
        overlap = self._names() & _label_names(core)
        self.assertEqual(overlap, set(), f"CHANNELS labels leaked into {tier_label}: {overlap}")

    def test_no_leak_into_core_state(self):
        self._assert_no_leak("CORE — State (all repos)", "CORE State")

    def test_no_leak_into_core_category(self):
        self._assert_no_leak("CORE — Category (all repos)", "CORE Category")

    def test_no_leak_into_core_size(self):
        self._assert_no_leak("CORE — Size (all repos)", "CORE Size")


class TestCrossLoopChannelLeak(unittest.TestCase):
    """LOOP/NETWORK and CHANNELS labels must not overlap each other."""

    @classmethod
    def setUpClass(cls):
        cls.text = LABELS_MD.read_text(encoding="utf-8")

    def test_loop_and_channels_disjoint(self):
        loop = _label_names(_extract_section(self.text, "LOOP/NETWORK (full-tier repos)"))
        channels = _label_names(
            _extract_section(
                self.text,
                "CHANNELS (owned by `dividedby/skills`, applied by consumers)",
            )
        )
        overlap = loop & channels
        self.assertEqual(overlap, set(), f"LOOP/NETWORK and CHANNELS share labels: {overlap}")


if __name__ == "__main__":
    unittest.main()
