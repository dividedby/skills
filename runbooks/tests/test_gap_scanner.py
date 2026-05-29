import shutil
import tempfile
import unittest
from pathlib import Path

from runbooks.lib.gap_scanner import run


class FakeRemote:
    def __init__(self, fixtures):
        self.fixtures = fixtures
        self.cloned = []

    def __call__(self, name, dest):
        self.cloned.append(name)
        if name not in self.fixtures:
            raise RuntimeError(f"unreachable: {name}")
        shutil.copytree(self.fixtures[name], dest)


class FakeTracker:
    def __init__(self):
        self.filed = []

    def __call__(self, body):
        self.filed.append(body)


class GapScannerRunTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.fixtures = {}
        self.tracker = FakeTracker()

    def tearDown(self):
        self._tmp.cleanup()

    def _fixture_repo(self, name):
        src = self.base / "remote" / name
        src.mkdir(parents=True)
        (src / "README.md").write_text("proprietary")
        self.fixtures[name] = src

    def test_scans_listed_repos_files_nothing_and_cleans_up(self):
        self._fixture_repo("billing")
        self._fixture_repo("unlisted")
        clone = FakeRemote(self.fixtures)

        result = run(["billing"], clone=clone, file_issue=self.tracker)

        self.assertEqual(clone.cloned, ["billing"])
        self.assertEqual(result["scanned"], ["billing"])
        self.assertEqual(result["filed"], 0)
        self.assertEqual(self.tracker.filed, [])  # no proposal logic yet
        self.assertFalse(result["workdir"].exists())  # working area empty after run

    def test_empty_repo_list_is_a_clean_no_op(self):
        clone = FakeRemote(self.fixtures)
        result = run([], clone=clone, file_issue=self.tracker)
        self.assertEqual(clone.cloned, [])
        self.assertEqual(result["scanned"], [])
        self.assertEqual(result["filed"], 0)
        self.assertFalse(result["workdir"].exists())


if __name__ == "__main__":
    unittest.main()
