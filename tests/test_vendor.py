import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pitchfork import vendor


# Every test patches vendor.fetch so nothing here touches the network.
def _fake_fetch(responses):
    """Build a fetch() stand-in backed by a {url: (body, content_type)} dict."""
    def fake(url, cache_dir=None):
        return responses.get(url)
    return fake


class TestInlineCssUrls(unittest.TestCase):
    def test_remote_font_becomes_data_uri(self):
        css = "@font-face { src: url(https://fonts.gstatic.com/s/a.woff2) format('woff2'); }"
        responses = {"https://fonts.gstatic.com/s/a.woff2": (b"WOFF2DATA", "font/woff2")}
        with patch.object(vendor, "fetch", _fake_fetch(responses)):
            out = vendor.inline_css_urls(css)
        self.assertIn("data:font/woff2;base64,", out)
        self.assertNotIn("fonts.gstatic.com", out)

    def test_falls_back_to_extension_when_no_content_type(self):
        css = "src: url('https://example.com/x.woff2');"
        with patch.object(vendor, "fetch", _fake_fetch({"https://example.com/x.woff2": (b"D", "")})):
            out = vendor.inline_css_urls(css)
        self.assertIn("data:font/woff2;base64,", out)

    def test_data_and_relative_urls_untouched(self):
        css = "a { background: url(data:image/png;base64,AAAA); } b { background: url(img/x.png); }"
        with patch.object(vendor, "fetch", _fake_fetch({})):
            out = vendor.inline_css_urls(css)
        self.assertEqual(css, out)

    def test_relative_url_resolved_against_base(self):
        css = "src: url(../fonts/a.woff2);"
        responses = {"https://cdn.example.com/fonts/a.woff2": (b"D", "font/woff2")}
        with patch.object(vendor, "fetch", _fake_fetch(responses)):
            out = vendor.inline_css_urls(css, base_url="https://cdn.example.com/css/main.css")
        self.assertIn("data:font/woff2;base64,", out)

    def test_unreachable_url_left_alone(self):
        css = "src: url(https://example.com/a.woff2);"
        with patch.object(vendor, "fetch", _fake_fetch({})):
            out = vendor.inline_css_urls(css)
        self.assertEqual(css, out)


class TestInlineCssImports(unittest.TestCase):
    def test_import_replaced_with_rules(self):
        css = "@import url('https://fonts.googleapis.com/css2?family=X');\nbody { color: red }"
        responses = {
            "https://fonts.googleapis.com/css2?family=X": (
                b"@font-face { font-family: X; src: url(https://f.gstatic.com/x.woff2); }",
                "text/css",
            ),
            "https://f.gstatic.com/x.woff2": (b"FONT", "font/woff2"),
        }
        with patch.object(vendor, "fetch", _fake_fetch(responses)):
            out = vendor.inline_css_imports(css)
        self.assertNotIn("@import", out)
        self.assertIn("font-family: X", out)
        # Nested url() inside the imported sheet is inlined too.
        self.assertIn("data:font/woff2;base64,", out)
        self.assertIn("body { color: red }", out)

    def test_bare_string_import_form(self):
        css = '@import "https://example.com/a.css";'
        with patch.object(vendor, "fetch", _fake_fetch({"https://example.com/a.css": (b"p{}", "text/css")})):
            out = vendor.inline_css_imports(css)
        self.assertEqual("p{}", out)

    def test_local_import_untouched(self):
        css = '@import url("local.css");'
        with patch.object(vendor, "fetch", _fake_fetch({})):
            self.assertEqual(css, vendor.inline_css_imports(css))

    def test_import_with_media_query_suffix(self):
        css = '@import url("https://example.com/a.css") screen;'
        with patch.object(vendor, "fetch", _fake_fetch({"https://example.com/a.css": (b"p{}", "text/css")})):
            out = vendor.inline_css_imports(css)
        self.assertNotIn("@import", out)


class TestInlineHeadTags(unittest.TestCase):
    def test_stylesheet_link_inlined(self):
        head = '<link rel="stylesheet" href="https://cdn.example.com/a.css">'
        with patch.object(vendor, "fetch", _fake_fetch({"https://cdn.example.com/a.css": (b"p{color:red}", "text/css")})):
            out = vendor.inline_head_tags(head)
        self.assertIn("<style>", out)
        self.assertIn("p{color:red}", out)
        self.assertNotIn("<link", out)

    def test_non_stylesheet_link_untouched(self):
        head = '<link rel="preconnect" href="https://fonts.gstatic.com">'
        with patch.object(vendor, "fetch", _fake_fetch({})):
            self.assertEqual(head, vendor.inline_head_tags(head))

    def test_script_src_inlined(self):
        head = '<script src="https://cdn.example.com/hl.js"></script>'
        with patch.object(vendor, "fetch", _fake_fetch({"https://cdn.example.com/hl.js": (b"var x=1;", "text/javascript")})):
            out = vendor.inline_head_tags(head)
        self.assertIn("var x=1;", out)
        self.assertNotIn("src=", out)

    def test_closing_script_tag_in_payload_is_escaped(self):
        """A fetched script containing "</script>" must not end our block early."""
        head = '<script src="https://cdn.example.com/a.js"></script>'
        payload = b'var s = "</script>";'
        with patch.object(vendor, "fetch", _fake_fetch({"https://cdn.example.com/a.js": (payload, "text/javascript")})):
            out = vendor.inline_head_tags(head)
        self.assertIn("<\\/script>", out)
        # Exactly one real closing tag remains: the one we wrote.
        self.assertEqual(1, out.count("</script>"))

    def test_unreachable_assets_keep_their_tags(self):
        head = '<script src="https://cdn.example.com/a.js"></script>'
        with patch.object(vendor, "fetch", _fake_fetch({})):
            self.assertEqual(head, vendor.inline_head_tags(head))


