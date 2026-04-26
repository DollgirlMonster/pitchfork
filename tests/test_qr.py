import unittest

from pitchfork import renderer
from pitchfork.parser import Slide


class TestQRPlaceholders(unittest.TestCase):
    def test_replace_qr_placeholders_basic(self):
        md_html = renderer.md('[QR](https://example.com)')
        out = renderer.replace_qr_placeholders(md_html)
        self.assertIn('class="pf-qr"', out)
        self.assertIn('data-value="https://example.com"', out)

    def test_replace_qr_with_strong(self):
        # Bold inside link typically renders as <a><strong>QR</strong></a>
        md_html = renderer.md('[**QR**](https://example.com)')
        out = renderer.replace_qr_placeholders(md_html)
        self.assertIn('class="pf-qr"', out)
        self.assertIn('data-value="https://example.com"', out)

    def test_render_slide_html_includes_placeholder(self):
        # Use a real Slide dataclass so layout.match() sees expected types
        slide = Slide(index=0, layout=None, content='[QR](https://example.com)', notes='', zones={})
        out = renderer.render_slide_html(slide)
        self.assertIn('class="pf-qr"', out)
        self.assertIn('data-value="https://example.com"', out)


if __name__ == '__main__':
    unittest.main()
