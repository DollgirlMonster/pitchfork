import unittest
from pitchfork.parser import (
    detect_layout,
    extract_marks,
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
        md = """::layout:code::
```
print('hi')
```
%%%
Notes here
"""
        slides = parse_deck(md, default_layout="body")
        self.assertEqual(len(slides), 1)
        slide = slides[0]
        self.assertEqual(slide.layout, "code")
        self.assertIn("print('hi')", slide.content)
        self.assertEqual(slide.notes, "Notes here")

    def test_parse_deck_explicit_layout_and_notes_new_marker(self):
        md = """::layout:code::
```
print('hi')
```
%%%
Notes here
"""
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

    # ── MARK / chapter tests ──────────────────────────────────

    def test_extract_marks_none(self):
        self.assertEqual(extract_marks("# No marks here"), [])

    def test_extract_marks_basic(self):
        src = "<!-- MARK: Intro -->\n# Slide"
        marks = extract_marks(src)
        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0][1], "Intro")

    def test_extract_marks_multiline_comment(self):
        # Confirm the multi-line variant used in VSCode (<!-- MARK: Foo\n-->) is caught
        src = "<!-- MARK: Query Loops\n-->\n## Slide"
        marks = extract_marks(src)
        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0][1], "Query Loops")

    def test_chapter_attached_to_containing_slide(self):
        # MARK inside a slide body names that slide, not the next one
        src = "# Slide zero\n\n---\n\n<!-- MARK: Chapter One -->\n## Slide one\n"
        slides = parse_deck(src)
        self.assertIsNone(slides[0].chapter)
        self.assertEqual(slides[1].chapter, "Chapter One")

    def test_chapter_none_when_no_marks(self):
        src = "# Slide A\n\n---\n\n## Slide B\n"
        slides = parse_deck(src)
        self.assertTrue(all(s.chapter is None for s in slides))

    def test_multiple_chapters(self):
        src = (
            "# Title\n\n---\n\n"
            "<!-- MARK: Part One -->\n## One\n\n---\n\n"
            "## One Inner\n\n---\n\n"
            "<!-- MARK: Part Two -->\n## Two\n"
        )
        slides = parse_deck(src)
        chapters = [(s.index, s.chapter) for s in slides if s.chapter]
        self.assertEqual(chapters, [(1, "Part One"), (3, "Part Two")])

    def test_last_mark_wins_in_chunk(self):
        src = "<!-- MARK: First -->\n<!-- MARK: Second -->\n## Slide\n"
        slides = parse_deck(src)
        self.assertEqual(slides[0].chapter, "Second")

    def test_slide_payload_includes_chapter(self):
        from pitchfork.renderer import slides_to_json_payload, init_layouts
        import tempfile, pathlib
        with tempfile.TemporaryDirectory() as d:
            deck = pathlib.Path(d) / "deck.md"
            deck.write_text("# Slide")
            init_layouts(deck)
        src = "<!-- MARK: Intro -->\n# Slide\n"
        slides = parse_deck(src)
        payload = slides_to_json_payload(slides)
        self.assertIn("chapter", payload[0])
        self.assertEqual(payload[0]["chapter"], "Intro")

    def test_chapters_json_payload(self):
        from pitchfork.renderer import chapters_json_payload
        src = (
            "# Title\n\n---\n\n"
            "<!-- MARK: Part One -->\n## One\n\n---\n\n"
            "<!-- MARK: Part Two -->\n## Two\n"
        )
        slides = parse_deck(src)
        chapters = chapters_json_payload(slides)
        self.assertEqual(chapters, [
            {"index": 1, "title": "Part One"},
            {"index": 2, "title": "Part Two"},
        ])
