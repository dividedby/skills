import tempfile
import unittest
from pathlib import Path

from runbooks.lib.map_store import read_map, write_map


class MapStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "integration-map.md"

    def tearDown(self):
        self._tmp.cleanup()

    def test_write_creates_map_and_reports_changed(self):
        changed = write_map(self.path, "# Integration map\n\n- tdd ↔ red-green\n")
        self.assertTrue(changed)
        self.assertEqual(read_map(self.path), "# Integration map\n\n- tdd ↔ red-green\n")

    def test_rewriting_identical_content_reports_no_change(self):
        content = "# Integration map\n\n- tdd ↔ red-green\n"
        write_map(self.path, content)
        self.assertFalse(write_map(self.path, content))

    def test_changed_content_reports_changed(self):
        write_map(self.path, "# Integration map\n\n- tdd ↔ red-green\n")
        self.assertTrue(write_map(self.path, "# Integration map\n\n- tdd ↔ red-green-refactor\n"))

    def test_read_missing_map_is_none(self):
        self.assertIsNone(read_map(self.path))


if __name__ == "__main__":
    unittest.main()
