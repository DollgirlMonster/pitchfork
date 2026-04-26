import unittest
import tempfile
from pathlib import Path

from pitchfork.exporter import (
    load_config,
    _embed_local_images,
    _MEASURE_SCALE_JS,
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

    def test_embed_local_images_to_data_uri(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            img = tmpdir / "img.png"
            img.write_bytes(b"PNGDATA")
            html = '<img src="img.png"> <img src="http://example.com/x.png">'
            out = _embed_local_images(html, tmpdir)
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

    def test_measure_scale_js_has_expected_tokens(self):
        self.assertIn("inner.scrollWidth", _MEASURE_SCALE_JS)
        self.assertIn("inner.scrollHeight", _MEASURE_SCALE_JS)
        self.assertIn("scaleW", _MEASURE_SCALE_JS)
        self.assertIn("scaleH", _MEASURE_SCALE_JS)
        self.assertIn("Math.max(fit, 0.1)", _MEASURE_SCALE_JS)

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
