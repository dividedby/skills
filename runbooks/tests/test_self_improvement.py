import tempfile
import unittest
from pathlib import Path

from runbooks.lib.map_store import read_map
from runbooks.lib.self_improvement import run


class FakeCommit:
    """Records the paths the run-book asked to commit."""

    def __init__(self):
        self.committed = []

    def __call__(self, path):
        self.committed.append(Path(path))


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


if __name__ == "__main__":
    unittest.main()
