"""Tests for tools/generate_adr_index.py — parse/cite/truncate logic.

The generator has ~22 branches but no unit coverage; integration-level CI
(adr-index.yml) only catches a stale file, not a silent logic regression.

Run: python3 -m unittest tools.test_generate_adr_index
"""

import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import tools.generate_adr_index as _mod
from tools.generate_adr_index import _adr_ref_pattern, _cite_map, _parse_adr


# ---------------------------------------------------------------------------
# _adr_ref_pattern
# ---------------------------------------------------------------------------

class TestAdrRefPattern(unittest.TestCase):

    def _pat(self, number: str) -> re.Pattern[str]:
        return _adr_ref_pattern(number)

    # "ADR 0001" — space-separated, canonical form
    def test_matches_adr_space_number(self):
        self.assertIsNotNone(self._pat("0001").search("See ADR 0001 for rationale."))

    # "ADR-0001" — hyphen-separated
    def test_matches_adr_hyphen_number(self):
        self.assertIsNotNone(self._pat("0001").search("per ADR-0001"))

    # "adr/0001" — path-style reference in markdown links
    def test_matches_adr_path_form(self):
        self.assertIsNotNone(self._pat("0001").search("[ADR 0001](adr/0001-some-title.md)"))

    # "0001-" — bare filename prefix
    def test_matches_bare_filename_prefix(self):
        self.assertIsNotNone(self._pat("0001").search("0001-buckets-cluster.md"))

    # Case-insensitive: "adr 1" / "ADR 1" must both match
    def test_case_insensitive_lower(self):
        self.assertIsNotNone(self._pat("0001").search("see adr 1 here"))

    def test_case_insensitive_upper(self):
        self.assertIsNotNone(self._pat("0001").search("see ADR 1 here"))

    # Leading zeros may be omitted in prose ("ADR 1" matches "0001")
    def test_matches_without_leading_zeros(self):
        self.assertIsNotNone(self._pat("0001").search("ADR 1 says so"))

    # Non-matching: a completely unrelated string
    def test_no_match_unrelated(self):
        self.assertIsNone(self._pat("0001").search("nothing relevant here"))

    # Non-matching: adjacent digit prevents match ("ADR 00011" should NOT match "0001")
    def test_no_match_longer_number(self):
        # "ADR 00011" contains an extra digit — the (?!\d) lookahead must block it.
        self.assertIsNone(self._pat("0001").search("ADR 00011"))

    # Different ADR numbers don't cross-match
    def test_no_cross_match(self):
        self.assertIsNone(self._pat("0002").search("see ADR 0001 here"))

    # Verify pattern for a two-digit-prefix number (e.g. 0018)
    def test_matches_higher_number(self):
        self.assertIsNotNone(self._pat("0018").search("ADR 0018 introduced config routing"))


# ---------------------------------------------------------------------------
# _parse_adr
# ---------------------------------------------------------------------------

