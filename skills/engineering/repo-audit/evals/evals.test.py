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
        cls.second = fixtures.generate(root / "second")
        cls.root = root

    def test_generation_is_idempotent(self):
        for name in fixtures.FIXTURES:
            with self.subTest(name):
                self.assertEqual(head(self.first[name]), head(self.second[name]))

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
            self.assertNotIn('"report"', (repo / "package.json").read_text())
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
            fc.diff_runs(prev, cur),
            {
                "new": ["usability:dead-end:d"],
                "fixed": ["tests:no-test:b", "privacy:log:c"],
                "still_open": ["security:secret-scan:a"],
                "not_rechecked": [],
            },
        )

    def test_a_finding_in_an_area_not_assessed_now_is_not_rechecked_not_fixed(self):
        prev = self.run_doc(
            ["feature-completeness:doc-command-missing:README.md", "tests:no-test:b"]
        )
        cur = self.run_doc([], not_assessed=("feature-completeness",))
        out = fc.diff_runs(prev, cur)
        self.assertEqual(
            out["not_rechecked"], ["feature-completeness:doc-command-missing:README.md"]
        )
        self.assertEqual(out["fixed"], ["tests:no-test:b"])

    def test_a_key_in_an_unknown_area_is_not_rechecked(self):
        out = fc.diff_runs(self.run_doc(["bogus:x:y"]), self.run_doc([]))
        self.assertEqual(out["not_rechecked"], ["bogus:x:y"])

    def test_duplicate_keys_count_once(self):
        out = fc.diff_runs(self.run_doc([]), self.run_doc(["tests:a:b", "tests:a:b"]))
        self.assertEqual(out["new"], ["tests:a:b"])

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
