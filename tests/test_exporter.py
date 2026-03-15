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
