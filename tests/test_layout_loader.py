import unittest
import tempfile
from pathlib import Path

from pitchfork.layout_loader import load_layouts, pick_layout, Layout
from pitchfork.parser import Slide


class TestLayoutLoader(unittest.TestCase):
    def test_pick_layout_by_name(self):
        layouts = [
            Layout(name="a", match=lambda s: True, html=lambda s, md: "a", source=Path("/tmp/a.py")),
            Layout(name="b", match=lambda s: False, html=lambda s, md: "b", source=Path("/tmp/b.py")),
        ]
        slide = Slide(0, None, "", "")
        self.assertIs(pick_layout(layouts, slide, explicit_name="b"), layouts[1])
        self.assertIsNone(pick_layout(layouts, slide, explicit_name="missing"))

    def test_load_layouts_sidecar_overrides_builtins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            deck = tmpdir / "deck.md"
            deck.write_text("# Test")

            layouts_dir = tmpdir / "_layouts"
            layouts_dir.mkdir()
            custom = layouts_dir / "body.py"
            custom.write_text(
                "def match(slide):\n    return True\n\n"
                "def html(slide, md):\n    return '<div>custom</div>'\n"
            )

            layouts = load_layouts(deck)
            # First layout should be our custom one (same name as built-in)
            self.assertTrue(len(layouts) > 0)
            self.assertEqual(layouts[0].name, "body")
            self.assertEqual(layouts[0].source, custom)

    def test_load_layouts_ignores_invalid_layouts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            deck = tmpdir / "deck.md"
            deck.write_text("# Test")

            layouts_dir = tmpdir / "_layouts"
            layouts_dir.mkdir()
            invalid = layouts_dir / "invalid.py"
            invalid.write_text("# no match/html here\n")

            layouts = load_layouts(deck)
            self.assertFalse(any(l.source == invalid for l in layouts))
