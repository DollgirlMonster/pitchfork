import unittest

from pitchfork.server import parse_duration


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


if __name__ == "__main__":
    unittest.main()
