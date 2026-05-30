import tempfile
import unittest
from pathlib import Path

from runbooks.lib.kb_source import load_kb_source, read_kb


class LoadKbSourceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_reads_kb_slug_and_explicit_subpaths(self):
        cfg = self.base / "kb-source.json"
        cfg.write_text(
            '{"kb": "dividedby/agent-research", '
            '"subpaths": ["knowledge/mattpocock/practices", '
            '"knowledge/mattpocock/artifacts"]}'
        )
        source = load_kb_source(cfg)
        self.assertEqual(source["kb"], "dividedby/agent-research")
        self.assertEqual(
            source["subpaths"],
            ["knowledge/mattpocock/practices", "knowledge/mattpocock/artifacts"],
        )

    def test_missing_config_is_safe_no_op(self):
        # No auto-discovery: an absent config reads nothing, never "everything
        # under the KB root".
        source = load_kb_source(self.base / "absent.json")
        self.assertIsNone(source["kb"])
        self.assertEqual(source["subpaths"], [])

    def test_absent_subpaths_key_defaults_to_empty(self):
        cfg = self.base / "kb-source.json"
        cfg.write_text('{"kb": "dividedby/agent-research"}')
        self.assertEqual(load_kb_source(cfg)["subpaths"], [])


class ReadKbTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _note(self, subpath, name, text):
        d = self.root / subpath
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text)

    def test_reads_md_notes_from_listed_subpaths(self):
        self._note("knowledge/mattpocock/practices", "index.md", "# practices")
        self._note("knowledge/mattpocock/practices", "tdd.md", "red-green-refactor")
        notes = read_kb(self.root, ["knowledge/mattpocock/practices"])
        self.assertEqual(
            [(n["subpath"], n["name"]) for n in notes],
            [
                ("knowledge/mattpocock/practices", "index.md"),
                ("knowledge/mattpocock/practices", "tdd.md"),
            ],
        )
        self.assertEqual(notes[1]["text"], "red-green-refactor")

    def test_records_carry_subject_and_category_axes(self):
        # The two domain axes the integration map is built on are first-class on
        # each record — consumers never re-parse the path.
        self._note("knowledge/mattpocock/practices", "tdd.md", "")
        self._note("knowledge/humanlayer/artifacts", "agent.md", "")
        notes = read_kb(
            self.root,
            ["knowledge/mattpocock/practices", "knowledge/humanlayer/artifacts"],
        )
        by_name = {n["name"]: n for n in notes}
        self.assertEqual(
            (by_name["tdd.md"]["subject"], by_name["tdd.md"]["category"]),
            ("mattpocock", "practices"),
        )
        self.assertEqual(
            (by_name["agent.md"]["subject"], by_name["agent.md"]["category"]),
            ("humanlayer", "artifacts"),
        )

    def test_non_conforming_subpath_leaves_axes_none(self):
        # A subpath without the knowledge/<subject>/<category> shape still reads,
        # but the axes it can't supply are None rather than a wrong guess.
        self._note("flat", "note.md", "")
        notes = read_kb(self.root, ["flat"])
        self.assertEqual((notes[0]["subject"], notes[0]["category"]), (None, "flat"))

    def test_subject_on_disk_but_not_listed_is_never_read(self):
        # No auto-discovery: a subject dir present under the KB root but absent
        # from the configured subpaths is never read.
        self._note("knowledge/mattpocock/practices", "tdd.md", "listed")
        self._note("knowledge/secret-subject/practices", "leak.md", "private")
        notes = read_kb(self.root, ["knowledge/mattpocock/practices"])
        self.assertEqual([n["name"] for n in notes], ["tdd.md"])

    def test_missing_subpath_is_skipped_not_crashed(self):
        # A configured subject the KB does not yet carry is skipped, not fatal.
        self._note("knowledge/mattpocock/practices", "tdd.md", "here")
        notes = read_kb(
            self.root,
            ["knowledge/humanlayer/practices", "knowledge/mattpocock/practices"],
        )
        self.assertEqual([n["name"] for n in notes], ["tdd.md"])

    def test_only_md_files_are_read(self):
        self._note("knowledge/mattpocock/practices", "tdd.md", "note")
        (self.root / "knowledge/mattpocock/practices" / "raw.json").write_text("{}")
        notes = read_kb(self.root, ["knowledge/mattpocock/practices"])
        self.assertEqual([n["name"] for n in notes], ["tdd.md"])

    def test_notes_are_returned_in_stable_order_across_subpaths(self):
        # Stable (subpath, name) ordering so a re-run is a minimal diff, not a
        # reordered rewrite.
        self._note("knowledge/mattpocock/practices", "b.md", "")
        self._note("knowledge/mattpocock/practices", "a.md", "")
        self._note("knowledge/mattpocock/artifacts", "z.md", "")
        notes = read_kb(
            self.root,
            ["knowledge/mattpocock/practices", "knowledge/mattpocock/artifacts"],
        )
        self.assertEqual(
            [(n["subpath"], n["name"]) for n in notes],
            [
                ("knowledge/mattpocock/artifacts", "z.md"),
                ("knowledge/mattpocock/practices", "a.md"),
                ("knowledge/mattpocock/practices", "b.md"),
            ],
        )

    def test_no_subpaths_is_a_clean_no_op(self):
        self.assertEqual(read_kb(self.root, []), [])


if __name__ == "__main__":
    unittest.main()
