import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pitchfork.cli import find_deck


class TestFindDeckOrdering(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir_path = Path(self.tmpdir.name)
        # Create required .pitchfork sidecar to enable auto-detection
        (self.tmpdir_path / ".pitchfork").write_text("[deck]\n")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_find_deck_sorts_files_naturally(self):
        # Create decks out of lexical order
        (self.tmpdir_path / "Week 10.md").write_text("# Week 10")
        (self.tmpdir_path / "Week 2.md").write_text("# Week 2")
        (self.tmpdir_path / "Introduction.md").write_text("# Intro")

        # Choose the first option, which should be "Introduction.md" after natural sorting
        with mock.patch("builtins.input", return_value="1"):
            out = io.StringIO()
            with mock.patch("sys.stdout", out):
                selected = find_deck(self.tmpdir_path)

        self.assertEqual(selected.name, "Introduction.md")
        self.assertIn("1. Introduction.md", out.getvalue())
        # Ensure Week 2 comes before Week 10 in the listing
        listing = out.getvalue().splitlines()
        week_lines = [l for l in listing if "Week" in l]
        self.assertEqual(week_lines, ["  2. Week 2.md", "  3. Week 10.md"])


if __name__ == "__main__":
    unittest.main()
