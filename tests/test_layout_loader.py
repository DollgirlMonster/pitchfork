import unittest
import tempfile
from pathlib import Path

from pitchfork.layout_loader import load_layouts, lookup_by_name, detect, resolve_layout, Layout
from pitchfork.parser import Slide


class TestLayoutLoader(unittest.TestCase):
    def test_lookup_by_name(self):
        layouts = [
            Layout(name="a", match=lambda s: True, html=lambda s, md: "a", source=Path("/tmp/a.py")),
            Layout(name="b", match=lambda s: False, html=lambda s, md: "b", source=Path("/tmp/b.py")),
        ]
        self.assertIs(lookup_by_name(layouts, "b"), layouts[1])
        self.assertIsNone(lookup_by_name(layouts, "missing"))

    def test_detect_returns_first_match(self):
        layouts = [
            Layout(name="a", match=lambda s: False, html=lambda s, md: "a", source=Path("/tmp/a.py")),
            Layout(name="b", match=lambda s: True, html=lambda s, md: "b", source=Path("/tmp/b.py")),
            Layout(name="c", match=lambda s: True, html=lambda s, md: "c", source=Path("/tmp/c.py")),
        ]
        slide = Slide(0, None, "", "")
        self.assertIs(detect(layouts, slide), layouts[1])

    def test_detect_returns_none_when_nothing_matches(self):
        layouts = [Layout(name="a", match=lambda s: False, html=lambda s, md: "a", source=Path("/tmp/a.py"))]
        slide = Slide(0, None, "", "")
        self.assertIsNone(detect(layouts, slide))

    def test_resolve_layout_explicit_name_wins(self):
        layouts = [
            Layout(name="a", match=lambda s: True, html=lambda s, md: "a", source=Path("/tmp/a.py")),
            Layout(name="b", match=lambda s: False, html=lambda s, md: "b", source=Path("/tmp/b.py")),
        ]
        slide = Slide(0, "b", "", "")
        self.assertIs(resolve_layout(layouts, slide, default_name="a"), layouts[1])

    def test_resolve_layout_explicit_miss_does_not_fall_through(self):
        """A typo'd ::layout:: marker must not get silently reinterpreted by auto-detect."""
        layouts = [Layout(name="a", match=lambda s: True, html=lambda s, md: "a", source=Path("/tmp/a.py"))]
        slide = Slide(0, "does-not-exist", "", "")
        self.assertIsNone(resolve_layout(layouts, slide, default_name="a"))

    def test_resolve_layout_falls_back_to_detect(self):
        layouts = [
            Layout(name="a", match=lambda s: False, html=lambda s, md: "a", source=Path("/tmp/a.py")),
            Layout(name="b", match=lambda s: True, html=lambda s, md: "b", source=Path("/tmp/b.py")),
        ]
        slide = Slide(0, None, "", "")
        self.assertIs(resolve_layout(layouts, slide, default_name="a"), layouts[1])

    def test_resolve_layout_falls_back_to_default_name(self):
        layouts = [Layout(name="a", match=lambda s: False, html=lambda s, md: "a", source=Path("/tmp/a.py"))]
        slide = Slide(0, None, "", "")
        self.assertIs(resolve_layout(layouts, slide, default_name="a"), layouts[0])

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
