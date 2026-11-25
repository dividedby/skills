"""Self-tests for the repo-audit evals: fixture generation, the findings.json
schema and expectation checks, the cross-run diff, and the runner's pure parts.

Needs only the standard library and git. No claude call is made.

Run: python3 -B skills/engineering/repo-audit/evals/evals.test.py
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import findings_check as fc
import fixtures
import run_evals

SKILL_DIR = HERE.parent
REPO_ROOT = HERE.parents[3]
SCHEMA = json.loads((HERE / "findings.schema.json").read_text())
EXPECTATIONS = json.loads((HERE / "expectations.json").read_text())
SAMPLE = json.loads((HERE / "sample-findings.json").read_text())

# Assembled here so this file holds no literal a secret scanner would flag.
SECRET_RE = re.compile("g" + "hp_[0-9A-Za-z]{36}")
LARGE = "large-workspace"


def tracked(repo: Path) -> list[str]:
    out = run_evals._git_out(repo, "ls-files")
    return [line for line in out.splitlines() if line]


def head(repo: Path) -> tuple[str, ...]:
    out = run_evals._git_out(repo, "rev-parse", "HEAD", "HEAD^{tree}")
    return tuple(out.split())


class FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        cls.first = fixtures.generate(root / "first")
        # The second build skips the Large fixture to keep the self-test fast;
        # its determinism is checked on the fast-import stream instead.
        cls.second = fixtures.generate(
            root / "second", only=[n for n in fixtures.FIXTURES if n != LARGE]
        )
        cls.root = root

    def test_generation_is_idempotent(self):
        for name in self.second:
            with self.subTest(name):
                self.assertEqual(head(self.first[name]), head(self.second[name]))
        build = fixtures._BUILDERS[LARGE]
        self.assertEqual(fixtures._stream(build()), fixtures._stream(build()))

    def test_regenerating_over_an_existing_folder_gives_the_same_commits(self):
        again = fixtures.generate(
            self.root / "first", only=["single-script", "docs-only"]
        )
        for name in again:
            self.assertEqual(head(again[name]), head(self.second[name]))

    def test_each_fixture_has_a_small_history_and_no_remote(self):
        for name, repo in self.first.items():
            with self.subTest(name):
                count = int(run_evals._git_out(repo, "rev-list", "--count", "HEAD"))
                self.assertTrue(3 <= count <= 5, count)
                self.assertNotIn("[remote", (repo / ".git" / "config").read_text())

    def test_refuses_a_non_empty_folder_it_did_not_create(self):
        stray = self.root / "stray"
        stray.mkdir()
        (stray / "keep.txt").write_text("mine")
        with self.assertRaises(fixtures.FixtureError):
            fixtures.generate(stray)
        self.assertTrue((stray / "keep.txt").exists())

    def test_refuses_a_git_repo_as_the_output_folder(self):
        with self.assertRaises(fixtures.FixtureError):
            fixtures.generate(self.first["single-script"])

    def test_planted_items_exist(self):
        for name, repo in self.first.items():
            for planted in EXPECTATIONS["fixtures"][name]["planted"]:
                with self.subTest(name=name, planted=planted["id"]):
                    self.assert_planted(repo, planted)

    def assert_planted(self, repo: Path, planted: dict) -> None:
        paths = planted["paths"]
        for rel in paths:
            self.assertTrue((repo / rel).is_file(), f"{rel} missing")
        if planted["id"] == "secret":
            self.assertRegex((repo / paths[0]).read_text(), SECRET_RE)
        elif planted["id"] == "stale-constant":
            self.assertIn("2019-12-31", (repo / paths[0]).read_text())
        elif planted["id"] == "duplicate-file":
            self.assertEqual(
                (repo / paths[0]).read_bytes(), (repo / paths[1]).read_bytes()
            )
        elif planted["id"] == "doc-command-missing":
            self.assert_command_documented_but_absent(repo, paths[0])
        elif planted["id"] == "stale-recorded-fixture":
            self.assertIn("recorded_at", (repo / paths[0]).read_text())
            for name in tracked(repo):
                self.assertNotIn("schema", (repo / name).read_text().lower(), name)
        elif planted["id"] == "viewport-overflow":
            css = (repo / "styles.css").read_text()
            self.assertRegex(css, r"\.hero\s*\{[^}]*width:\s*480px")
        elif planted["id"] == "low-contrast":
            self.assertIn("#b5b5b5", (repo / "styles.css").read_text())

    def assert_command_documented_but_absent(self, repo: Path, readme: str) -> None:
        text = (repo / readme).read_text()
        names = set(tracked(repo))
        if "make report" in text:
            self.assertNotIn("Makefile", names)
        elif "make synth" in text:
            self.assertNotRegex((repo / "Makefile").read_text(), r"(?m)^synth:")
        elif "pnpm run report" in text:
            for name in names:
                if name.endswith("package.json"):
                    self.assertNotIn('"report"', (repo / name).read_text(), name)
        elif "./bin/export" in text:
            self.assertFalse(any(n.startswith("bin/") for n in names))
        elif "npm run build" in text:
            self.assertNotIn("package.json", names)
        else:
            self.fail(f"{readme} documents none of the expected commands")

    def test_unchanged_check_detects_edits_and_additions(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "single-script"
            shutil.copytree(self.first["single-script"], repo)
            self.assertEqual(run_evals.snapshot_repo(repo)["status"], "")
            before = run_evals.snapshot_repo(repo)
            self.assertEqual(
                run_evals.compare_snapshots(before, run_evals.snapshot_repo(repo)), []
            )
            (repo / "README.md").write_text("changed\n")
            (repo / "new.txt").write_text("x\n")
            changes = run_evals.compare_snapshots(before, run_evals.snapshot_repo(repo))
            self.assertIn("README.md: modified", changes)
            self.assertIn("new.txt: added", changes)
            self.assertIn("git status changed", changes)

    def test_secret_literal_is_in_no_committed_file(self):
        for path in HERE.iterdir():
            if path.is_file():
                with self.subTest(path.name):
                    self.assertIsNone(SECRET_RE.search(path.read_text()))

    def test_no_git_repo_in_the_evals_folder(self):
        for _root, dirs, _files in os.walk(HERE):
            self.assertNotIn(".git", dirs)

    def test_planted_paths_exist_in_the_fixtures(self):
        self.assertEqual(sorted(EXPECTATIONS["fixtures"]), sorted(fixtures.FIXTURES))
        for name, exp in EXPECTATIONS["fixtures"].items():
            for planted in exp["planted"]:
                for rel in planted["paths"]:
                    self.assertTrue(
                        (self.first[name] / rel).is_file(), f"{name}: {rel}"
                    )

    def test_workspace_is_medium_with_three_packages(self):
        repo = self.first["workspace"]
        lines = sum(
            len((repo / rel).read_text().splitlines())
            for rel in tracked(repo)
            if rel.endswith(".js")
        )
        self.assertTrue(2000 < lines < 50000, lines)
        manifests = [
            n for n in tracked(repo) if re.fullmatch(r"packages/[^/]+/package\.json", n)
        ]
        self.assertEqual(len(manifests), 3)

    def test_large_workspace_is_large_and_its_planted_files_are_where_a_sample_looks(
        self,
    ):
        repo = self.first[LARGE]
        exp = EXPECTATIONS["fixtures"][LARGE]
        names = tracked(repo)
        lines = sum(
            len((repo / rel).read_text().splitlines())
            for rel in names
            if rel.endswith(".js")
        )
        self.assertGreater(lines, 100000)
        manifests = [
            n for n in names if re.fullmatch(r"packages/[^/]+/package\.json", n)
        ]
        self.assertGreaterEqual(len(manifests), exp["profile"]["packages_min"])
        # Nothing the tier rule's exclusions (types.md) would drop from the count.
        excluded = (
            r"(^|/)(vendor|dist|node_modules|fixtures?|__snapshots__)/|\.min\.|\.lock$"
        )
        self.assertEqual([n for n in names if re.search(excluded, n)], [])
        planted = {p["id"]: p["paths"] for p in exp["planted"]}
        self.assertRegex(
            planted["stale-constant"][0], r"^packages/[^/]+/src/index\.js$"
        )
        largest = sorted(names, key=lambda n: (repo / n).stat().st_size, reverse=True)
        self.assertEqual(sorted(largest[:2]), sorted(planted["duplicate-file"]))

    def test_unknown_type_matches_no_type_detection(self):
        # types.md Detect lines: userscript, library manifest, CLI, native app, server,
        # infra, local web app, hosted site, docs/config/data.
        names = tracked(self.first["unknown-type"])
        forbidden = [
            r"\.user\.js$",
            r"(^|/)(package\.json|pyproject\.toml|Cargo\.toml|go\.mod|go\.work|Package\.swift|pnpm-workspace\.yaml)$",
            r"(^|/)(Dockerfile|compose\.ya?ml)$",
            r"\.(tf|tofu|xcodeproj|html|service)$",
            r"^(bin|cmd|ops|apps|packages)/",
            r"^\.github/workflows/",
        ]
        for pattern in forbidden:
            self.assertEqual([n for n in names if re.search(pattern, n)], [], pattern)
        self.assertTrue(any(n.endswith(".v") for n in names), "needs tracked source")


class SchemaTests(unittest.TestCase):
    def mutated(self, change) -> list[str]:
        doc = copy.deepcopy(SAMPLE)
        change(doc)
        return fc.validate(doc, SCHEMA)

    def test_sample_is_valid(self):
        self.assertEqual(fc.validate(SAMPLE, SCHEMA), [])

    def test_go_public_null_and_object_are_accepted(self):
        def object_form(d):
            d["go_public"] = {
                "verdict": "ready_after_cleanup",
                "minutes_saved_per_month": None,
                "basis": None,
                "basis_reason": "Needs X: billing scope",
                "items": [
                    {"row": "secrets", "result": "found", "needs_history_rewrite": True}
                ],
            }

        self.assertEqual(self.mutated(object_form), [])
        self.assertIsNone(SAMPLE["go_public"])

    def test_invalid_documents_are_rejected(self):
        cases = {
            "missing key": lambda d: d["findings"][0].pop("key"),
            "bad severity": lambda d: d["findings"][0].update(severity="critical"),
            "bad area id": lambda d: d["findings"][0].update(area="docs"),
            "malformed key": lambda d: d["findings"][0].update(key="no-colons"),
            "bad overall": lambda d: d["scorecard"].update(overall="fine"),
            "wrong type": lambda d: d["scorecard"]["areas"][0].update(applies="yes"),
            "extra top-level key": lambda d: d.update(extra=1),
            "bad effort": lambda d: d["findings"][0].update(effort="XL"),
            "missing section": lambda d: d.pop("coverage"),
            "bad diff": lambda d: d.update(diff={"previous_url": "u"}),
        }
        for label, change in cases.items():
            with self.subTest(label):
                self.assertTrue(self.mutated(change), label)

    def test_diff_field_is_optional_and_nullable(self):
        self.assertEqual(self.mutated(lambda d: d.update(diff=None)), [])
        full = {
            "previous_url": "u",
            "new": [],
            "fixed": [],
            "still_open": [],
            "not_rechecked": [],
            "not_reraised": [],
        }
        self.assertEqual(self.mutated(lambda d: d.update(diff=full)), [])

    def test_schema_enums_match_rubric_area_table(self):
        rubric = (SKILL_DIR / "rubric.md").read_text()
        rows = re.findall(
            r"^\| [^|]+ \| `([a-z-]+)` +\| `([a-z]+)` +\|", rubric, re.MULTILINE
        )
        self.assertEqual(len(rows), 16)
        self.assertEqual([a for a, _ in rows], fc.AREAS)
        self.assertEqual(dict(rows), fc.AREA_OWNER)
        self.assertEqual(SCHEMA["$defs"]["area"]["enum"], fc.AREAS)


class ExpectationTests(unittest.TestCase):
    EXP = EXPECTATIONS["fixtures"]["single-script"]

    def failed(self, doc: dict, depth: str = "quick") -> list[str]:
        return [r.name for r in fc.check_expectations(doc, self.EXP, depth) if not r.ok]

    def edit(self, change) -> dict:
        doc = copy.deepcopy(SAMPLE)
        change(doc)
        return doc

    def finding(self, doc: dict, fid: str) -> dict:
        return next(f for f in doc["findings"] if f["id"] == fid)

    def card(self, doc: dict, area: str) -> dict:
        return next(a for a in doc["scorecard"]["areas"] if a["area"] == area)

    def test_sample_passes_at_quick(self):
        self.assertEqual(self.failed(SAMPLE), [])

    def test_wrong_path_area_or_check_fails_that_planted_finding(self):
        for label, key in {
            "path": "security:secret-scan:other.ini",
            "area": "privacy:secret-scan:config.ini",
            "check": "security:naming:config.ini",
        }.items():
            doc = self.edit(
                lambda d, k=key: self.finding(d, "security-1").update(key=k)
            )
            with self.subTest(label):
                self.assertEqual(self.failed(doc), ["planted: secret"])

    def test_failure_names_the_nearest_finding(self):
        doc = self.edit(
            lambda d: self.finding(d, "security-1").update(
                key="security:naming:config.ini"
            )
        )
        detail = next(
            r.detail
            for r in fc.check_expectations(doc, self.EXP, "quick")
            if r.name == "planted: secret"
        )
        self.assertIn("security:naming:config.ini", detail)

    def test_key_paths_are_matched_without_a_leading_dot_slash(self):
        doc = self.edit(
            lambda d: self.finding(d, "security-1").update(
                key="security:secret-scan:./config.ini"
            )
        )
        self.assertEqual(self.failed(doc), [])

    def test_profile_and_area_expectations(self):
        doc = self.edit(
            lambda d: d["profile"].remove(
                next(r for r in d["profile"] if r["fact"] == "tier")
            )
        )
        self.assertEqual(self.failed(doc), ["tier"])
        doc = self.edit(
            lambda d: next(r for r in d["profile"] if r["fact"] == "type").update(
                value="CLI (fallback profile)"
            )
        )
        self.assertEqual(self.failed(doc), ["type"])
        doc = self.edit(lambda d: self.card(d, "code-quality").update(applies=False))
        self.assertIn("applicable areas", self.failed(doc))

    def test_silent_gaps_fail(self):
        cases = {
            "missing scorecard area": lambda d: d["scorecard"]["areas"].pop(),
            "missing coverage row": lambda d: d["coverage"].pop(),
            "not assessed with no reason": lambda d: self.card(d, "tech-stack").update(
                not_assessed_reason=None
            ),
            "n/a area with a verdict": lambda d: self.card(d, "tech-stack").update(
                verdict="ready"
            ),
        }
        for label, change in cases.items():
            with self.subTest(label):
                self.assertIn("no silent gap", self.failed(self.edit(change)))

    def test_quick_requires_a_depth_reason_for_unlaunched_lenses(self):
        doc = self.edit(
            lambda d: self.card(d, "repo-hygiene").update(
                not_assessed_reason="Needs X: a remote"
            )
        )
        self.assertIn("quick depth gaps", self.failed(doc))
        doc = self.edit(
            lambda d: self.card(d, "repo-hygiene").update(
                verdict="ready", not_assessed_reason=None
            )
        )
        self.assertIn("quick depth gaps", self.failed(doc))

    def test_standard_depth_expects_the_product_finding(self):
        failed = self.failed(SAMPLE, "standard")
        self.assertEqual(failed, ["planted: doc-command-missing"])
        doc = self.edit(
            lambda d: d["findings"].append(
                {
                    **self.finding(d, "code-quality-1"),
                    "id": "feature-completeness-1",
                    "key": "feature-completeness:doc-command-missing:README.md",
                    "area": "feature-completeness",
                }
            )
        )
        self.assertEqual(self.failed(doc, "standard"), [])

    def test_malformed_document_fails_without_raising(self):
        self.assertEqual(self.failed({}, "quick")[:1], ["type"])
        self.assertFalse(fc.check_expectations([], self.EXP, "quick")[0].ok)


# The sample's findings, re-keyed to the large fixture's planted paths.
LARGE_KEYS = {
    "security-1": "security:secret-scan:packages/api/src/config.js",
    "external-facts-1": "external-facts:stale-constant:packages/billing/src/index.js",
    "code-quality-1": "code-quality:duplicate-file:packages/cli/src/format.js",
    # Not planted in the large fixture; re-keyed so the sample stays one document.
    "tests-1": "tests:stale-recorded-fixture:packages/api/test/recorded.json",
}


class LargeExpectationTests(unittest.TestCase):
    """The Large-tier expectations, checked against a synthetic sampled run."""

    EXP = EXPECTATIONS["fixtures"][LARGE]

    @classmethod
    def large_sample(cls) -> dict:
        doc = copy.deepcopy(SAMPLE)
        fact = {r["fact"]: r for r in doc["profile"]}
        fact["type"].update(
            value="Monorepo (pnpm workspace)", source="pnpm-workspace.yaml"
        )
        fact["tier"].update(value="Large", source="git ls-files | wc -l: 113k lines")
        doc["lens_coverage"] = [
            {
                "lens": lens,
                "read": "read 60 of 618 files",
                "chosen_by": "Large tier: entry points, 20 largest, top 20 by churn, 20 random",
            }
            for lens in ("code", "architecture")
        ]
        for finding in doc["findings"]:
            finding["key"] = LARGE_KEYS[finding["id"]]
        for card in doc["scorecard"]["areas"]:
            want = cls.EXP["areas"][card["area"]]
            if want is not None:
                card["applies"] = want
        tech = next(a for a in doc["scorecard"]["areas"] if a["area"] == "tech-stack")
        tech.update(verdict="ready", not_assessed_reason=None)
        doc["scorecard"]["packages"] = [
            {
                "package": f"@ledger/{pkg}",
                "type": "library",
                "verdict": "ready",
                "not_assessed_reason": None,
                "top_finding": None,
            }
            for pkg in ("core", "utils", "cli", "api", "billing", "store")
        ]
        return doc

    def failed(self, doc: dict) -> list[str]:
        return [
            r.name for r in fc.check_expectations(doc, self.EXP, "quick") if not r.ok
        ]

    def test_the_synthetic_sample_is_valid_and_passes_at_quick(self):
        doc = self.large_sample()
        self.assertEqual(fc.validate(doc, SCHEMA), [])
        self.assertEqual(self.failed(doc), [])

    def test_a_lens_that_does_not_state_its_sample_fails_lens_coverage(self):
        unsampled = {"read": "read everything", "chosen_by": "every file"}
        cases = {
            "one lens reads everything": lambda d: d["lens_coverage"][1].update(
                unsampled
            ),
            "no lens_coverage rows": lambda d: d.update(lens_coverage=[]),
            "no lens_coverage field": lambda d: d.pop("lens_coverage"),
        }
        for label, change in cases.items():
            doc = self.large_sample()
            change(doc)
            with self.subTest(label):
                self.assertEqual(self.failed(doc), ["lens coverage"])

    def test_each_sampling_rule_the_brief_allows_passes_and_the_run_that_missed_it_fails(
        self,
    ):
        for chosen_by, ok in [
            ("entry points", True),
            ("the largest files", True),
            ("churn hotspots", True),
            ("random, seed 7", True),
            ("full read: all of its scope", True),
            ("every doc and manifest; module files only via billing index.js", False),
        ]:
            doc = self.large_sample()
            doc["lens_coverage"][1].update(read="read 12 files", chosen_by=chosen_by)
            with self.subTest(chosen_by):
                self.assertEqual(self.failed(doc), [] if ok else ["lens coverage"])

    def test_the_failure_names_the_lens_that_did_not_sample(self):
        doc = self.large_sample()
        doc["lens_coverage"][1].update(read="read everything", chosen_by="every file")
        detail = next(
            r.detail
            for r in fc.check_expectations(doc, self.EXP, "quick")
            if r.name == "lens coverage"
        )
        self.assertIn("architecture", detail)
        self.assertNotIn("code,", detail)

    def test_a_medium_tier_or_too_few_packages_fails(self):
        doc = self.large_sample()
        next(r for r in doc["profile"] if r["fact"] == "tier")["value"] = "Medium"
        self.assertEqual(self.failed(doc), ["tier"])
        doc = self.large_sample()
        doc["scorecard"]["packages"].pop()
        self.assertEqual(self.failed(doc), ["packages"])

    def test_small_fixtures_do_not_expect_lens_coverage_to_sample(self):
        results = fc.check_expectations(
            SAMPLE, EXPECTATIONS["fixtures"]["single-script"], "quick"
        )
        self.assertNotIn("lens coverage", [r.name for r in results])


class DiffTests(unittest.TestCase):
    @staticmethod
    def run_doc(keys: list[str], not_assessed: tuple[str, ...] = ()) -> dict:
        areas = [
            {
                "area": a,
                "applies": True,
                "verdict": "not_assessed" if a in not_assessed else "ready",
                "not_assessed_reason": "Depth: quick run"
                if a in not_assessed
                else None,
                "top_finding": None,
            }
            for a in fc.AREAS
        ]
        findings = [{"key": k} for k in keys]
        return {"findings": findings, "scorecard": {"areas": areas}}

    def test_new_fixed_and_still_open(self):
        prev = self.run_doc(
            ["security:secret-scan:a", "tests:no-test:b", "privacy:log:c"]
        )
        cur = self.run_doc(["security:secret-scan:a", "usability:dead-end:d"])
        self.assertEqual(
            fc.diff_runs(prev, cur, changed=["b", "d/x.py"]),
            {
                "new": ["usability:dead-end:d"],
                "fixed": ["tests:no-test:b"],
                "still_open": ["security:secret-scan:a"],
                "not_rechecked": [],
                "not_reraised": ["privacy:log:c"],
            },
        )

    def test_a_vanished_key_is_fixed_only_with_a_change_under_its_path(self):
        file_key, dir_key = "tests:no-test:src/a.py", "tests:no-test:lib"
        prev = self.run_doc([file_key, dir_key])
        cases = {
            "unchanged commit": ([], [], [file_key, dir_key]),
            "change under the file": (["src/a.py"], [file_key], [dir_key]),
            "change elsewhere": (["docs/x.md"], [], [file_key, dir_key]),
            "file under a directory path": (["lib/m.py"], [dir_key], [file_key]),
            "sibling sharing a prefix": (["library/m.py"], [], [file_key, dir_key]),
            "commits not comparable": (None, [], [file_key, dir_key]),
        }
        for label, (changed, fixed, not_reraised) in cases.items():
            with self.subTest(label):
                out = fc.diff_runs(prev, self.run_doc([]), changed=changed)
                self.assertEqual(out["fixed"], fixed)
                self.assertEqual(out["not_reraised"], not_reraised)

    def test_a_repo_wide_key_is_covered_by_any_change(self):
        prev = self.run_doc(["repo-hygiene:no-license:."])
        cur = self.run_doc([])
        self.assertEqual(
            fc.diff_runs(prev, cur, changed=["anything.py"])["fixed"],
            ["repo-hygiene:no-license:."],
        )
        self.assertEqual(fc.diff_runs(prev, cur, changed=[])["fixed"], [])

    def test_a_key_a_lens_did_not_recheck_is_not_fixed(self):
        prev = self.run_doc(["tests:no-test:b", "tests:no-test:c"])
        out = fc.diff_runs(
            prev,
            self.run_doc([]),
            not_rechecked=["tests:no-test:b"],
            changed=["b", "c"],
        )
        self.assertEqual(out["not_rechecked"], ["tests:no-test:b"])
        self.assertEqual(out["fixed"], ["tests:no-test:c"])

    def test_a_not_rechecked_key_that_came_back_stays_open(self):
        prev = self.run_doc(["tests:no-test:b"])
        cur = self.run_doc(["tests:no-test:b"])
        out = fc.diff_runs(prev, cur, not_rechecked=["tests:no-test:b"], changed=[])
        self.assertEqual(out["still_open"], ["tests:no-test:b"])
        self.assertEqual(out["not_rechecked"], [])

    def test_a_finding_in_an_area_not_assessed_now_is_not_rechecked_not_fixed(self):
        prev = self.run_doc(
            ["feature-completeness:doc-command-missing:README.md", "tests:no-test:b"]
        )
        cur = self.run_doc([], not_assessed=("feature-completeness",))
        out = fc.diff_runs(prev, cur, changed=["README.md", "b"])
        self.assertEqual(
            out["not_rechecked"], ["feature-completeness:doc-command-missing:README.md"]
        )
        self.assertEqual(out["fixed"], ["tests:no-test:b"])

    def test_the_previous_findings_area_field_beats_the_key_prefix(self):
        prev = self.run_doc(["code-quality:null-body:a.py"])
        prev["findings"][0]["area"] = "feature-completeness"
        cur = self.run_doc([], not_assessed=("feature-completeness",))
        out = fc.diff_runs(prev, cur, changed=["a.py"])
        self.assertEqual(out["not_rechecked"], ["code-quality:null-body:a.py"])

    def test_a_key_in_an_unknown_area_is_not_rechecked(self):
        out = fc.diff_runs(self.run_doc(["bogus:x:y"]), self.run_doc([]), changed=["y"])
        self.assertEqual(out["not_rechecked"], ["bogus:x:y"])

    def test_duplicate_keys_count_once(self):
        out = fc.diff_runs(self.run_doc([]), self.run_doc(["tests:a:b", "tests:a:b"]))
        self.assertEqual(out["new"], ["tests:a:b"])

    def test_an_older_schema_baseline_is_usable_for_the_diff(self):
        old = {
            "findings": [
                {"key": "security:secret-scan:a", "area": "security", "lens": "legacy"}
            ],
            "scorecard": {"overall": "retired-verdict"},
        }
        self.assertEqual(fc.diff_input_errors(old), [])

    def test_a_baseline_the_diff_cannot_read_is_reported(self):
        cases = {
            "not an object": [],
            "no findings": {},
            "findings not a list": {"findings": {}},
            "finding not an object": {"findings": ["x"]},
            "finding without a key": {"findings": [{"area": "tests"}]},
            "key not a string": {"findings": [{"key": 3}]},
            "malformed key": {"findings": [{"key": "no-colons"}]},
            "area not a string": {"findings": [{"key": "a:b:c", "area": 1}]},
        }
        for label, doc in cases.items():
            with self.subTest(label):
                self.assertTrue(fc.diff_input_errors(doc), label)

    def test_parse_key_splits_on_the_first_two_colons(self):
        self.assertEqual(
            fc.parse_key("security:secret-scan:./a:b/c"),
            ("security", "secret-scan", "a:b/c"),
        )
        self.assertIsNone(fc.parse_key("security:only"))


class RunnerTests(unittest.TestCase):
    def test_default_skill_name_matches_the_plugin_and_skill(self):
        plugin = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
        frontmatter = (SKILL_DIR / "SKILL.md").read_text().split("---")[1]
        match = re.search(r"^name:\s*(\S+)", frontmatter, re.MULTILINE)
        assert match is not None
        self.assertEqual(run_evals.DEFAULT_SKILL, f"/{plugin['name']}:{match.group(1)}")

    def test_run_cannot_use_publish_send_or_edit_tools(self):
        for tool in run_evals.ALLOWED_TOOLS:
            self.assertNotRegex(tool.lower(), r"artifact|publish|send|edit")
        cmd = run_evals.build_command(
            "claude", "/p:s", "quick", Path("/plug"), Path("/art"), 10
        )
        self.assertEqual(cmd[cmd.index("--disallowedTools") + 1], "Artifact")
        self.assertNotIn("Artifact", cmd[cmd.index("--allowedTools") + 1])

    def test_command_carries_the_flags_and_budget(self):
        cmd = run_evals.build_command(
            "claude", "/p:s", "quick", Path("/plug"), Path("/art"), 10
        )
        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertTrue(cmd[2].startswith("/p:s quick"))
        self.assertIn("/art/findings.json", cmd[2])
        for flag, value in [
            ("--max-budget-usd", "10"),
            ("--plugin-dir", "/plug"),
            ("--permission-mode", "dontAsk"),
            ("--add-dir", "/art"),
            ("--output-format", "json"),
        ]:
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertIn("--no-session-persistence", cmd)

    def test_dry_run_generates_prints_and_never_spawns_claude(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(
                run_evals, "run_claude", side_effect=AssertionError("spawned claude")
            ),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            code = run_evals.main(
                ["--dry-run", "--out", tmp, "--fixtures", "single-script"]
            )
            self.assertEqual(code, 0)
            self.assertTrue(
                (Path(tmp) / "fixtures" / "single-script" / ".git").is_dir()
            )
        text = out.getvalue()
        self.assertIn("# single-script: cwd", text)
        self.assertIn("--max-budget-usd 10", text)
        self.assertEqual(text.count("claude -p"), 1)

    def test_dry_run_says_the_preflight_would_run_and_which_names_it_tries(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(
                run_evals, "run_claude", side_effect=AssertionError("spawned claude")
            ),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            run_evals.main(["--dry-run", "--out", tmp, "--fixtures", "single-script"])
        text = out.getvalue()
        self.assertIn("preflight", text)
        self.assertIn("/dividedby-skills:repo-audit, /repo-audit", text)

    def test_unknown_fixture_is_an_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run_evals.main(["--dry-run", "--fixtures", "nope"]), 2)

    def test_cost_from_a_canned_result(self):
        result = run_evals.parse_result(
            json.dumps(
                {
                    "type": "result",
                    "is_error": False,
                    "duration_ms": 90000,
                    "total_cost_usd": 1.5,
                    "modelUsage": {
                        "a": {
                            "inputTokens": 10,
                            "outputTokens": 20,
                            "cacheReadInputTokens": 30,
                            "cacheCreationInputTokens": 40,
                        },
                        "b": {"inputTokens": 1, "outputTokens": 2},
                    },
                }
            )
        )
        cost = run_evals.summarise_cost(result)
        self.assertEqual(
            (cost.usd, cost.tokens, cost.wall_s, cost.status), (1.5, 103, 90.0, "ok")
        )

    def test_cost_flags_errors_and_unreadable_output(self):
        capped = run_evals.summarise_cost(
            {"is_error": True, "subtype": "error_max_budget_usd", "total_cost_usd": 10}
        )
        self.assertEqual(capped.status, "error: error_max_budget_usd")
        failed_start = run_evals.summarise_cost(
            {
                "is_error": True,
                "subtype": "success",
                "terminal_reason": "api_error",
                "result": "Failed to authenticate",
            }
        )
        self.assertEqual(
            failed_start.status, "error: api_error (Failed to authenticate)"
        )
        self.assertEqual(
            run_evals.summarise_cost(run_evals.parse_result("not json")).status,
            "no result JSON",
        )

    def test_findings_are_located_in_the_copy_or_the_named_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            art = tmp_path / "art"
            art.mkdir()
            named = tmp_path / "named" / "findings.json"
            named.parent.mkdir()
            named.write_text("{}")
            self.assertEqual(
                run_evals.locate_findings(art, f"saved to {named}.", 0), named
            )
            self.assertIsNone(run_evals.locate_findings(art, "no path here", 0))
            (art / "findings.json").write_text("{}")
            self.assertEqual(
                run_evals.locate_findings(art, f"saved to {named}", 0),
                art / "findings.json",
            )

    def test_a_file_older_than_the_run_is_never_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            art = tmp_path / "art"
            art.mkdir()
            named = tmp_path / "findings.json"
            for path in (art / "findings.json", named):
                path.write_text("{}")
                os.utime(path, (1000, 1000))
            self.assertIsNone(run_evals.locate_findings(art, f"see {named}", 2000))
            self.assertEqual(
                run_evals.locate_findings(art, "", 500), art / "findings.json"
            )

    @staticmethod
    def init_line(**fields) -> str:
        event = {"type": "system", "subtype": "init", "slash_commands": [], **fields}
        return json.dumps({"type": "hook", "subtype": "x"}) + "\n" + json.dumps(event)

    def test_skill_resolution_picks_the_name_the_child_loaded(self):
        namespaced, bare = "dividedby-skills:repo-audit", "repo-audit"
        for label, explicit, loaded, want in [
            (
                "explicit name present",
                "/custom:audit",
                ["custom:audit"],
                "/custom:audit",
            ),
            ("explicit without a slash", "repo-audit", [bare], "/repo-audit"),
            ("default namespaced present", None, [bare, namespaced], f"/{namespaced}"),
            ("falls back to bare", None, ["compact", bare], f"/{bare}"),
            ("name listed under skills", None, [], f"/{bare}"),
            ("explicit absent", "/custom:audit", [bare], None),
            ("neither present", None, ["compact", "other:audit-ish"], None),
        ]:
            with self.subTest(label):
                init = {"slash_commands": loaded}
                if label == "name listed under skills":
                    init["skills"] = [bare]
                name, note = run_evals.pick_skill(explicit, init)
                self.assertEqual(name, want)
                if want is None:
                    self.assertIn("not loaded", note)

    def test_skill_resolution_without_an_init_event_is_an_error(self):
        name, note = run_evals.pick_skill(None, run_evals.parse_init("not json\n{}"))
        self.assertIsNone(name)
        self.assertIn("no init event", note)

    def test_preflight_command_is_one_cheap_turn_with_the_plugin_dir(self):
        cmd = run_evals.build_preflight_command("claude", Path("/plug"))
        self.assertEqual(cmd[:2], ["claude", "-p"])
        for flag, value in [
            ("--plugin-dir", "/plug"),
            ("--output-format", "stream-json"),
            ("--max-turns", "1"),
        ]:
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertIn("--verbose", cmd)

    def test_resolve_skill_spawns_once_from_an_empty_folder_and_reads_the_init_line(
        self,
    ):
        calls = []

        def spawn(cmd, cwd, timeout, until_init=False):
            calls.append((cmd, list(Path(cwd).iterdir()), until_init))
            return self.init_line(slash_commands=["repo-audit"]), ""

        args = run_evals.parse_args([])
        with mock.patch.object(run_evals, "run_claude", side_effect=spawn):
            name, _ = run_evals.resolve_skill(args)
        self.assertEqual(name, "/repo-audit")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1:], ([], True))

    def test_main_stops_before_any_fixture_when_the_skill_is_not_loaded(self):
        def spawn(cmd, cwd, timeout, until_init=False):
            assert until_init, "a fixture run started"
            return self.init_line(slash_commands=["compact"]), ""

        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(run_evals, "run_claude", side_effect=spawn),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()) as err,
        ):
            code = run_evals.main(["--out", tmp, "--fixtures", "single-script"])
        self.assertEqual(code, 2)
        self.assertIn("not loaded", err.getvalue())
        self.assertIn("no fixture was run", err.getvalue())

    def test_main_runs_the_fixtures_under_the_resolved_name(self):
        prompts = []

        def spawn(cmd, cwd, timeout, until_init=False):
            if until_init:
                return self.init_line(slash_commands=["repo-audit"]), ""
            prompts.append(cmd[2])
            return "{}", ""

        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(run_evals, "run_claude", side_effect=spawn),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            run_evals.main(["--out", tmp, "--fixtures", "single-script"])
        self.assertEqual(len(prompts), 1)
        self.assertTrue(prompts[0].startswith("/repo-audit quick"))
        self.assertIn("preflight: skill `/repo-audit` is loaded", out.getvalue())

    def test_the_preflight_kills_the_child_after_its_init_line(self):
        script = (
            "import json,sys,time\n"
            "print(json.dumps({'type':'system','subtype':'init','slash_commands':['repo-audit']}),flush=True)\n"
            "time.sleep(60)\n"
        )
        started = time.time()
        stdout, _ = run_evals.run_claude(
            [sys.executable, "-c", script], Path.cwd(), 30, until_init=True
        )
        self.assertLess(time.time() - started, 20)
        init = run_evals.parse_init(stdout)
        assert init is not None
        self.assertEqual(init["slash_commands"], ["repo-audit"])

    def run_one_fixture(self, tmp: str, spawn) -> run_evals.FixtureRun:
        out = Path(tmp)
        repo = fixtures.generate(out / "fixtures", only=["single-script"])[
            "single-script"
        ]
        args = run_evals.parse_args(["--fixtures", "single-script"])
        with mock.patch.object(run_evals, "run_claude", side_effect=spawn):
            return run_evals.run_fixture(
                "single-script", repo, out, args, SCHEMA, EXPECTATIONS
            )

    def test_a_rerun_that_writes_nothing_does_not_pass_on_the_last_runs_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "single-script"
            stale.mkdir()
            (stale / "findings.json").write_text(json.dumps(SAMPLE))
            run = self.run_one_fixture(tmp, lambda cmd, cwd, timeout: ("{}", ""))
            self.assertEqual(run.results[0].name, "findings.json")
            self.assertFalse(run.results[0].ok)
            self.assertFalse((stale / "findings.json").exists())

    def test_a_run_that_copies_findings_is_checked_against_the_expectations(self):
        with tempfile.TemporaryDirectory() as tmp:

            def spawn(cmd, cwd, timeout):
                art = Path(tmp) / "single-script"
                (art / "findings.json").write_text(json.dumps(SAMPLE))
                return json.dumps({"total_cost_usd": 2.0}), ""

            run = self.run_one_fixture(tmp, spawn)
            self.assertEqual([r.name for r in run.results if not r.ok], [])
            self.assertEqual(run.cost.usd, 2.0)

    def test_report_lists_each_expectation_and_a_total(self):
        run = run_evals.FixtureRun(
            "single-script",
            [
                fc.Result("tier", True, "ok"),
                fc.Result("planted: secret", False, "missing"),
            ],
            run_evals.Cost(1.25, 1000, 120, "ok"),
        )
        report = run_evals.format_report([run, run])
        self.assertIn("single-script | tier | PASS | ok", report)
        self.assertIn("single-script | planted: secret | FAIL | missing", report)
        self.assertIn("TOTAL | 2.50 | 2,000 | 4.0 min", report)


if __name__ == "__main__":
    unittest.main()
