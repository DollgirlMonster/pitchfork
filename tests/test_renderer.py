import unittest
import tempfile
from pathlib import Path

from pitchfork.renderer import md, render_slide_html, slides_to_json_payload, init_layouts
from pitchfork.parser import Slide


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
