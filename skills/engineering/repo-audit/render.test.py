"""Self-tests for render.py, which builds the repo-audit report page.

Standard library only. Inputs are evals/sample-findings.json and
evals/sample-page-extra.json, changed per test. The structure of the output is
checked by render.check_output (tags, ids, links, leftover tokens); the tests
below show it fails on each fault and passes the sample.

Run: python3 -B skills/engineering/repo-audit/render.test.py
"""

from __future__ import annotations

import base64
import contextlib
import copy
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "evals"))
import findings_check
import render

SAMPLE_F = json.loads((HERE / "evals" / "sample-findings.json").read_text())
SAMPLE_X = json.loads((HERE / "evals" / "sample-page-extra.json").read_text())
TEMPLATE = (HERE / "template.html").read_text()
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def docs():
    return copy.deepcopy(SAMPLE_F), copy.deepcopy(SAMPLE_X)


def finding(ident, area, severity="med", title="A finding", **kw):
    return {
        "id": ident,
        "key": f"{area}:check:{ident}.py",
        "area": area,
        "severity": severity,
        "title": title,
        "evidence": "x.py:1 evidence",
        "fix": "Fix it",
        "effort": "S",
        "rule_source": None,
        "also_reported_by": [],
        "package": None,
        **kw,
    }


def build(f, x, template=TEMPLATE, base=HERE):
    return render.render(f, x, template, base)


def failures(f, x, template=TEMPLATE, base=HERE):
    with unittest.TestCase().assertRaises(render.RenderError) as cm:
        build(f, x, template, base)
    return "\n".join(cm.exception.errors)


def table(page, caption):
    m = re.search(
        rf"<table[^>]*>\s*<caption>\s*{re.escape(caption)}\s*</caption>.*?</table>",
        page,
        re.DOTALL,
    )
    assert m, f"no table {caption!r}"
    return m.group(0)


def cells(table_html, first):
    """The cells of the row whose first cell reads `first` (a link's text counts)."""
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL):
        found = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if found and re.sub(r"<[^>]+>", "", found[0]).strip() == first:
            return [c.strip() for c in found]
    raise AssertionError(f"no row {first!r}")


def section(page, ident):
    m = re.search(rf'<h2 id="{ident}">.*?(?=<h2 |</div>\s*<script>)', page, re.DOTALL)
    assert m, f"no section {ident}"
    return m.group(0)


def h2_ids(page):
    return re.findall(r'<h2 id="([^"]+)"', page)


def nav_ids(page):
    nav = re.search(r'<nav class="nav".*?</nav>', page, re.DOTALL).group(0)
    return re.findall(r'href="#([^"]+)"', nav)


def add_design_finding(f, x):
    """A High usability finding, with the scorecard row and intro that go with it."""
    f["findings"].append(finding("usability-1", "usability", "high"))
    row = next(r for r in f["scorecard"]["areas"] if r["area"] == "usability")
    row.update(
        applies=True,
        verdict="not_ready",
        not_assessed_reason=None,
        top_finding="usability-1",
    )
    x["intros"]["usability"] = "One flow fails."
    # A design verdict needs the design lens: a standard run that launched it.
    for fact in f["profile"]:
        if fact["fact"] == "depth":
            fact["value"] = "standard"
    f["lens_coverage"].append(
        {"lens": "design", "read": "the UI", "chosen_by": "Small tier: everything"}
    )


