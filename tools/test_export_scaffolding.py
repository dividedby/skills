"""Tests for the scaffolding exporter — focus on the secret scrubber and file
selection, the two places a mistake either leaks a secret or silently drops a
surface. Run: python3 -m unittest tools.test_export_scaffolding
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.export_scaffolding import scrub, select_files


class TestScrub(unittest.TestCase):
    def test_keeps_github_actions_secret_reference(self):
        # ${{ secrets.X }} carries no value — must survive untouched.
        text = "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}"
        out, n = scrub(text)
        self.assertEqual(out, text)
        self.assertEqual(n, 0)

    def test_redacts_token_prefixes(self):
        for tok in ("ghp_ABCDEFGHIJ1234567890abcdEFGH",
                    "sk-ant-abcd1234EFGH5678ijkl90mnop",
                    "AKIAIOSFODNN7EXAMPLE"):
            out, n = scrub(f"value = {tok}")
            self.assertNotIn(tok, out)
            self.assertGreaterEqual(n, 1)

    def test_redacts_kv_secret_value(self):
        out, n = scrub("api_key = 'sk_live_abcd1234EFGH5678ijkl'")
        self.assertIn("<REDACTED>", out)
        self.assertNotIn("sk_live_abcd1234EFGH5678ijkl", out)
        self.assertEqual(n, 1)

    def test_leaves_short_nonsecret(self):
        text = "password=hunter2"          # too short to be an opaque token
        out, n = scrub(text)
        self.assertEqual(out, text)
        self.assertEqual(n, 0)


class TestSelectFiles(unittest.TestCase):
    def test_excludes_take_precedence_and_dedup(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.md").write_text("a")
            (root / "my-secret.txt").write_text("s")
            (root / "sub").mkdir()
            (root / "sub" / "b.md").write_text("b")
            got = select_files(
                root,
                include=["*.md", "**/*.md", "my-secret.txt"],
                exclude=["**/*secret*"],
            )
            rels = [p.relative_to(root).as_posix() for p in got]
            self.assertEqual(rels, ["a.md", "sub/b.md"])  # sorted, deduped, no secret


if __name__ == "__main__":
    unittest.main()
