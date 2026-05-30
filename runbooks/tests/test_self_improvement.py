import tempfile
import unittest
from pathlib import Path

from runbooks.lib.kb_source import load_kb_source, read_kb
from runbooks.lib.map_store import read_map
from runbooks.lib.self_improvement import (
    SOURCE_LABEL,
    TRIAGE_LABEL,
    run,
)


class FakeCommit:
    """Records the paths the run-book asked to commit."""

    def __init__(self):
        self.committed = []

    def __call__(self, path):
        self.committed.append(Path(path))


class FakeTracker:
    """Records issue payloads filed, and serves open dedup keys."""

    def __init__(self, open_keys=()):
        self.filed = []
        self._open = list(open_keys)

    def file_issue(self, payload):
        self.filed.append(payload)

    def open_issues(self):
        return list(self._open)


class SelfImprovementRunTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.map_path = Path(self._tmp.name) / "integration-map.md"
        self.calls = []
        self.commit = FakeCommit()

    def tearDown(self):
        self._tmp.cleanup()

    def kb_reader(self):
        self.calls.append("kb")
        return {"practices": ["red-green-refactor"]}

    def repo_reader(self):
        self.calls.append("repo")
        return {"skills": ["tdd"]}

    def build_map(self, kb, repo):
        # Deterministic stand-in for the agent's analysis.
        return f"# Integration map\n\n- {repo['skills'][0]} ↔ {kb['practices'][0]}\n"

    def run_once(self):
        return run(
            kb_reader=self.kb_reader,
            repo_reader=self.repo_reader,
            build_map=self.build_map,
            map_path=self.map_path,
            commit=self.commit,
        )

    def test_first_run_reads_inputs_and_commits_map(self):
        result = self.run_once()
        self.assertIn("kb", self.calls)
        self.assertIn("repo", self.calls)
        self.assertTrue(result["changed"])
        self.assertEqual(self.commit.committed, [self.map_path])
        self.assertIn("tdd ↔ red-green-refactor", read_map(self.map_path))

    def test_rerun_with_same_inputs_is_minimal_diff_no_recommit(self):
        self.run_once()
        result = self.run_once()
        self.assertFalse(result["changed"])
        # Committed exactly once across both runs — no wholesale regeneration.
        self.assertEqual(self.commit.committed, [self.map_path])

    def test_sparse_kb_still_produces_and_commits_a_map(self):
        result = run(
            kb_reader=lambda: {"practices": []},
            repo_reader=lambda: {"skills": ["tdd"]},
            build_map=lambda kb, repo: "# Integration map\n\n- tdd ↔ (no counterpart yet)\n",
            map_path=self.map_path,
            commit=self.commit,
        )
        self.assertTrue(result["changed"])
        self.assertEqual(self.commit.committed, [self.map_path])
        self.assertIn("no counterpart yet", read_map(self.map_path))

    def test_writes_only_to_map_path_never_into_the_kb(self):
        kb_dir = Path(self._tmp.name) / "agent-research" / "knowledge"
        kb_dir.mkdir(parents=True)
        (kb_dir / "practices.md").write_text("- red-green-refactor\n")
        before = sorted(p.name for p in kb_dir.iterdir())

        run(
            kb_reader=lambda: {"practices": ["red-green-refactor"]},
            repo_reader=lambda: {"skills": ["tdd"]},
            build_map=self.build_map,
            map_path=self.map_path,
            commit=self.commit,
        )

        # The KB is read-only input; the map is written consumer-side only.
        self.assertEqual(sorted(p.name for p in kb_dir.iterdir()), before)
        self.assertTrue(self.map_path.exists())


