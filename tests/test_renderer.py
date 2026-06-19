import unittest
import tempfile
from pathlib import Path

from pitchfork.renderer import md, render_slide_html, slides_to_json_payload, init_layouts
from pitchfork.parser import Slide, parse_deck


class TestRenderer(unittest.TestCase):
    def test_md_basic(self):
        self.assertIn("<em>", md("*em*"))

    def test_render_slide_html_fallback(self):
        # Use a layout name that doesn't exist; should fall back to body layout
        slide = Slide(index=0, layout="does-not-exist", content="# Hi", notes="")
        html = render_slide_html(slide)
        self.assertIn("slide-layout body", html)
        self.assertIn("<h1>Hi</h1>", html)

    def test_render_slide_html_layout_error(self):
        # Inject a layout that raises to ensure the error is captured gracefully
        from pitchfork import renderer

        class BadLayout:
            name = "bad"

            def match(self, slide):
                return True

            def html(self, slide, md_fn):
                raise RuntimeError("boom")

        # Temporarily replace global layouts list
        original = renderer._layouts
        renderer._layouts = [BadLayout()]
        try:
            slide = Slide(index=0, layout="bad", content="# Hi", notes="")
            out = render_slide_html(slide)
            self.assertIn("Layout error (bad)", out)
            self.assertIn("<h1>Hi</h1>", out)
        finally:
            renderer._layouts = original

    def test_slides_to_json_payload(self):
        slide = Slide(index=0, layout="title", content="# Title", notes="Note")
        payload = slides_to_json_payload([slide])
        self.assertEqual(len(payload), 1)
        self.assertIn("html", payload[0])
        self.assertIn("notes", payload[0])

    def test_init_layouts_loads_builtins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deck_path = Path(tmpdir) / "deck.md"
            deck_path.write_text("# Hi")
            # Ensure layouts load without errors
            init_layouts(deck_path)
            # Ensure we can render using a built-in layout
            slide = Slide(index=0, layout="title", content="# Title", notes="")
            html = render_slide_html(slide)
            self.assertIn("slide-layout title", html)

    # ── render-time auto-detection tests ──────────────────────────────────────
    # These cover the match() dispatch path (slide.layout is None).

    def setUp(self):
        """Load built-in layouts once for all auto-detection tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            deck_path = Path(tmpdir) / "deck.md"
            deck_path.write_text("# Hi")
            init_layouts(deck_path, default_layout="body")

    def _slide(self, content="", zones=None):
        return Slide(index=0, layout=None, content=content, notes="", zones=zones or {})

    def test_auto_detect_title_layout(self):
        slide = self._slide("# My Title")
        html = render_slide_html(slide)
        self.assertIn("slide-layout title", html)

    def test_auto_detect_section_layout(self):
        slide = self._slide("# Only\n# More\n# Three")
        html = render_slide_html(slide)
        self.assertIn("slide-layout section", html)

    def test_auto_detect_two_column_layout(self):
        slide = self._slide(zones={"left": "Left", "right": "Right"})
        html = render_slide_html(slide)
        self.assertIn("slide-layout two-column", html)

    def test_auto_detect_code_layout(self):
        content = "```\nline1\nline2\nline3\nline4\n```"
        slide = self._slide(content)
        html = render_slide_html(slide)
        self.assertIn("slide-layout code", html)

    def test_auto_detect_image_right_layout(self):
        slide = self._slide("Text ![alt](img.png)")
        html = render_slide_html(slide)
        self.assertIn("slide-layout image-right", html)

    def test_auto_detect_image_left_layout(self):
        slide = self._slide("![alt](img.png) text after")
        html = render_slide_html(slide)
        self.assertIn("slide-layout image-left", html)

    def test_auto_detect_falls_back_to_default_layout(self):
        slide = self._slide("Just a bunch of prose text that matches nothing.")
        html = render_slide_html(slide)
        self.assertIn("slide-layout body", html)

    def test_auto_detect_custom_layout_match_invoked(self):
        """A custom layout's match() must be called during render-time dispatch."""
        from pitchfork import renderer
        from pitchfork.layout_loader import Layout

        custom = Layout(
            name="custom-test",
            match=lambda slide: "CUSTOM" in slide.content,
            html=lambda slide, md_fn: '<div class="slide-layout custom-test">hit</div>',
            source=Path(__file__),
        )
        original = renderer._layouts[:]
        renderer._layouts = [custom] + original
        try:
            slide = self._slide("CUSTOM content here")
            html = render_slide_html(slide)
            self.assertIn("slide-layout custom-test", html)
        finally:
            renderer._layouts = original

    def test_parse_and_render_two_column_end_to_end(self):
        """Full pipeline: parse produces layout=None; render resolves two-column via match()."""
        src = "::left::\nLeft content\n::right::\nRight content"
        slides = parse_deck(src)
        self.assertIsNone(slides[0].layout, "parse_deck must not pre-resolve layout")
        html = render_slide_html(slides[0])
        self.assertIn("slide-layout two-column", html)
        self.assertIn("Left content", html)
        self.assertIn("Right content", html)

    def test_parse_and_render_title_end_to_end(self):
        src = "# My Deck Title"
        slides = parse_deck(src)
        self.assertIsNone(slides[0].layout)
        html = render_slide_html(slides[0])
        self.assertIn("slide-layout title", html)

    def test_default_layout_respected_when_nothing_matches(self):
        """init_layouts default_layout param must propagate to fallback resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            deck_path = Path(tmpdir) / "deck.md"
            deck_path.write_text("# Hi")
            init_layouts(deck_path, default_layout="body")
        slide = self._slide("Prose that matches no layout.")
        html = render_slide_html(slide)
        self.assertIn("slide-layout body", html)

