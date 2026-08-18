import tempfile
import unittest
from pathlib import Path

from pitchfork.server import PitchforkServer, parse_duration


class TestParseDuration(unittest.TestCase):
    def test_ms_and_seconds(self):
        self.assertEqual(parse_duration("5m30s"), 330)
        self.assertEqual(parse_duration("5m"), 300)
        self.assertEqual(parse_duration("100s"), 100)
        self.assertEqual(parse_duration("50m30s"), 3030)

    def test_fallback_seconds(self):
        self.assertEqual(parse_duration("42"), 42)
        self.assertEqual(parse_duration("  42  "), 42)

    def test_invalid_returns_none(self):
        self.assertIsNone(parse_duration(""))
        self.assertIsNone(parse_duration(None))
        self.assertIsNone(parse_duration("abc"))


class TestServerStatic(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir_path = Path(self.tmpdir.name)
        self.deck_path = self.tmpdir_path / "deck.md"
        self.deck_path.write_text("# Deck")
        self.css_path = self.tmpdir_path / "styles.css"
        self.css_path.write_text("body { background: #000; }")
        self.server = PitchforkServer(self.deck_path, self.css_path, host="localhost", port=1234)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_inject_replaces_tokens(self):
        self.server.set_slides_json("[{}]")
        self.server.set_chapters_json('[{"index":0,"title":"Intro"}]')
        html = "<html>__SLIDES_JSON__ __CHAPTERS_JSON__ __WS_PORT__</html>"
        out = self.server._inject(html)
        self.assertIn(b"[{}]", out)
        self.assertIn(b'"Intro"', out)
        self.assertIn(b"1235", out)  # port + 1

    def test_serve_static_styles_css(self):
        body, ct = self.server._serve_static("/styles.css")
        self.assertEqual(ct, "text/css")
        self.assertIn(b"background", body)

    def test_serve_static_pitchfork_css(self):
        body, ct = self.server._serve_static("/pitchfork.css")
        self.assertEqual(ct, "text/css")
        self.assertTrue(body.startswith(b"/*"))

    def test_serve_static_deck_file(self):
        (self.tmpdir_path / "foo.txt").write_text("hello")
        body, ct = self.server._serve_static("/foo.txt")
        self.assertEqual(ct, "application/octet-stream")
        self.assertEqual(body, b"hello")

    def test_serve_static_prevents_directory_traversal(self):
        self.assertIsNone(self.server._serve_static("/../etc/passwd"))


class _FakeReader:
    def __init__(self, data: bytes):
        self._data = data

    async def read(self, n):
        return self._data


class _FakeWriter:
    def __init__(self):
        self.chunks = []

    def write(self, data):
        self.chunks.append(data)

    async def drain(self):
        pass

    def close(self):
        pass

    async def wait_closed(self):
        pass

    @property
    def response(self):
        return b"".join(self.chunks)


class TestServerChaptersEndpoint(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        tmpdir_path = Path(self.tmpdir.name)
        deck_path = tmpdir_path / "deck.md"
        deck_path.write_text("# Deck")
        css_path = tmpdir_path / "styles.css"
        css_path.write_text("body {}")
        self.server = PitchforkServer(deck_path, css_path, host="localhost", port=1234)

    def tearDown(self):
        self.tmpdir.cleanup()

    async def test_chapters_json_endpoint(self):
        self.server.set_chapters_json('[{"index":0,"title":"Intro"}]')
        reader = _FakeReader(b"GET /chapters.json HTTP/1.1\r\nHost: localhost\r\n\r\n")
        writer = _FakeWriter()
        await self.server._http_handler(reader, writer)
        self.assertIn(b"Content-Type: application/json", writer.response)
        self.assertIn(b'[{"index":0,"title":"Intro"}]', writer.response)


if __name__ == "__main__":
    unittest.main()