class TestParseAdr(unittest.TestCase):

    def _write_adr(self, tmpdir: Path, name: str, content: str) -> Path:
        p = tmpdir / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_parses_number_from_filename(self):
        with TemporaryDirectory() as d:
            p = self._write_adr(Path(d), "0042-some-decision.md",
                                 "# Some Decision\n\nThis is the summary.\n")
            number, _, _ = _parse_adr(p)
            self.assertEqual(number, "0042")

    def test_parses_title_stripping_hash(self):
        with TemporaryDirectory() as d:
            p = self._write_adr(Path(d), "0001-foo.md",
                                 "# My Title\n\nFirst paragraph.\n")
            _, title, _ = _parse_adr(p)
            self.assertEqual(title, "My Title")

    def test_parses_first_paragraph(self):
        with TemporaryDirectory() as d:
            p = self._write_adr(Path(d), "0001-foo.md",
                                 "# Title\n\nThis is the summary sentence.\n")
            _, _, para = _parse_adr(p)
            self.assertEqual(para, "This is the summary sentence.")

    def test_skips_blank_lines_after_title(self):
        with TemporaryDirectory() as d:
            content = "# Title\n\n\n\nParagraph starts here.\n"
            p = self._write_adr(Path(d), "0001-foo.md", content)
            _, _, para = _parse_adr(p)
            self.assertEqual(para, "Paragraph starts here.")

    def test_skips_section_header_before_paragraph(self):
        # If a ## section header appears before any paragraph body, the parser
        # should skip it and use the paragraph found after it.
        with TemporaryDirectory() as d:
            content = "# Title\n\n## Context\n\nActual summary here.\n"
            p = self._write_adr(Path(d), "0001-foo.md", content)
            _, _, para = _parse_adr(p)
            self.assertEqual(para, "Actual summary here.")

    def test_multi_line_paragraph_collapsed(self):
        with TemporaryDirectory() as d:
            content = "# Title\n\nLine one\nline two\nline three.\n"
            p = self._write_adr(Path(d), "0001-foo.md", content)
            _, _, para = _parse_adr(p)
            self.assertEqual(para, "Line one line two line three.")

    def test_truncates_at_sentence_boundary_within_200(self):
        # Build a paragraph where the first sentence ends before 200 chars and
        # the full text exceeds 200 chars.  Expect truncation at sentence end.
        sentence_a = "A" * 80 + ". "    # 82 chars, ends at index 81 (". ")
        sentence_b = "B" * 150 + "."    # pushes total > 200
        with TemporaryDirectory() as d:
            content = f"# Title\n\n{sentence_a}{sentence_b}\n"
            p = self._write_adr(Path(d), "0001-foo.md", content)
            _, _, para = _parse_adr(p)
            # Must end with "." (sentence boundary), not "..."
            self.assertTrue(para.endswith("."))
            self.assertLessEqual(len(para), 200)
            self.assertNotIn("...", para)

    def test_truncates_at_197_when_no_sentence_boundary(self):
        # A single 250-char sentence with no ". " within the first 200 chars.
        long_word = "W" * 250
        with TemporaryDirectory() as d:
            content = f"# Title\n\n{long_word}\n"
            p = self._write_adr(Path(d), "0001-foo.md", content)
            _, _, para = _parse_adr(p)
            self.assertTrue(para.endswith("..."))
            self.assertEqual(len(para), 200)  # 197 chars + "..."

    def test_no_truncation_under_200(self):
        short = "Short summary."
        with TemporaryDirectory() as d:
            content = f"# Title\n\n{short}\n"
            p = self._write_adr(Path(d), "0001-foo.md", content)
            _, _, para = _parse_adr(p)
            self.assertEqual(para, short)

    def test_invalid_filename_raises(self):
        with TemporaryDirectory() as d:
            p = self._write_adr(Path(d), "README.md", "# Heading\n\nBody.\n")
            with self.assertRaises(ValueError):
                _parse_adr(p)

    def test_paragraph_stops_at_blank_line(self):
        # Only the first paragraph block should be captured; text after a blank
        # line belongs to the second paragraph.
        with TemporaryDirectory() as d:
            content = "# Title\n\nFirst para only.\n\nSecond para ignored.\n"
            p = self._write_adr(Path(d), "0001-foo.md", content)
            _, _, para = _parse_adr(p)
            self.assertEqual(para, "First para only.")

    def test_paragraph_stops_at_section_header_inside_para(self):
        # A section header that appears AFTER the paragraph has started should
        # terminate paragraph collection (in_para=True branch).
        with TemporaryDirectory() as d:
            content = "# Title\n\nFirst line\n## Section\n\nIgnored.\n"
            p = self._write_adr(Path(d), "0001-foo.md", content)
            _, _, para = _parse_adr(p)
            self.assertEqual(para, "First line")


# ---------------------------------------------------------------------------
# _cite_map
# ---------------------------------------------------------------------------