class HeaderAndScorecard(unittest.TestCase):
    def test_pill_class_and_label_follow_the_overall_verdict(self):
        want = {
            "not_ready": ("not-ready", "Not ready"),
            "ready_with_fixes": ("fixes", "Ready with fixes"),
            "ready": ("ready", "Ready"),
            "not_assessed": ("not-assessed", "Not assessed"),
        }
        for overall, (cls, label) in want.items():
            with self.subTest(overall):
                f, x = docs()
                f["scorecard"]["overall"] = (
                    overall  # a Blocker stays: nothing recomputes
                )
                page = build(f, x)
                self.assertIn(f'<span class="pill {cls}">{label}</span>', page)

    def test_header_reads_commit_and_branch_from_the_profile(self):
        page = build(*docs())
        self.assertIn("fee-tool · main @ d60d377 ·", page)
        self.assertIn("<title>fee-tool Audit</title>", page)

    def test_blockers_list_names_finding_and_area_and_goes_when_empty(self):
        f, x = docs()
        page = build(f, x)
        self.assertIn(
            '<li><a href="#security-1">A GitHub token is committed in config.ini</a> (Security)</li>',
            page,
        )
        f["scorecard"]["blockers"] = []
        x["plan"]["now"]["items"] = []
        page = build(f, x)
        self.assertNotIn("<h3>Blockers</h3>", page)

    def test_scorecard_rows_follow_rubric_order_with_dashes_and_reasons(self):
        page = build(*docs())
        card = table(page, "Verdict per area")
        titles = [
            re.sub(r"<[^>]+>", "", re.findall(r"<td>(.*?)</td>", row, re.DOTALL)[0])
            for row in re.findall(r"<tr>(.*?)</tr>", card, re.DOTALL)[1:]
        ]
        self.assertEqual(titles, list(render.AREAS.values()))
        self.assertEqual(
            cells(card, "Architecture")[1:],
            ['<span class="pill ready">Ready</span>', render.DASH, render.DASH],
        )
        self.assertEqual(
            cells(card, "Data integrity")[1:],
            [
                '<span class="pill not-assessed">Not assessed</span>',
                "Not applicable: no data store",
                render.DASH,
            ],
        )
        self.assertEqual(
            cells(card, "Security")[2:],
            [
                "A GitHub token is committed in config.ini",
                '<a href="#security-1">security-1</a>',
            ],
        )

    def test_area_name_links_only_to_an_emitted_section(self):
        card = table(build(*docs()), "Verdict per area")
        self.assertIn('<a href="#security">Security</a>', card)
        self.assertNotIn('href="#privacy"', card)

    def test_package_table_only_for_a_monorepo(self):
        f, x = docs()
        self.assertNotIn("Verdict per package", build(f, x))
        f["scorecard"]["packages"] = [
            {
                "package": "web",
                "type": "Web app",
                "verdict": "ready_with_fixes",
                "not_assessed_reason": None,
                "top_finding": "tests-1",
            },
            {
                "package": "docs",
                "type": "Docs",
                "verdict": "not_assessed",
                "not_assessed_reason": "Not selected",
                "top_finding": None,
            },
        ]
        pkgs = table(build(f, x), "Verdict per package")
        self.assertIn('<table class="wide">', pkgs)
        self.assertEqual(
            cells(pkgs, "docs")[1:],
            [
                "Docs",
                '<span class="pill not-assessed">Not assessed</span>',
                "Not selected",
                render.DASH,
            ],
        )