class SelfImprovementKbAcquisitionTest(unittest.TestCase):
    """The KB acquisition contract (#29): the real kb-source loader + reader feed
    the orchestrator's injected ``kb_reader`` so ``build_map`` is exercised over a
    ``knowledge/<subject>/{practices,artifacts}/``-shaped fixture — the C parallel
    to the gap-scanner's fixture-dir scan tests."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.kb_root = self.base / "agent-research"
        self.map_path = self.base / "integration-map.md"
        self.commit = FakeCommit()

    def tearDown(self):
        self._tmp.cleanup()

    def _note(self, subpath, name, text):
        d = self.kb_root / subpath
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text)

    def _config(self, subpaths):
        cfg = self.base / "kb-source.json"
        cfg.write_text(
            '{"kb": "dividedby/agent-research", "subpaths": %s}'
            % list(subpaths).__repr__().replace("'", '"')
        )
        return cfg

    def test_configured_reader_feeds_build_map_over_the_knowledge_layer(self):
        self._note("knowledge/mattpocock/practices", "index.md", "# practices")
        self._note(
            "knowledge/mattpocock/practices", "tdd.md", "red-green-refactor"
        )
        self._note("knowledge/mattpocock/artifacts", "index.md", "# artifacts")
        cfg = self._config(
            [
                "knowledge/mattpocock/practices",
                "knowledge/mattpocock/artifacts",
            ]
        )
        source = load_kb_source(cfg)

        def build_map(kb, repo):
            # The agent's analysis step, exercised over the real read: a stable
            # listing of the practice notes it ingested. The category axis is a
            # first-class field — no path re-parsing.
            practices = [n["name"] for n in kb if n["category"] == "practices"]
            return "# Integration map\n\n" + "".join(
                f"- {repo['skills'][0]} ↔ {name}\n" for name in practices
            )

        result = run(
            kb_reader=lambda: read_kb(self.kb_root, source["subpaths"]),
            repo_reader=lambda: {"skills": ["tdd"]},
            build_map=build_map,
            map_path=self.map_path,
            commit=self.commit,
        )

        self.assertTrue(result["changed"])
        self.assertEqual(self.commit.committed, [self.map_path])
        written = read_map(self.map_path)
        # The configured practice notes were ingested and mapped, in stable order.
        self.assertIn("tdd ↔ index.md", written)
        self.assertIn("tdd ↔ tdd.md", written)

    def test_subject_not_in_config_is_never_ingested(self):
        # No auto-discovery: a subject present under the KB root but absent from
        # the configured subpaths never reaches build_map.
        self._note("knowledge/mattpocock/practices", "tdd.md", "listed")
        self._note("knowledge/secret-subject/practices", "leak.md", "private")
        cfg = self._config(["knowledge/mattpocock/practices"])
        source = load_kb_source(cfg)
        seen = {}

        def build_map(kb, repo):
            seen["names"] = sorted(n["name"] for n in kb)
            return "# Integration map\n\n- tdd ↔ practices\n"

        run(
            kb_reader=lambda: read_kb(self.kb_root, source["subpaths"]),
            repo_reader=lambda: {"skills": ["tdd"]},
            build_map=build_map,
            map_path=self.map_path,
            commit=self.commit,
        )
        self.assertEqual(seen["names"], ["tdd.md"])

    def test_sparse_kb_still_builds_and_commits_a_map(self):
        # A configured subject the KB does not yet carry yields an empty read; the
        # map is then valid but sparse (parallels the existing sparse-KB test).
        cfg = self._config(["knowledge/humanlayer/practices"])
        source = load_kb_source(cfg)
        result = run(
            kb_reader=lambda: read_kb(self.kb_root, source["subpaths"]),
            repo_reader=lambda: {"skills": ["tdd"]},
            build_map=lambda kb, repo: "# Integration map\n\n- tdd ↔ (gap)\n"
            if not kb
            else "# Integration map\n\n- tdd ↔ found\n",
            map_path=self.map_path,
            commit=self.commit,
        )
        self.assertTrue(result["changed"])
        self.assertIn("(gap)", read_map(self.map_path))


class SelfImprovementProposalTest(unittest.TestCase):
    """The proposal step (#19): diff the committed map for refinement candidates,
    run the real proposal gate, file at most one issue. Never edits a skill."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.map_path = Path(self._tmp.name) / "integration-map.md"
        self.commit = FakeCommit()

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, find_refinements, tracker, **over):
        kwargs = dict(
            kb_reader=lambda: {"practices": ["red-green-refactor"]},
            repo_reader=lambda: {"skills": ["tdd"]},
            build_map=lambda kb, repo: "# Integration map\n\n- tdd ↔ red-green-refactor\n",
            map_path=self.map_path,
            commit=self.commit,
            find_refinements=find_refinements,
            open_issues=tracker.open_issues,
            file_issue=tracker.file_issue,
        )
        kwargs.update(over)
        return run(**kwargs)

    def test_files_one_refinement_with_provenance_and_triage_labels(self):
        tracker = FakeTracker()
        candidates = [
            {"dedup_key": "tdd-mentions-coverage", "priority": 3,
             "title": "tdd: cross-link coverage practice", "body": "Generalized refinement."},
            {"dedup_key": "low-value", "priority": 1,
             "title": "minor", "body": "barely worth it"},
        ]
        result = self._run(lambda content, kb, repo: candidates, tracker)

        self.assertEqual(result["filed"], 1)
        self.assertEqual(len(tracker.filed), 1)
        payload = tracker.filed[0]
        # Highest priority candidate wins.
        self.assertEqual(payload["title"], "tdd: cross-link coverage practice")
        self.assertIn(SOURCE_LABEL, payload["labels"])
        self.assertIn(TRIAGE_LABEL, payload["labels"])
        # The map is still committed — analysis is not skipped by the proposal step.
        self.assertEqual(self.commit.committed, [self.map_path])

    def test_dedup_against_open_issue_files_nothing(self):
        tracker = FakeTracker(open_keys=["tdd-mentions-coverage"])
        candidates = [
            {"dedup_key": "tdd-mentions-coverage", "priority": 3,
             "title": "dup", "body": "already open"},
        ]
        result = self._run(lambda content, kb, repo: candidates, tracker)
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_no_candidate_clears_the_bar_files_nothing(self):
        tracker = FakeTracker()
        result = self._run(lambda content, kb, repo: [], tracker)
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])
        # Map still committed even when nothing is filed.
        self.assertEqual(self.commit.committed, [self.map_path])

    def test_below_min_priority_files_nothing(self):
        tracker = FakeTracker()
        candidates = [{"dedup_key": "weak", "priority": 1, "title": "x", "body": "y"}]
        result = self._run(
            lambda content, kb, repo: candidates, tracker, min_priority=2
        )
        self.assertEqual(result["filed"], 0)

    def test_refinement_step_receives_committed_map_content(self):
        tracker = FakeTracker()
        seen = {}

        def find(content, kb, repo):
            seen["content"] = content
            return []

        self._run(find, tracker)
        self.assertIn("tdd ↔ red-green-refactor", seen["content"])

    def test_proposal_step_writes_no_file_other_than_the_map(self):
        tracker = FakeTracker()
        candidates = [{"dedup_key": "k", "priority": 5, "title": "t", "body": "b"}]
        self._run(lambda content, kb, repo: candidates, tracker)
        # Filing goes through the tracker seam, never the filesystem: the map is
        # the only artifact written. No skill is edited.
        written = [p.name for p in self.map_path.parent.iterdir()]
        self.assertEqual(written, ["integration-map.md"])

    def test_private_signal_in_body_is_blocked_nothing_filed(self):
        # C reads the private agent-research KB, so its filed payload is guarded
        # exactly like the gap-scanner's (#26): a would-be high-priority refinement
        # whose body pastes a file path is dropped before the gate is consulted.
        tracker = FakeTracker()
        candidate = {
            "dedup_key": "k", "priority": 9, "title": "leaky",
            "body": "The KB note lives at notes/private/charge.py.",
        }
        result = self._run(lambda content, kb, repo: [candidate], tracker)
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_private_signal_in_title_is_blocked_nothing_filed(self):
        # The title is published too, so a clean body does not excuse a leaky title.
        tracker = FakeTracker()
        candidate = {
            "dedup_key": "k", "priority": 9,
            "title": "Refine tdd per notes/private/charge.py",
            "body": "A clean, generalized refinement of the tdd skill.",
        }
        result = self._run(lambda content, kb, repo: [candidate], tracker)
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_private_marker_in_payload_is_blocked(self):
        tracker = FakeTracker()
        candidate = {
            "dedup_key": "k", "priority": 5, "title": "leaky marker",
            "body": "This idea came straight from agent-research/secret-notes.",
        }
        result = self._run(
            lambda content, kb, repo: [candidate], tracker,
            private_markers=["agent-research/secret-notes"],
        )
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_leaky_candidate_dropped_clean_one_still_files(self):
        # A leaky high-priority draft is dropped; a clean lower-priority draft
        # still files. Proves sanitize-then-gate over the survivors.
        tracker = FakeTracker()
        leaky = {
            "dedup_key": "leak", "priority": 9, "title": "x",
            "body": "see notes/private/config.py",
        }
        clean = {
            "dedup_key": "clean", "priority": 2, "title": "clean refinement",
            "body": "Cross-link the coverage practice into the tdd skill.",
        }
        result = self._run(lambda content, kb, repo: [leaky, clean], tracker)
        self.assertEqual(result["filed"], 1)
        self.assertEqual(tracker.filed[0]["title"], "clean refinement")

    def test_analysis_only_run_without_tracker_files_nothing(self):
        # Backward compat: the #16 analysis-only invocation still works.
        commit = FakeCommit()
        result = run(
            kb_reader=lambda: {"practices": []},
            repo_reader=lambda: {"skills": ["tdd"]},
            build_map=lambda kb, repo: "# Integration map\n\n- tdd ↔ (gap)\n",
            map_path=self.map_path,
            commit=commit,
        )
        self.assertTrue(result["changed"])
        self.assertEqual(result["filed"], 0)


if __name__ == "__main__":
    unittest.main()