class TestCiteMap(unittest.TestCase):
    """Tests for _cite_map.

    _cite_map calls _skill_label internally, which resolves paths relative to
    the module-level SKILLS_DIR constant.  We patch that constant so temp
    files look like real skill files to the labeller.
    """

    def _make_skill(self, tmpdir: Path, rel: str, content: str) -> Path:
        p = tmpdir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_uncited_adr_returns_empty_list(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            sf = self._make_skill(root, "engineering/my-skill/SKILL.md",
                                   "No references here.")
            with patch.object(_mod, "SKILLS_DIR", root):
                result = _cite_map([sf], ["0001"])
            self.assertEqual(result["0001"], [])

    def test_cited_adr_returns_skill_label(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            sf = self._make_skill(root, "engineering/my-skill/SKILL.md",
                                   "See ADR 0001 for details.")
            with patch.object(_mod, "SKILLS_DIR", root):
                result = _cite_map([sf], ["0001"])
            self.assertEqual(len(result["0001"]), 1)

    def test_cited_skill_label_value(self):
        # Verify the label format: bucket stripped, .md suffix removed.
        with TemporaryDirectory() as d:
            root = Path(d)
            sf = self._make_skill(root, "engineering/my-skill/SKILL.md",
                                   "See ADR 0001 for details.")
            with patch.object(_mod, "SKILLS_DIR", root):
                result = _cite_map([sf], ["0001"])
            # bucket=engineering, parts>=3 -> label is "my-skill/SKILL"
            self.assertEqual(result["0001"], ["my-skill/SKILL"])

    def test_multiple_skills_cite_same_adr(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            sf1 = self._make_skill(root, "engineering/skill-a/SKILL.md",
                                    "See ADR-0002.")
            sf2 = self._make_skill(root, "engineering/skill-b/SKILL.md",
                                    "per ADR 0002")
            with patch.object(_mod, "SKILLS_DIR", root):
                result = _cite_map([sf1, sf2], ["0002"])
            self.assertEqual(len(result["0002"]), 2)

    def test_skill_citing_one_adr_not_another(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            sf = self._make_skill(root, "engineering/skill-a/SKILL.md",
                                   "ADR 0001 is relevant. 0003 is not.")
            with patch.object(_mod, "SKILLS_DIR", root):
                result = _cite_map([sf], ["0001", "0002"])
            self.assertEqual(len(result["0001"]), 1)
            self.assertEqual(result["0002"], [])

    def test_adr_0017_absent_does_not_error(self):
        # ADR-0017 does not exist in the repo (numbering skips 0016→0018).
        # _cite_map takes a plain list of numbers; an absent ADR has no files
        # that cite it and must return an empty list without error.
        with TemporaryDirectory() as d:
            root = Path(d)
            sf = self._make_skill(root, "engineering/skill-a/SKILL.md",
                                   "ADR 0016 and ADR 0018 are relevant.")
            with patch.object(_mod, "SKILLS_DIR", root):
                result = _cite_map([sf], ["0016", "0017", "0018"])
            self.assertEqual(result["0017"], [])
            self.assertGreater(len(result["0016"]), 0)
            self.assertGreater(len(result["0018"]), 0)

    def test_path_style_reference_matched(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            sf = self._make_skill(root, "engineering/skill-a/SKILL.md",
                                   "[link](adr/0005-some-title.md)")
            with patch.object(_mod, "SKILLS_DIR", root):
                result = _cite_map([sf], ["0005"])
            self.assertEqual(len(result["0005"]), 1)

    def test_bare_filename_prefix_matched(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            sf = self._make_skill(root, "engineering/skill-a/SKILL.md",
                                   "file 0007-some-decision.md is relevant")
            with patch.object(_mod, "SKILLS_DIR", root):
                result = _cite_map([sf], ["0007"])
            self.assertEqual(len(result["0007"]), 1)


if __name__ == "__main__":
    unittest.main()
