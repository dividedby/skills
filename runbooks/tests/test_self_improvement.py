import tempfile
import unittest
from pathlib import Path

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
