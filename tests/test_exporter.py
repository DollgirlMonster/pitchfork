import unittest
import tempfile
from pathlib import Path

from pitchfork.exporter import (
    load_config,
    _rewrite_local_images_to_data_uri,
    export_deck,
)


class TestExporter(unittest.TestCase):
    def test_load_config_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = load_config(Path(tmpdir) / "deck.md")
            self.assertEqual(cfg, {})

    def test_load_config_sidecar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            sidecar = tmpdir / ".pitchfork"
            sidecar.write_text("[deck]\ndefault_layout = \"body\"\n")
            cfg = load_config(tmpdir / "deck.md")
            self.assertIn("deck", cfg)

    def test_rewrite_local_images_to_data_uri(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            img = tmpdir / "img.png"
            img.write_bytes(b"PNGDATA")
            html = '<img src="img.png"> <img src="http://example.com/x.png">'
            out = _rewrite_local_images_to_data_uri(html, tmpdir)
            self.assertIn("data:image/png;base64", out)
            self.assertIn("http://example.com/x.png", out)

    def test_export_deck_html_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            deck = tmpdir / "deck.md"
            deck.write_text("# Slide\n\nContent")
            # Export to HTML
            export_deck(deck, html=True)
            out = deck.with_suffix(".html")
            self.assertTrue(out.exists())
            content = out.read_text(encoding="utf-8")
            self.assertIn("<html", content)
            self.assertIn("Slide", content)

    def test_overflow_shrink_js_uses_ratio_scaling(self):
        from pitchfork.exporter import _OVERFLOW_SHRINK_JS
        self.assertIn("inner.scrollWidth", _OVERFLOW_SHRINK_JS)
        self.assertIn("inner.scrollHeight", _OVERFLOW_SHRINK_JS)
        self.assertIn("clientW / scrollW", _OVERFLOW_SHRINK_JS)
        self.assertIn("clientH / scrollH", _OVERFLOW_SHRINK_JS)
        self.assertIn("minScale = 0.1", _OVERFLOW_SHRINK_JS)

    def test_export_css_wraps_pre_blocks(self):
        from pitchfork.exporter import export_deck
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            deck = tmpdir / "deck.md"
            deck.write_text("# Slide\n\n```js\nconst longLine = 'x'.repeat(500);\n```\n")
            export_deck(deck, html=True)
            out = deck.with_suffix(".html")
            content = out.read_text(encoding="utf-8")
            self.assertIn("white-space: pre-wrap !important", content)
            self.assertIn("overflow-wrap: anywhere !important", content)
