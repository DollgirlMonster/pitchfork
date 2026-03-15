import unittest
from pitchfork.parser import (
    detect_layout,
    parse_zones,
    parse_deck,
    Slide,
)


class TestParser(unittest.TestCase):
    def test_parse_zones_no_markers(self):
        content = "# Title\nSome text"
        cleaned, zones = parse_zones(content)
        self.assertEqual(cleaned, content)
        self.assertEqual(zones, {})

    def test_parse_zones_multiple(self):
        content = """# Title\n
::left::\nLeft side\n::right::\nRight side\n"""
        cleaned, zones = parse_zones(content)
        self.assertEqual(cleaned, "# Title")
        self.assertEqual(zones, {"left": "Left side", "right": "Right side"})

    def test_detect_layout_title_and_section(self):
        self.assertEqual(detect_layout("# Title", {}), "title")
        self.assertEqual(detect_layout("# One\n# Two\n# Three", {}), "section")

    def test_detect_layout_two_column_via_zones(self):
        self.assertEqual(detect_layout("", {"left": "a", "right": "b"}), "two-column")

    def test_detect_layout_code(self):
        content = """```\nline1\nline2\nline3\nline4\n```"""
        self.assertEqual(detect_layout(content, {}), "code")

    def test_detect_layout_image_right(self):
        self.assertEqual(detect_layout("Text ![alt](img.png)", {}), "image-right")

    def test_detect_layout_none(self):
        self.assertIsNone(detect_layout("Just a bunch of text", {}))

    def test_parse_deck_explicit_layout_and_notes(self):
        md = """# slide: code\n```\nprint('hi')\n```\n%%%\nNotes here\n"""
        slides = parse_deck(md, default_layout="body")
        self.assertEqual(len(slides), 1)
        slide = slides[0]
        self.assertEqual(slide.layout, "code")
        self.assertIn("print('hi')", slide.content)
        self.assertEqual(slide.notes, "Notes here")

    def test_parse_deck_default_layout(self):
        md = "# Just text"
        slides = parse_deck(md, default_layout="body")
        self.assertEqual(len(slides), 1)
        self.assertEqual(slides[0].layout, "title")
