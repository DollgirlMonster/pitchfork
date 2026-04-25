import unittest

from pitchfork import renderer


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
        # Construct a minimal slide-like object expected by render_slide_html
        class SlideStub:
            def __init__(self, content):
                self.content = content
                self.notes = ''
                self.zones = []
                self.title = ''

        slide = SlideStub('[QR](https://example.com)')
        out = renderer.render_slide_html(slide)
        self.assertIn('class="pf-qr"', out)
        self.assertIn('data-value="https://example.com"', out)


if __name__ == '__main__':
    unittest.main()
