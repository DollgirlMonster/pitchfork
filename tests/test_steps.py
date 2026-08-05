import tempfile
import unittest
from pathlib import Path

from pitchfork.parser import STEP_SENTINEL, Slide, mark_steps, parse_deck


class TestMarkSteps(unittest.TestCase):
    def test_bare_double_dash_becomes_a_step(self):
        body, count = mark_steps("one\n--\ntwo")
        self.assertEqual(1, count)
        self.assertIn(STEP_SENTINEL, body)
        self.assertNotIn("\n--\n", body)

    def test_counts_every_step(self):
        self.assertEqual(3, mark_steps("a\n--\nb\n--\nc\n--\nd")[1])

    def test_no_steps_leaves_body_untouched(self):
        body = "just some prose\nwith a line"
        self.assertEqual((body, 0), mark_steps(body))

    def test_leading_and_trailing_whitespace_allowed(self):
        self.assertEqual(1, mark_steps("a\n   --  \nb")[1])

    def test_arrow_comment_close_is_not_a_step(self):
        """`-->` on its own line"""
        self.assertEqual(0, mark_steps("<!-- MARK: Intro\n-->\n# Hi")[1])

    def test_em_dash_usage_midline_is_not_a_step(self):
        self.assertEqual(0, mark_steps("carousel slider -- pretty good but hard to style")[1])

    def test_triple_dash_is_not_a_step(self):
        """`---` slide break"""
        self.assertEqual(0, mark_steps("a\n---\nb")[1])

    def test_double_dash_inside_fenced_code_is_ignored(self):
        body = "text\n\n```bash\n--\ngit log --oneline\n```\n"
        self.assertEqual((body, 0), mark_steps(body))

    def test_step_outside_fence_still_found(self):
        body, count = mark_steps("```\n--\n```\n\nreal text\n--\nmore")
        self.assertEqual(1, count)

    def test_tilde_fences_respected(self):
        body = "~~~\n--\n~~~\n"
        self.assertEqual((body, 0), mark_steps(body))


class TestParseDeckSteps(unittest.TestCase):
    def test_steps_recorded_on_slide(self):
        slides = parse_deck("# Hi\n\n- a\n--\n- b\n")
        self.assertEqual(1, slides[0].steps)

    def test_slides_without_steps_report_zero(self):
        slides = parse_deck("# Hi\n\n---\n\n# Bye\n")
        self.assertEqual([0, 0], [s.steps for s in slides])

    def test_steps_work_inside_zones(self):
        """A build in ::left:: must not leak into ::right::."""
        slides = parse_deck("## T\n\n::left::\nA\n--\nB\n\n::right::\nC\n")
        slide = slides[0]
        self.assertEqual(1, slide.steps)
        self.assertIn(STEP_SENTINEL, slide.zones["left"])
        self.assertNotIn(STEP_SENTINEL, slide.zones["right"])

    def test_steps_do_not_disturb_notes_split(self):
        slides = parse_deck("- a\n--\n- b\n\n%%%\nspeaker notes\n")
        self.assertEqual(1, slides[0].steps)
        self.assertEqual("speaker notes", slides[0].notes)
        self.assertNotIn(STEP_SENTINEL, slides[0].notes)

    def test_steps_do_not_disturb_layout_marker(self):
        slides = parse_deck("::layout:body::\n- a\n--\n- b\n")
        self.assertEqual("body", slides[0].layout)
        self.assertEqual(1, slides[0].steps)

    def test_steps_do_not_disturb_chapter_marks(self):
        slides = parse_deck("<!-- MARK: Intro\n-->\n- a\n--\n- b\n")
        self.assertEqual("Intro", slides[0].chapter)
        self.assertEqual(1, slides[0].steps)


class TestStepsInPayload(unittest.TestCase):
    def test_payload_carries_step_count(self):
        from pitchfork.renderer import init_layouts, slides_to_json_payload

        with tempfile.TemporaryDirectory() as tmpdir:
            deck = Path(tmpdir) / "deck.md"
            deck.write_text("x")
            init_layouts(deck, default_layout="body")
            slides = parse_deck("- a\n--\n- b\n\n---\n\n# plain\n")
            payload = slides_to_json_payload(slides)
            self.assertEqual([1, 0], [p["steps"] for p in payload])

    def test_sentinel_survives_markdown_at_block_level(self):
        """The reveal marker must come out as a top-level comment node, not
        wrapped in a <p>, or the client can't attach steps to siblings."""
        from pitchfork.renderer import md

        out = md(f"- one\n\n{STEP_SENTINEL}\n\n- two\n")
        self.assertIn(STEP_SENTINEL, out)
        self.assertNotIn(f"<p>{STEP_SENTINEL}", out)


if __name__ == "__main__":
    unittest.main()
