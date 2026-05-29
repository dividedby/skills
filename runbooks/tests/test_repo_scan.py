import shutil
import tempfile
import unittest
from pathlib import Path

from runbooks.lib.repo_scan import load_repo_list, scan


class FakeRemote:
    """Stands in for the git host: named fixture dirs 'cloned' by copytree.

    Repos not present here are unreachable and raise when cloned.
    """

    def __init__(self, fixtures):
        self.fixtures = fixtures  # name -> source Path
        self.cloned = []

    def __call__(self, name, dest):
        self.cloned.append(name)
        if name not in self.fixtures:
            raise RuntimeError(f"unreachable: {name}")
        shutil.copytree(self.fixtures[name], dest)


class RepoScanTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.fixtures = {}

    def tearDown(self):
        self._tmp.cleanup()

    def _fixture_repo(self, name, filename="README.md", text="hi"):
        src = self.base / "remote" / name
        src.mkdir(parents=True)
        (src / filename).write_text(text)
        self.fixtures[name] = src
        return src

    def test_clones_listed_repo_and_cleans_up(self):
        self._fixture_repo("billing", text="proprietary")
        clone = FakeRemote(self.fixtures)

        with scan(["billing"], clone=clone) as result:
            self.assertEqual(clone.cloned, ["billing"])
            self.assertIn("billing", result.repos)
            self.assertEqual((result.repos["billing"] / "README.md").read_text(), "proprietary")
            workdir = result.workdir
            self.assertTrue(workdir.exists())

        # Everything cloned is removed at end of run.
        self.assertFalse(workdir.exists())

    def test_clones_owner_slash_name_entries(self):
        # The real config lists repos as "owner/name"; the slash must not break
        # the scratch-dir layout or the cleanup.
        src = self.base / "remote" / "acme" / "billing"
        src.mkdir(parents=True)
        (src / "README.md").write_text("proprietary")
        self.fixtures["acme/billing"] = src
        clone = FakeRemote(self.fixtures)

        with scan(["acme/billing"], clone=clone) as result:
            self.assertIn("acme/billing", result.repos)
            self.assertEqual((result.repos["acme/billing"] / "README.md").read_text(), "proprietary")
            workdir = result.workdir
        self.assertFalse(workdir.exists())

    def test_unlisted_repo_is_never_read(self):
        self._fixture_repo("billing")
        self._fixture_repo("secret-side-project")  # exists on the remote but not listed
        clone = FakeRemote(self.fixtures)

        with scan(["billing"], clone=clone) as result:
            self.assertEqual(clone.cloned, ["billing"])
            self.assertNotIn("secret-side-project", result.repos)

    def test_unreachable_listed_repo_is_skipped_not_crashed(self):
        self._fixture_repo("billing")
        clone = FakeRemote(self.fixtures)  # "ghost" has no fixture -> raises

        with scan(["ghost", "billing"], clone=clone) as result:
            self.assertEqual(clone.cloned, ["ghost", "billing"])
            self.assertNotIn("ghost", result.repos)
            self.assertIn("billing", result.repos)

    def test_load_repo_list_reads_only_listed_repos(self):
        cfg = self.base / "repos.json"
        cfg.write_text('{"repos": ["acme/billing", "acme/auth"]}')
        self.assertEqual(load_repo_list(cfg), ["acme/billing", "acme/auth"])

    def test_load_missing_config_is_safe_no_op(self):
        # No auto-discovery: an absent config scans nothing, never "everything".
        self.assertEqual(load_repo_list(self.base / "absent.json"), [])

    def test_empty_repo_list_is_a_clean_no_op(self):
        clone = FakeRemote(self.fixtures)
        with scan([], clone=clone) as result:
            self.assertEqual(clone.cloned, [])
            self.assertEqual(result.repos, {})
            workdir = result.workdir
        self.assertFalse(workdir.exists())


if __name__ == "__main__":
    unittest.main()