class AreaSections(unittest.TestCase):
    def test_a_section_exists_only_for_an_area_with_findings(self):
        page = build(*docs())
        self.assertEqual(
            [i for i in h2_ids(page) if i in render.AREAS],
            ["code-quality", "tests", "security", "external-facts"],
        )

    def test_rows_sort_by_severity_then_natural_id(self):
        f, x = docs()
        f["findings"] += [
            finding("tests-10", "tests"),
            finding("tests-2", "tests"),
            finding("tests-3", "tests", "low"),
            finding("tests-4", "tests", "high"),
        ]
        body = section(build(f, x), "tests")
        order = re.findall(r'<tr id="([^"]+)"', body)
        self.assertEqual(
            order, ["tests-4", "tests-1", "tests-2", "tests-10", "tests-3"]
        )

    def test_severity_class_and_label_map(self):
        f, x = docs()
        f["findings"].append(finding("tests-5", "tests", "high"))
        body = section(build(f, x), "tests")
        self.assertIn('<span class="sev hi">HIGH</span>', body)
        self.assertIn('<span class="sev med">MED</span>', body)

    def test_also_reported_by_shows_only_when_a_lens_merged(self):
        page = build(*docs())
        self.assertIn("Also reported by: code", section(page, "external-facts"))
        self.assertNotIn("Also reported by", section(page, "security"))

    def test_evidence_list_joins_and_text_is_escaped(self):
        f, x = docs()
        f["findings"][0]["title"] = "<img src=x onerror=1> & co"
        f["findings"][0]["evidence"] = ["a.py:1", "b.py:2 <b>"]
        page = build(f, x)
        self.assertIn("&lt;img src=x onerror=1&gt; &amp; co", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("<code>a.py:1; b.py:2 &lt;b&gt;</code>", page)

    def test_area_intro_rules(self):
        cases = {
            "findings but no intro": (
                lambda f, x: x["intros"].pop("security"),
                "no intro",
            ),
            "intro for a Not-assessed area": (
                lambda f, x: x["intros"].update({"tech-stack": "Words."}),
                "Not-assessed area has no section",
            ),
        }
        for name, (mutate, expected) in cases.items():
            with self.subTest(name):
                f, x = docs()
                mutate(f, x)
                self.assertIn(expected, failures(f, x))

    def test_an_intro_keeps_a_section_with_no_findings_and_drops_its_empty_table(self):
        f, x = docs()
        x["intros"]["privacy"] = "Nothing found."
        body = section(build(f, x), "privacy")
        self.assertIn("Nothing found.", body)
        self.assertNotIn("<table", body)

    def test_extra_tables_sit_between_intro_and_finding_table(self):
        body = section(build(*docs()), "external-facts")
        self.assertLess(body.index("<caption>"), body.index("<th>Severity</th>"))
        self.assertIn('<table class="wide">', body)

    def test_nav_links_match_the_emitted_sections(self):
        page = build(*docs())
        self.assertEqual(nav_ids(page), h2_ids(page))

    def test_tables_for_a_missing_section_fail(self):
        f, x = docs()
        x["tables"].append(
            {
                "section": "repo-hygiene",
                "caption": "Cruft",
                "head": ["Path"],
                "rows": [["a"]],
            }
        )
        self.assertIn("`repo-hygiene` has tables but no section", failures(f, x))


class Standards(unittest.TestCase):
    def standards(self):
        f, x = docs()
        x["standards"]["rows"] = [
            {
                "id": "ci-tests",
                "requirement": "CI runs the tests",
                "source": "standards.md",
                "result": "fail",
                "severity": "high",
                "evidence": "no workflow",
                "fix": "Add one",
            },
            {"id": "readme", "requirement": "README", "source": "s", "result": "pass"},
            {
                "id": "docker",
                "requirement": "Dockerfile",
                "source": "s",
                "result": "na",
            },
            {
                "id": "gate",
                "requirement": "Report only",
                "source": "s",
                "result": "unchecked",
                "label": "FLAG",
                "severity": "low",
            },
        ]
        f["findings"].append(finding("fs-ci-tests", "tests", "high"))
        next(r for r in f["scorecard"]["areas"] if r["area"] == "tests")[
            "top_finding"
        ] = "fs-ci-tests"
        return f, x

    def test_severity_span_only_on_fail_and_flag_rows(self):
        page = build(*self.standards())
        body = section(page, "standards")
        rows = dict(re.findall(r'<tr id="fs-([^"]+)">(.*?)</tr>', body, re.DOTALL))
        self.assertEqual(set(rows), {"ci-tests", "readme", "docker", "gate"})
        for ident, has_sev in {
            "ci-tests": True,
            "gate": True,
            "readme": False,
            "docker": False,
        }.items():
            with self.subTest(ident):
                self.assertEqual('<span class="sev' in rows[ident], has_sev)
        self.assertIn('<span class="res fail">FAIL</span', rows["ci-tests"])
        self.assertIn('<span class="res unchecked">FLAG</span', rows["gate"])
        self.assertIn('<span class="res na">N/A</span', rows["docker"])

    def test_a_fleet_fail_is_a_standards_row_not_a_finding_row(self):
        page = build(*self.standards())
        self.assertEqual(page.count('id="fs-ci-tests"'), 1)
        self.assertNotIn('<tr id="fs-ci-tests"', section(page, "tests"))
        self.assertIn('<a href="#fs-ci-tests">fs-ci-tests</a>', page)

    def test_no_rows_deletes_the_table_and_keeps_the_section(self):
        body = section(build(*docs()), "standards")
        self.assertIn("Not assessed (Needs X: a remote)", body)
        self.assertNotIn("<table", body)

    def test_row_faults(self):
        def fail_without_severity(f, x):
            del x["standards"]["rows"][0]["severity"]

        def pass_with_severity(f, x):
            x["standards"]["rows"][1]["severity"] = "low"

        def flag_on_a_fail(f, x):
            x["standards"]["rows"][0]["label"] = "OK"

        def orphan_finding(f, x):
            x["standards"]["rows"].pop(0)

        def severity_differs(f, x):
            x["standards"]["rows"][0]["severity"] = "low"

        def fail_without_finding(f, x):
            f["findings"] = [i for i in f["findings"] if i["id"] != "fs-ci-tests"]
            next(r for r in f["scorecard"]["areas"] if r["area"] == "tests")[
                "top_finding"
            ] = "tests-1"

        def finding_for_a_pass_row(f, x):
            f["findings"].append(finding("fs-readme", "tests", "low"))

        cases = {
            "has a standards row that is not a fail": finding_for_a_pass_row,
            "differs from finding `fs-ci-tests` (high)": severity_differs,
            "a fail row has no finding `fs-ci-tests`": fail_without_finding,
            "severity is required": fail_without_severity,
            "only for fail and FLAG": pass_with_severity,
            "does not fit result": flag_on_a_fail,
            "has no row in standards.rows": orphan_finding,
        }
        for expected, mutate in cases.items():
            with self.subTest(expected):
                f, x = self.standards()
                mutate(f, x)
                self.assertIn(expected, failures(f, x))


class PlanSinceCoverage(unittest.TestCase):
    def test_plan_phases_hold_their_own_items(self):
        page = build(*docs())
        phases = re.findall(r'<div class="phase">(.*?)</ol>\s*</div>', page, re.DOTALL)
        self.assertEqual([len(re.findall(r"<li>", p)) for p in phases], [1, 2, 1])
        self.assertIn('<a class="go" href="#security-1">finding</a>', phases[0])

    def test_plan_faults(self):
        def dangling(f, x):
            x["plan"]["next"]["items"][0]["finding"] = "nope-9"

        def blocker_not_in_now(f, x):
            x["plan"]["now"]["items"] = []

        for expected, mutate in {
            "dangling link #nope-9": dangling,
            "Blocker `security-1` is not in Now": blocker_not_in_now,
        }.items():
            with self.subTest(expected):
                f, x = docs()
                mutate(f, x)
                self.assertIn(expected, failures(f, x))

    def diff(self):
        return {
            "previous_url": "https://example.com/prev",
            "new": ["security:secret-scan:config.ini"],
            "fixed": ["code-quality:gone:old.py"],
            "still_open": ["external-facts:stale-constant:tool.py"],
            "not_rechecked": ["feature-completeness:claim:README.md"],
            "not_reraised": ["tests:thing:t.py"],
        }

    def test_since_groups_in_order_with_counts_and_notes(self):
        f, x = docs()
        f["diff"] = self.diff()
        x["since_notes"] = [
            {"key": "tests:thing:t.py", "note": "Severity went <b>med</b> to low."}
        ]
        page = build(f, x)
        body = section(page, "since")
        states = re.findall(r"<b>([^<]+):</b> <code>", body)
        self.assertEqual(
            states, ["New", "Fixed", "Still open", "Not re-checked", "Not re-raised"]
        )
        self.assertIn(
            '<a href="https://example.com/prev">the previous run</a>: 1 new, 1 fixed, 1 still open, 1 not re-checked, 1 not re-raised.',
            body,
        )
        self.assertIn(
            '<a href="#security-1">security-1</a>', body
        )  # a key in this run links
        self.assertIn(
            "Depth: quick run, `product` lens not launched", body
        )  # the area's reason
        self.assertIn("Severity went <b>med</b> to low.", body)  # an authored note wins
        self.assertIn("since", nav_ids(page))

    def test_since_with_a_null_diff_needs_an_intro_and_lists_nothing(self):
        f, x = docs()
        f["diff"] = None
        self.assertIn("intros.since: required", failures(f, x))
        x["intros"]["since"] = "The previous run could not be read."
        body = section(build(f, x), "since")
        self.assertIn("could not be read", body)
        self.assertNotIn("<li>", body)

    def test_since_is_deleted_without_a_diff(self):
        page = build(*docs())
        self.assertNotIn('id="since"', page)
        self.assertNotIn('href="#since"', page)

    def test_since_notes_need_a_diff_and_a_key_in_it(self):
        f, x = docs()
        x["since_notes"] = [{"key": "a:b:c", "note": "n"}]
        self.assertIn("findings.json has no `diff`", failures(f, x))
        f["diff"] = self.diff()
        self.assertIn("is not in `diff`", failures(f, x))

    def test_coverage_marks_and_reasons(self):
        page = build(*docs())
        cov = table(page, "Coverage per area")
        dash = render.DASH
        self.assertEqual(
            cells(cov, "Code quality")[1:], [render.CHECK, dash, dash, dash, dash, dash]
        )
        self.assertEqual(
            cells(cov, "Tech stack, dependencies and supply chain")[1:],
            [
                dash,
                dash,
                dash,
                dash,
                "yes",
                "Not applicable: no manifest, lockfile, workflow, container or IaC file",
            ],
        )
        self.assertEqual(
            cells(cov, "Performance")[-1],
            "benchmark: Depth: quick run, benchmark not run",
        )

    def test_lens_table_lists_each_launched_lens(self):
        lens = table(build(*docs()), "Coverage per lens")
        self.assertEqual(
            cells(lens, "code"), ["code", "read 6 of 6 files", "Small tier: everything"]
        )


class QuickDepth(unittest.TestCase):
    """A quick run's unlaunched lenses own no verdict (SKILL.md, Skipped areas)."""

    def give_verdict(self, area, verdict="ready"):
        f, x = docs()
        row = next(r for r in f["scorecard"]["areas"] if r["area"] == area)
        row.update(
            applies=True, verdict=verdict, not_assessed_reason=None, top_finding=None
        )
        return f, x

    def test_a_verdict_on_an_unlaunched_lens_area_is_refused_by_name(self):
        for area, lens, verdict in [
            ("feature-completeness", "product", "ready_with_fixes"),
            ("repo-hygiene", "product", "ready"),
            ("ops-release", "product", "not_ready"),
            ("accessibility", "design", "ready"),
        ]:
            with self.subTest(area):
                f, x = self.give_verdict(area, verdict)
                out = failures(f, x)
                self.assertIn(f"`{area}` belongs to the `{lens}` lens", out)
                self.assertIn(f"Depth: quick run, `{lens}` lens not launched", out)

    def test_every_offending_area_is_named_in_one_refusal(self):
        f, x = self.give_verdict("feature-completeness", "ready_with_fixes")
        row = next(r for r in f["scorecard"]["areas"] if r["area"] == "repo-hygiene")
        row.update(verdict="ready", not_assessed_reason=None)
        out = failures(f, x)
        self.assertIn("`feature-completeness`", out)
        self.assertIn("`repo-hygiene`", out)

    def test_the_depth_reason_renders(self):
        f, x = docs()
        row = next(r for r in f["scorecard"]["areas"] if r["area"] == "repo-hygiene")
        self.assertEqual(row["verdict"], "not_assessed")
        self.assertEqual(
            row["not_assessed_reason"], "Depth: quick run, `product` lens not launched"
        )
        build(f, x)

    def test_a_standard_run_is_unaffected(self):
        f, x = self.give_verdict("feature-completeness", "ready_with_fixes")
        for r in f["profile"]:
            if r["fact"] == "depth":
                r["value"] = "standard"
        build(f, x)


class OptionalSections(unittest.TestCase):
    def test_absent_sections_leave_neither_block_nor_nav_link(self):
        page = build(*docs())
        for ident in ("since", "measurements", "screens", "mockups", "research"):
            with self.subTest(ident):
                self.assertNotIn(f'id="{ident}"', page)
                self.assertNotIn(f'href="#{ident}"', page)

    def test_measurements_need_an_intro_and_set_wide_by_column_count(self):
        f, x = docs()
        x["tables"] += [
            {
                "section": "measurements",
                "caption": "Four",
                "head": list("abcd"),
                "rows": [list("wxyz")],
            },
            {
                "section": "measurements",
                "caption": "Five",
                "head": list("abcde"),
                "rows": [list("vwxyz")],
            },
        ]
        self.assertIn("intros.measurements: required", failures(f, x))
        x["intros"]["measurements"] = "Probe totals."
        page = build(f, x)
        self.assertIn("measurements", nav_ids(page))
        self.assertTrue(re.search(r"<table>\s*<caption>\s*Four", page))
        self.assertTrue(re.search(r'<table class="wide">\s*<caption>\s*Five', page))

    def test_research_and_checked_render_their_lists(self):
        f, x = docs()
        x["research"] = {
            "sources": [
                {
                    "topic": "Fees",
                    "summary": "Rates <b>rose</b>.",
                    "url": "https://example.com/r",
                    "title": "A & B",
                }
            ],
            "gaps": "No pricing page found.",
        }
        x["intros"]["research"] = "One source."
        page = build(f, x)
        body = section(page, "research")
        self.assertIn('<a href="https://example.com/r">A &amp; B</a>', body)
        self.assertIn("No pricing page found.", body)
        checked = section(page, "checked")
        self.assertIn("<h3>Verified</h3>", checked)
        self.assertNotIn(
            "<h3>Corrected</h3>", checked
        )  # an empty list goes with its heading

    def test_checked_section_goes_when_every_list_is_empty(self):
        f, x = docs()
        x["checked"] = {}
        self.assertNotIn('id="checked"', build(f, x))

    def test_screens_embed_the_file_as_a_data_uri(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "shot.png").write_bytes(PNG)
            f, x = docs()
            x["screens"] = [
                {
                    "path": "shot.png",
                    "alt": "Home <page>",
                    "caption": "The first screen.",
                }
            ]
            x["intros"]["screens"] = "One capture."
            page = build(f, x, base=Path(tmp))
        self.assertIn(
            'alt="Home &lt;page&gt;" src="data:image/png;base64,'
            + base64.b64encode(PNG).decode(),
            page,
        )

    def test_screens_faults(self):
        with tempfile.TemporaryDirectory() as tmp:
            for expected, mutate in {
                "cannot read the image file": lambda x: x["screens"][0].update(
                    path="gone.png"
                ),
                "is not a .jpg, .png or .webp": lambda x: x["screens"][0].update(
                    path="shot.gif"
                ),
                "intros.screens: required": lambda x: x["intros"].pop("screens"),
            }.items():
                with self.subTest(expected):
                    f, x = docs()
                    x["screens"] = [{"path": "shot.png", "alt": "a", "caption": "c"}]
                    x["intros"]["screens"] = "One capture."
                    mutate(x)
                    self.assertIn(expected, failures(f, x, base=Path(tmp)))

    def test_no_screens_requires_the_no_captures_note(self):
        f, x = docs()
        x["method_note"] = "Quick run. No mockups: no UI."
        self.assertIn("No captures", failures(f, x))

    def mockup(self, **kw):
        return {
            "title": "Settings",
            "context": "Rewritten copy",
            "width": 936,
            "html": '<div class="bw" style="--w: 880px; --h: 480px">Label <b style="color: var(--mk-green)">Ready</b></div>',
            "notes": ["Says what it does."],
            **kw,
        }

    def test_mockup_replaces_the_frame_sample_and_fills_notes(self):
        f, x = docs()
        add_design_finding(f, x)
        x["mockups"] = [self.mockup()]
        x["intros"]["mockups"] = "One screen."
        page = build(f, x)
        body = section(page, "mockups")
        self.assertIn('<div class="scaler" data-w="936">', body)
        self.assertIn(
            '<div class="mk"><div class="bw" style="--w: 880px; --h: 480px">Label', body
        )
        self.assertNotIn("example.com/settings", body)  # the sample is gone
        self.assertIn("<li>Says what it does.</li>", body)

    def test_mockup_faults(self):
        def too_many(f, x):
            add_design_finding(f, x)
            x["mockups"] = [self.mockup() for _ in range(4)]

        def no_design_finding(f, x):
            x["mockups"] = [self.mockup()]

        def script(f, x):
            add_design_finding(f, x)
            x["mockups"] = [self.mockup(html="<script>alert(1)</script>")]

        def literal_colour(f, x):
            add_design_finding(f, x)
            x["mockups"] = [self.mockup(html='<div style="color: #fff">x</div>')]

        def missing_intro(f, x):
            add_design_finding(f, x)
            x["mockups"] = [self.mockup()]
            x["intros"].pop("mockups", None)

        cases = {
            "at most 3": too_many,
            "High or Blocker": no_design_finding,
            "a <script> tag": script,
            "a literal colour": literal_colour,
            "intros.mockups: required": missing_intro,
        }
        for expected, mutate in cases.items():
            with self.subTest(expected):
                f, x = docs()
                x["intros"]["mockups"] = "Screens."
                mutate(f, x)
                self.assertIn(expected, failures(f, x))

    def test_no_mockups_needs_a_stated_reason(self):
        f, x = docs()
        x["method_note"] = "Quick run. No captures: no UI."
        self.assertIn("No mockups", failures(f, x))


class Escaping(unittest.TestCase):
    def test_prose_is_trusted_markup_with_unsafe_parts_refused(self):
        cases = [
            ("a <script> tag", "<script>alert(1)</script>"),
            ("an event-handler attribute", '<a href="#x" onclick="go()">x</a>'),
            ("a javascript: URL", '<a href="javascript:go()">x</a>'),
            ("a javascript: URL", '<a href="&#106;avascript&colon;go()">x</a>'),
            ("a data: URL", '<a href="data:text/html,x">x</a>'),
            ("a <style> tag", "<style>p{color:red}</style>"),
        ]
        for expected, markup in cases:
            with self.subTest(markup):
                f, x = docs()
                x["lede"] = markup
                self.assertIn(expected, failures(f, x))

    def test_known_bypasses_are_refused(self):
        cases = [
            ("an event-handler attribute", "<img/onerror=a() src=x>"),
            ("an event-handler attribute", "<span onmouseover=go()>x</span>"),
            ("an event-handler attribute", '<span ONCLICK="go()">x</span>'),
            ("a javascript: URL", '<a href="java&#9;script:x">x</a>'),
            ("a javascript: URL", '<a href="java\nscript:x">x</a>'),
            ("a javascript: URL", '<a href=" \x01javascript:x">x</a>'),
            ("a vbscript: URL", '<a href="vbscript:x">x</a>'),
            ("a data: URL", '<a href="data:text/html,x">x</a>'),
            ("a protocol-relative URL", '<a href="//evil.example/x">x</a>'),
            ("a protocol-relative URL", '<a href="\\\\evil.example/x">x</a>'),
            ("a protocol-relative URL", '<a href="/\\evil.example/x">x</a>'),
            ("a protocol-relative URL", '<a href="\\/evil.example/x">x</a>'),
            (
                "an image function",
                "<span style=\"background:image-set('https://e.example/x.png' 1x)\">x</span>",
            ),
            (
                "an image function",
                "<span style=\"background:-webkit-image-set('https://e.example/x.png' 1x)\">x</span>",
            ),
            (
                "an image function",
                "<span style=\"background:cross-fade('https://e.example/a.png', 'b.png', 50%)\">x</span>",
            ),
            ("a srcset", '<span srcset="data:image/png;base64,AA 1x">x</span>'),
            (
                "url(), a backslash",
                '<span style="background:url(data:image/png;base64,AA)">x</span>',
            ),
            (
                "url(), a backslash",
                '<span style="background:url(https://x.example/a.png)">x</span>',
            ),
            ("url(), a backslash", '<span style="col\\6fr: x">x</span>'),
            ("a <base> tag", '<base href="https://evil.example/">'),
            ("a <form> tag", '<form action="https://evil.example/"><input></form>'),
            ("a <iframe> tag", '<iframe src="x"></iframe>'),
            ("a <img> tag", '<img src="https://x.example/a.png">'),
            ("tag is not allowed", "<scr<script>ipt>x</script>"),
            ("a <script> tag", "<SCRIPT>x</SCRIPT>"),
            ("the `formaction` attribute", '<span formaction="x">x</span>'),
            ("the `src` attribute", '<span src="https://x.example/a.png">x</span>'),
            ("the `target` attribute", '<a href="#x" target="_blank">x</a>'),
            ("an HTML comment", "<!-- hidden -->"),
            ("an unterminated tag", "text <scr"),
        ]
        for expected, markup in cases:
            with self.subTest(markup):
                problems = render.markup_problems(markup)
                self.assertTrue(any(expected in p for p in problems), problems)

    def test_allowed_links_pass(self):
        for href in (
            "#security-1",
            "run-log.md",
            "https://example.com/a?b=1",
            "http://example.com",
            "mailto:a@example.com",
        ):
            with self.subTest(href):
                self.assertEqual(render.markup_problems(f'<a href="{href}">x</a>'), [])

    def test_sample_prose_and_every_mockup_frame_pass(self):
        strings = []

        def walk(node):
            if isinstance(node, str):
                strings.append(node)
            elif isinstance(node, list):
                for n in node:
                    walk(n)
            elif isinstance(node, dict):
                for n in node.values():
                    walk(n)

        walk(SAMPLE_X)
        self.assertTrue(strings)
        for text in strings:
            with self.subTest(text[:40]):
                self.assertEqual(render.markup_problems(text), [])
        frames = 0
        for source in (HERE / "snippets.html", HERE / "template.html"):
            text = source.read_text()
            text = text.replace("{{MOCKUP_HTML}}", "")  # not a frame
            for m in re.finditer(r'<div class="mk">', text):
                end = render._close_of_div(text, m.end())
                inner = re.sub(r"<!--.*?-->", "", text[m.end() : end], flags=re.DOTALL)
                frames += 1
                with self.subTest(f"{source.name} frame {frames}"):
                    self.assertEqual(render.markup_problems(inner), [])
        self.assertGreaterEqual(
            frames, 4
        )  # browser (template), window, phone, terminal

    def test_every_literal_colour_form_is_refused(self):
        cases = [
            '<span style="background: rgb(1, 2, 3)">x</span>',
            '<span style="color:#fff">x</span>',
            '<span style="background:red">x</span>',
            '<span style="border: 1px solid Tomato">x</span>',
            '<span style="box-shadow: 0 0 2px var(--rule), 0 0 4px black">x</span>',
            '<svg><rect fill="#ff0000"></rect></svg>',
            '<svg><rect stroke="blue"></rect></svg>',
            "<svg><rect fill=red /></svg>",
            "<span style=color:red>x</span>",
            '<span style="color: var(--ink, red)">x</span>',
            '<span style="color: var(--ink, var(--x, #f00))">x</span>',
            '<svg><rect color="red"></rect></svg>',
        ]
        for markup in cases:
            with self.subTest(markup):
                f, x = docs()
                x["lede"] = markup
                self.assertIn("a literal colour", failures(f, x))

    def test_token_and_keyword_colours_pass(self):
        cases = [
            '<span style="color: var(--hi); font-family: Georgia, serif">x</span>',
            '<span style="background: var(--hi-bg); border: 1px solid var(--rule)">x</span>',
            '<svg><rect fill="var(--accent)" stroke="currentColor"></rect><path fill="none"></path></svg>',
            '<span style="color: inherit; background: transparent">x</span>',
        ]
        for markup in cases:
            with self.subTest(markup):
                f, x = docs()
                x["lede"] = markup
                self.assertIn(markup, build(f, x))

    def test_inline_html_and_token_colours_pass(self):
        f, x = docs()
        x["lede"] = (
            '<b>Bold</b> <span style="color: var(--hi)">risk</span> <a href="#security-1">link</a>'
        )
        self.assertIn('<span style="color: var(--hi)">risk</span>', build(f, x))

    def test_plain_text_fields_are_escaped(self):
        f, x = docs()
        x["project"] = "A & <B>"
        page = build(f, x)
        self.assertIn("<title>A &amp; &lt;B&gt; Audit</title>", page)

    def test_double_braces_in_data_are_escaped_not_a_failure(self):
        f, x = docs()
        f["findings"][0]["title"] = "{{PROJECT}} leaks"
        x["lede"] = "Lede with {{OVERALL_TEXT}}"
        page = build(f, x)
        self.assertIn("&#123;&#123;PROJECT}} leaks", page)
        self.assertIn("Lede with &#123;&#123;OVERALL_TEXT}}", page)
        self.assertEqual(render.check_output(page), [])


class Output(unittest.TestCase):
    def test_sample_page_is_whole(self):
        page = build(*docs())
        self.assertEqual(render.check_output(page), [])
        self.assertNotIn("{{", page)
        self.assertNotRegex(page, r"<!--\s*/?repeat")
        self.assertNotIn("REPORT TEMPLATE", page)
        self.assertEqual(len(h2_ids(page)), len(set(h2_ids(page))))
        self.assertTrue(
            page.rstrip().endswith("</script>")
        )  # the theme script survives

    def test_two_renders_are_byte_identical(self):
        self.assertEqual(build(*docs()), build(*docs()))

    def test_check_output_names_each_fault(self):
        cases = {
            "unfilled tokens left in the page: {{X_Y}}": "<p>{{X_Y}}</p>",
            "a repeat marker is left": "<!-- repeat: a --><p></p>",
            "unbalanced tags": "<div><p></div>",
            "unclosed tags: div": "<div><p></p>",
            "duplicate id `a`": '<p id="a"></p><p id="a"></p>',
            "dangling link #zz": '<a href="#zz">x</a>',
        }
        for expected, markup in cases.items():
            with self.subTest(expected):
                self.assertTrue(
                    any(expected in e for e in render.check_output(markup)), markup
                )
        self.assertEqual(
            render.check_output('<p id="a"></p><a href="#a">x</a><br><img src="x">'), []
        )

    def test_an_unfilled_token_in_the_template_fails_the_build(self):
        bad = TEMPLATE.replace("<h1>", "<h1>{{BOGUS}}", 1)
        self.assertIn(
            "unfilled tokens left in the page: {{BOGUS}}",
            failures(*docs(), template=bad),
        )

    def test_a_malformed_template_fails_with_a_message(self):
        for expected, bad in {
            "is not closed": TEMPLATE.replace("<!-- /repeat -->", "", 1),
            "has no opener": TEMPLATE.replace("<!-- repeat: nav-link -->", "", 1),
        }.items():
            with self.subTest(expected):
                self.assertIn(expected, failures(*docs(), template=bad))

    def test_template_inventory_matches_what_render_fills(self):
        found = render.template_inventory(TEMPLATE)
        self.assertEqual(found["tokens"], set(render.TOKENS))
        self.assertEqual(found["repeats"], set(render.REPEATS))
        self.assertEqual(found["sections"], set(render.SECTION_IDS))

    def test_area_titles_are_rubrics(self):
        rubric = (HERE / "rubric.md").read_text()
        table_rows = re.findall(
            r"^\|\s*([^|]+?)\s*\|\s*`([a-z-]+)`\s*\|", rubric, re.MULTILINE
        )
        self.assertEqual({a: t for t, a in table_rows}, render.AREAS)
        self.assertEqual([a for _, a in table_rows], findings_check.AREAS)


class Inputs(unittest.TestCase):
    def test_sample_extra_is_schema_valid(self):
        self.assertEqual(render.schema_errors(SAMPLE_F, SAMPLE_X), [])

    def test_schema_faults_are_reported_without_building(self):
        cases = {
            "page-extra.json $: missing required 'plan'": lambda f, x: x.pop("plan"),
            "page-extra.json $: unexpected property 'extra_thing'": lambda f, x: (
                x.update(extra_thing=1)
            ),
            "page-extra.json $.plan.now.items[0].effort": lambda f, x: x["plan"]["now"][
                "items"
            ][0].update(effort="XL"),
            "page-extra.json $.intros.plan": lambda f, x: x["intros"].update(plan="  "),
            "findings.json $: missing required 'scorecard'": lambda f, x: f.pop(
                "scorecard"
            ),
        }
        for expected, mutate in cases.items():
            with self.subTest(expected):
                f, x = docs()
                mutate(f, x)
                self.assertTrue(
                    any(e.startswith(expected) for e in render.schema_errors(f, x))
                )

    def test_messages_are_short(self):
        f, x = docs()
        x["lede"] = 5
        f["findings"][0]["severity"] = "x" * 500
        self.assertTrue(
            all(len(e) <= render.MAX_MESSAGE for e in render.schema_errors(f, x))
        )

    def test_table_rows_must_match_the_head(self):
        f, x = docs()
        x["tables"][0]["rows"][0].pop()
        self.assertIn("a row has 4 cells, the head 5", failures(f, x))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.findings = self.dir / "findings.json"
        self.extra = self.dir / "page-extra.json"
        self.out = self.dir / "page.html"
        self.findings.write_text(json.dumps(SAMPLE_F))
        self.extra.write_text(json.dumps(SAMPLE_X))

    def run_main(self, *args):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            try:
                code = render.main([str(a) for a in args])
            except SystemExit as exc:
                code = exc.code
        return code, err.getvalue()

    def test_writes_the_page_and_exits_0(self):
        code, _ = self.run_main(self.findings, self.extra, "-o", self.out)
        self.assertEqual(code, 0)
        self.assertEqual(render.check_output(self.out.read_text()), [])

    def test_check_writes_nothing(self):
        code, _ = self.run_main("--check", self.findings, self.extra)
        self.assertEqual(code, 0)
        self.assertFalse(self.out.exists())

    def test_invalid_input_exits_1_with_messages_and_writes_nothing(self):
        bad = copy.deepcopy(SAMPLE_X)
        del bad["plan"]
        self.extra.write_text(json.dumps(bad))
        code, err = self.run_main(self.findings, self.extra, "-o", self.out)
        self.assertEqual(code, 1)
        self.assertIn("render: page-extra.json $: missing required 'plan'", err)
        self.assertFalse(self.out.exists())

    def test_unreadable_input_exits_2(self):
        self.extra.write_text("{not json")
        bad_utf8 = self.dir / "bad.json"
        bad_utf8.write_bytes(b"\xff\xfe")
        cases = {
            "not JSON": (self.findings, self.extra),
            "not UTF-8": (bad_utf8, self.extra),
            "cannot read": (self.dir / "missing.json", self.extra),
        }
        for expected, (findings, extra) in cases.items():
            with self.subTest(expected):
                code, err = self.run_main(findings, extra, "-o", self.out)
                self.assertEqual(code, 2)
                self.assertIn(expected, err)

    def test_usage_error_exits_2(self):
        code, err = self.run_main(self.findings, self.extra)
        self.assertEqual(code, 2)
        self.assertIn("-o is required", err)

    def test_runs_isolated_from_another_folder(self):
        done = subprocess.run(
            [
                sys.executable,
                "-I",
                str(HERE / "render.py"),
                str(self.findings),
                str(self.extra),
                "-o",
                str(self.out),
            ],
            cwd=self.dir,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(self.out.exists())

    def test_template_option_swaps_the_markup(self):
        custom = self.dir / "t.html"
        custom.write_text(TEMPLATE.replace("<h1>", '<h1 class="custom">', 1))
        code, _ = self.run_main(
            self.findings, self.extra, "-o", self.out, "--template", custom
        )
        self.assertEqual(code, 0)
        self.assertIn('<h1 class="custom">', self.out.read_text())


if __name__ == "__main__":
    unittest.main()