class TestFetchCache(unittest.TestCase):
    def test_cache_hit_avoids_network(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Path(tmpdir)
            url = "https://example.com/a.woff2"

            with patch.object(vendor, "urlopen") as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b"BODY"
                mock_open.return_value.__enter__.return_value.headers = {"Content-Type": "font/woff2"}
                first = vendor.fetch(url, cache)
                self.assertEqual((b"BODY", "font/woff2"), first)
                self.assertEqual(1, mock_open.call_count)

            # Second call is served from disk — no urlopen at all.
            with patch.object(vendor, "urlopen") as mock_open:
                second = vendor.fetch(url, cache)
                self.assertEqual((b"BODY", "font/woff2"), second)
                mock_open.assert_not_called()

class TestFailureHandling(unittest.TestCase):
    """One bad URL must not disable vendoring for everything behind it."""

    def setUp(self):
        vendor.begin_run()
        self.addCleanup(vendor.begin_run)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name)

    def test_stale_link_does_not_stop_later_fetches(self):
        """A 404 is about that URL, not the network — the export shouldn't lose
        every other font because one link went stale."""
        import urllib.error

        def responses(req, timeout=None):
            if "stale" in req.full_url:
                raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
            mock = MagicMock()
            mock.__enter__.return_value.read.return_value = b"OK"
            mock.__enter__.return_value.headers = {"Content-Type": "font/woff2"}
            return mock

        with patch.object(vendor, "urlopen", side_effect=responses):
            self.assertIsNone(vendor.fetch("https://example.com/stale.woff2", self.cache))
            self.assertEqual((b"OK", "font/woff2"), vendor.fetch("https://example.com/good.woff2", self.cache))

        self.assertEqual([("https://example.com/stale.woff2", "HTTP 404")], vendor.last_failures())

    def test_dns_failure_does_not_stop_later_fetches(self):
        """DNS failures return in milliseconds, so there's nothing to save by
        giving up on the rest."""
        import urllib.error

        def responses(req, timeout=None):
            if "bad" in req.full_url:
                raise urllib.error.URLError("Name or service not known")
            mock = MagicMock()
            mock.__enter__.return_value.read.return_value = b"OK"
            mock.__enter__.return_value.headers = {"Content-Type": "font/woff2"}
            return mock

        with patch.object(vendor, "urlopen", side_effect=responses):
            self.assertIsNone(vendor.fetch("https://bad.example/a.woff2", self.cache))
            self.assertIsNotNone(vendor.fetch("https://ok.example/b.woff2", self.cache))

    def test_cached_assets_still_served_after_a_timeout(self):
        """A timeout stops new requests, not the disk cache."""
        mock = MagicMock()
        mock.__enter__.return_value.read.return_value = b"CACHED"
        mock.__enter__.return_value.headers = {"Content-Type": "font/woff2"}
        with patch.object(vendor, "urlopen", return_value=mock):
            vendor.fetch("https://example.com/warm.woff2", self.cache)

        with patch.object(vendor, "urlopen", side_effect=TimeoutError("nope")):
            vendor.fetch("https://example.com/cold.woff2", self.cache)
            self.assertEqual((b"CACHED", "font/woff2"),
                             vendor.fetch("https://example.com/warm.woff2", self.cache))

    def test_begin_run_clears_previous_failures(self):
        with patch.object(vendor, "urlopen", side_effect=TimeoutError("nope")):
            vendor.fetch("https://example.com/a.woff2", self.cache)
        self.assertTrue(vendor.last_failures())
        vendor.begin_run()
        self.assertEqual([], vendor.last_failures())


class TestVendorAssets(unittest.TestCase):
    def test_reports_bytes_added(self):
        head = '<script src="https://cdn.example.com/a.js"></script>'
        css_parts = ["body { color: red }", "p { color: blue }"]
        responses = {"https://cdn.example.com/a.js": (b"x" * 500, "text/javascript")}
        with patch.object(vendor, "fetch", _fake_fetch(responses)):
            out_head, out_css_parts, added = vendor.vendor_assets(head, css_parts)
        self.assertGreater(added, 400)
        self.assertEqual(css_parts, out_css_parts)
        self.assertIn("x" * 500, out_head)

    def test_each_part_vendored_independently(self):
        """A leading @import in one CSS block shouldn't need to be first in
        the whole document — each block is its own stylesheet."""
        css_parts = [
            "body { color: red }",
            '@import url("https://fonts.googleapis.com/css2?family=X");',
        ]
        responses = {
            "https://fonts.googleapis.com/css2?family=X": (b"p{}", "text/css"),
        }
        with patch.object(vendor, "fetch", _fake_fetch(responses)):
            _, out_css_parts, _ = vendor.vendor_assets("", css_parts)
        self.assertEqual("body { color: red }", out_css_parts[0])
        self.assertEqual("p{}", out_css_parts[1])


if __name__ == "__main__":
    unittest.main()
