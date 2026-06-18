#!/usr/bin/env python3
"""Table-driven tests for the divergence classifier (pure stdlib, ADR 0004)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from divergence import (  # noqa: E402
    CATEGORIES,
    PROPOSAL_CATEGORIES,
    classify_skill,
    classify_upstream,
    diff,
    render_report,
    to_candidates,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def skill(name, pillars=()):
    return {"name": name, "pillars": list(pillars)}


def upstream_skill(name, pillars=(), source="matt"):
    return {"name": name, "pillars": list(pillars), "source": source}


# ---------------------------------------------------------------------------
# classify_skill
# ---------------------------------------------------------------------------

class TestClassifySkill(unittest.TestCase):
    def test_no_upstream_equivalent(self):
        ours = skill("my-skill", ["scan", "report"])
        self.assertEqual(classify_skill(ours, []), "NO_UPSTREAM_EQUIVALENT")

    def test_aligned_when_we_cover_all_upstream_pillars(self):
        ours = skill("foo", ["scan", "classify", "render"])
        up = [upstream_skill("foo", ["scan", "classify"])]
        self.assertEqual(classify_skill(ours, up), "ALIGNED")

    def test_aligned_when_upstream_has_no_pillars(self):
        ours = skill("foo", ["scan"])
        up = [upstream_skill("foo", [])]
        self.assertEqual(classify_skill(ours, up), "ALIGNED")

    def test_outdated_when_missing_a_pillar(self):
        ours = skill("foo", ["scan"])
        up = [upstream_skill("foo", ["scan", "classify"])]
        self.assertEqual(classify_skill(ours, up), "OUTDATED_HERE")

    def test_name_comparison_is_case_insensitive(self):
        ours = skill("Foo", ["scan"])
        up = [upstream_skill("foo", ["scan"])]
        self.assertEqual(classify_skill(ours, up), "ALIGNED")

    def test_pillar_comparison_is_case_insensitive(self):
        ours = skill("foo", ["Scan", "Classify"])
        up = [upstream_skill("foo", ["scan", "classify"])]
        self.assertEqual(classify_skill(ours, up), "ALIGNED")

    def test_multiple_upstream_sources_merged(self):
        # Matt has pillar A; KB has pillar B; we only cover A → OUTDATED
        ours = skill("foo", ["a"])
        up = [
            upstream_skill("foo", ["a"], source="matt"),
            upstream_skill("foo", ["b"], source="kb"),
        ]
        self.assertEqual(classify_skill(ours, up), "OUTDATED_HERE")


# ---------------------------------------------------------------------------
# classify_upstream
# ---------------------------------------------------------------------------

class TestClassifyUpstream(unittest.TestCase):
    def test_missing_here_when_we_have_no_match(self):
        up = upstream_skill("brand-new", ["scan"])
        self.assertEqual(classify_upstream(up, []), "MISSING_HERE")

    def test_delegates_to_classify_skill_when_match_found(self):
        up = upstream_skill("foo", ["scan", "report"])
        ours = [skill("foo", ["scan"])]
        # We're missing "report" → OUTDATED_HERE
        self.assertEqual(classify_upstream(up, ours), "OUTDATED_HERE")


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

class TestDiff(unittest.TestCase):
    def test_empty_inputs_return_empty(self):
        self.assertEqual(diff([], []), [])

    def test_our_skill_with_no_upstream_is_no_upstream_equivalent(self):
        results = diff([skill("mine")], [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "NO_UPSTREAM_EQUIVALENT")
        self.assertEqual(results[0]["name"], "mine")

    def test_upstream_skill_we_lack_is_missing_here(self):
        results = diff([], [upstream_skill("theirs")])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "MISSING_HERE")
        self.assertEqual(results[0]["name"], "theirs")

    def test_aligned_skill_included_in_results(self):
        results = diff([skill("foo", ["scan"])], [upstream_skill("foo", ["scan"])])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "ALIGNED")

    def test_outdated_skill_lists_missing_pillars(self):
        results = diff(
            [skill("foo", ["scan"])],
            [upstream_skill("foo", ["scan", "classify", "render"])],
        )
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r["category"], "OUTDATED_HERE")
        self.assertIn("classify", r["pillars"])
        self.assertIn("render", r["pillars"])

    def test_no_duplicate_rows_for_same_upstream_name(self):
        # Same upstream name appears once in our list and twice in upstream (two
        # sources): diff should produce exactly one row (Pass 1 hits it).
        ours = [skill("foo", ["scan"])]
        upstream = [
            upstream_skill("foo", ["scan"], source="matt"),
            upstream_skill("foo", ["report"], source="kb"),
        ]
        results = diff(ours, upstream)
        # Pass 2 must NOT add a second row for "foo" since it exists in our list
        names = [r["name"] for r in results]
        self.assertEqual(names.count("foo"), 1)
        self.assertEqual(results[0]["category"], "OUTDATED_HERE")

    def test_source_field_set_on_missing_here(self):
        results = diff([], [upstream_skill("theirs", source="kb")])
        self.assertEqual(results[0]["source"], "kb")


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------

class TestRenderReport(unittest.TestCase):
    def test_empty_divergences_returns_no_divergences_message(self):
        out = render_report([])
        self.assertIn("No divergences found", out)

    def test_aligned_omitted_by_default(self):
        divs = [
            {"name": "foo", "category": "ALIGNED", "detail": "...", "source": "both", "pillars": []},
        ]
        out = render_report(divs)
        self.assertIn("All skills are aligned", out)
        self.assertNotIn("foo", out)

    def test_aligned_included_when_flag_set(self):
        divs = [
            {"name": "foo", "category": "ALIGNED", "detail": "all good", "source": "both", "pillars": []},
        ]
        out = render_report(divs, include_aligned=True)
        self.assertIn("foo", out)

    def test_report_contains_markdown_table_header(self):
        divs = [
            {"name": "bar", "category": "MISSING_HERE", "detail": "missing", "source": "matt", "pillars": []},
        ]
        out = render_report(divs)
        self.assertIn("| skill |", out)
        self.assertIn("bar", out)
        self.assertIn("MISSING_HERE", out)

    def test_pipe_chars_in_detail_escaped(self):
        divs = [
            {"name": "x", "category": "MISSING_HERE", "detail": "a | b", "source": "matt", "pillars": []},
        ]
        out = render_report(divs)
        self.assertIn(r"a \| b", out)


# ---------------------------------------------------------------------------
# to_candidates
# ---------------------------------------------------------------------------

class TestToCandidates(unittest.TestCase):
    def test_aligned_and_no_upstream_not_included(self):
        divs = [
            {"name": "a", "category": "ALIGNED", "detail": "", "source": "both", "pillars": []},
            {"name": "b", "category": "NO_UPSTREAM_EQUIVALENT", "detail": "", "source": "ours", "pillars": []},
        ]
        self.assertEqual(to_candidates(divs), [])

    def test_missing_here_becomes_candidate(self):
        divs = [
            {"name": "foo", "category": "MISSING_HERE", "detail": "...", "source": "matt", "pillars": []},
        ]
        cands = to_candidates(divs)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["dedup_key"], "divergence-missing-foo")
        self.assertEqual(cands[0]["priority"], 3)

    def test_outdated_here_becomes_candidate(self):
        divs = [
            {"name": "bar", "category": "OUTDATED_HERE", "detail": "...", "source": "both", "pillars": ["x"]},
        ]
        cands = to_candidates(divs)
        self.assertEqual(cands[0]["dedup_key"], "divergence-outdated-bar")
        self.assertEqual(cands[0]["priority"], 2)

    def test_diverged_has_highest_priority(self):
        divs = [
            {"name": "baz", "category": "DIVERGED", "detail": "...", "source": "both", "pillars": []},
        ]
        cands = to_candidates(divs)
        self.assertEqual(cands[0]["priority"], 4)

    def test_sorted_by_priority_descending(self):
        divs = [
            {"name": "low", "category": "OUTDATED_HERE", "detail": "", "source": "both", "pillars": []},
            {"name": "high", "category": "DIVERGED", "detail": "", "source": "both", "pillars": []},
        ]
        cands = to_candidates(divs)
        self.assertEqual(cands[0]["name"], "high")

    def test_dedup_key_normalizes_spaces_and_underscores(self):
        divs = [
            {"name": "my skill", "category": "MISSING_HERE", "detail": "", "source": "matt", "pillars": []},
        ]
        cands = to_candidates(divs)
        self.assertEqual(cands[0]["dedup_key"], "divergence-missing-my-skill")

    def test_categories_constant_integrity(self):
        self.assertTrue(PROPOSAL_CATEGORIES.issubset(CATEGORIES))


if __name__ == "__main__":
    unittest.main()
