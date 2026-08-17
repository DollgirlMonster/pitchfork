import tempfile
import unittest
from pathlib import Path

from pitchfork.layout_loader import Layout, _wants_deck, load_layouts, user_layouts_dir
from pitchfork.parser import Slide, chapters_of, parse_deck
from pitchfork.renderer import init_deck, init_layouts, render_slide_html


class TestWantsDeck(unittest.TestCase):
    def test_two_arg_layout_does_not_want_deck(self):
        self.assertFalse(_wants_deck(lambda slide, md: ""))

    def test_three_arg_layout_wants_deck(self):
        self.assertTrue(_wants_deck(lambda slide, md, deck: ""))

    def test_varargs_layout_wants_deck(self):
        self.assertTrue(_wants_deck(lambda *args: ""))

    def test_keyword_only_third_arg_does_not_count(self):
        """Only positional parameters count — deck is passed positionally."""
        self.assertFalse(_wants_deck(lambda slide, md, *, debug=False: ""))

    def test_builtin_without_signature_is_safe(self):
        self.assertFalse(_wants_deck(len))


class TestDispatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.deck_path = self.root / "deck.md"
        self.deck_path.write_text("# Hi")
        init_layouts(self.deck_path, cwd=self.root, default_layout="body")

    def _slide(self, content="x", **kw):
        return Slide(index=kw.pop("index", 0), layout=None, content=content, notes="", **kw)

    def test_two_arg_layout_called_with_two_args(self):
        """Existing layouts must keep working untouched."""
        from pitchfork import renderer

        seen = {}

        def html(slide, md):
            seen["argc"] = 2
            return "<div>two</div>"

        renderer._layouts = [Layout("t", lambda s: True, html, Path("t.py"), wants_deck=False)]
        render_slide_html(self._slide())
        self.assertEqual(2, seen["argc"])

    def test_three_arg_layout_receives_deck(self):
        from pitchfork import renderer

        captured = {}

        def html(slide, md, deck):
            captured["deck"] = deck
            return "<div>three</div>"

        renderer._layouts = [Layout("t", lambda s: True, html, Path("t.py"), wants_deck=True)]
        slides = [self._slide()]
        init_deck(slides, self.deck_path, {"vars": {"course": "UI/UX"}})
        render_slide_html(slides[0])

        deck = captured["deck"]
        self.assertEqual(self.deck_path, deck.path)
        self.assertEqual("UI/UX", deck.config["vars"]["course"])
        self.assertEqual(slides, deck.slides)

    def test_layout_error_is_reported_not_raised(self):
        from pitchfork import renderer

        def html(slide, md, deck):
            raise ValueError("boom")

        renderer._layouts = [Layout("t", lambda s: True, html, Path("t.py"), wants_deck=True)]
        init_deck([self._slide()], self.deck_path, {})
        out = render_slide_html(self._slide())
        self.assertIn("Layout error", out)
        self.assertIn("boom", out)


class TestChapters(unittest.TestCase):
    def test_chapters_of_picks_out_chapter_openers(self):
        source = (
            "<!-- MARK: Intro -->\n# One\n\n---\n\n# Two\n\n---\n\n<!-- MARK: Demo -->\n# Three\n"
        )
        chapters = chapters_of(parse_deck(source))
        self.assertEqual([(0, "Intro"), (2, "Demo")], [(c.index, c.title) for c in chapters])

    def test_deck_without_chapters(self):
        self.assertEqual([], chapters_of(parse_deck("# Only\n")))


class TestAgendaLayout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.deck_path = self.root / "deck.md"

    def _render(self, source, agenda_index):
        self.deck_path.write_text(source)
        init_layouts(self.deck_path, cwd=self.root, default_layout="body")
        slides = parse_deck(source)
        init_deck(slides, self.deck_path, {})
        return render_slide_html(slides[agenda_index])

    def test_agenda_lists_every_chapter(self):
        source = (
            "::layout:agenda::\n## Agenda\n\n---\n\n<!-- MARK: SEO -->\n# S\n\n"
            "---\n\n<!-- MARK: Analytics -->\n# A\n\n---\n\n<!-- MARK: Hosting -->\n# H\n"
        )
        out = self._render(source, 0)
        for title in ("SEO", "Analytics", "Hosting"):
            self.assertIn(title, out)
        self.assertIn("Agenda", out)  # the slide's own content is kept

    def test_agenda_omits_itself_when_it_opens_the_first_chapter(self):
        """An agenda slide that is itself the first MARK shouldn't list its own title."""
        source = (
            "::layout:agenda::\n<!-- MARK: Agenda -->\n## Agenda\n\n---\n\n"
            "<!-- MARK: SEO -->\n# S\n\n---\n\n<!-- MARK: Hosting -->\n# H\n"
        )
        out = self._render(source, 0)
        self.assertNotIn('data-state', out.split("<ol", 1)[0])  # sanity: list follows preamble
        self.assertEqual(1, out.count(">Agenda<"))  # heading only, not repeated as a list item
        self.assertIn("SEO", out)
        self.assertIn("Hosting", out)

    def test_agenda_before_any_chapter_marks_all_upcoming(self):
        source = (
            "::layout:agenda::\n\n---\n\n<!-- MARK: One -->\n# A\n\n---\n\n<!-- MARK: Two -->\n# B\n"
        )
        out = self._render(source, 0)
        self.assertEqual(2, out.count('data-state="upcoming"'))
        self.assertNotIn('data-state="current"', out)

    def test_revisited_agenda_marks_position(self):
        """An agenda dropped in mid-deck marks what's done and where you are."""
        source = (
            "<!-- MARK: One -->\n# A\n\n---\n\n<!-- MARK: Two -->\n# B\n\n"
            "---\n\n::layout:agenda::\n\n---\n\n<!-- MARK: Three -->\n# C\n"
        )
        out = self._render(source, 2)
        self.assertIn('data-state="done"', out)
        self.assertIn('data-state="current"', out)
        self.assertIn('data-state="upcoming"', out)
        # The agenda sits inside chapter Two, so One is done and Three is ahead.
        self.assertLess(out.index("One"), out.index("Two"))
        self.assertIn('is-current" data-state="current">Two', out)

    def test_agenda_without_chapters_explains_itself(self):
        out = self._render("::layout:agenda::\n## Agenda\n", 0)
        self.assertIn("MARK", out)

    def test_chapter_titles_are_escaped(self):
        source = "::layout:agenda::\n\n---\n\n<!-- MARK: A & <b>B</b> -->\n# X\n"
        out = self._render(source, 0)
        self.assertIn("&amp;", out)
        self.assertNotIn("<b>B</b>", out)

    def test_agenda_is_never_auto_selected(self):
        from pitchfork.layouts import agenda
        self.assertFalse(agenda.match(Slide(0, None, "## Agenda", "")))


class TestUserLayoutsDir(unittest.TestCase):
    def test_honours_xdg_config_home(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/xdg"}):
            self.assertEqual(Path("/tmp/xdg/pitchfork/_layouts"), user_layouts_dir())

    def test_defaults_to_dot_config(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(Path.home() / ".config/pitchfork/_layouts", user_layouts_dir())

    def test_user_layouts_load_below_project_but_above_builtin(self):
        import os
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            config_home = tmpdir / "config"
            user_dir = config_home / "pitchfork" / "_layouts"
            user_dir.mkdir(parents=True)
            # Shadows the built-in `title`, and adds a name nothing else has.
            (user_dir / "title.py").write_text(
                "def match(slide):\n    return False\n\ndef html(slide, md):\n    return '<div>user title</div>'\n"
            )
            (user_dir / "shared.py").write_text(
                "def match(slide):\n    return False\n\ndef html(slide, md):\n    return '<div>shared</div>'\n"
            )

            project = tmpdir / "project"
            project.mkdir()
            deck = project / "deck.md"
            deck.write_text("# Hi")

            with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config_home)}):
                layouts = load_layouts(deck, cwd=project)

            by_name = {l.name: l for l in layouts}
            self.assertIn("shared", by_name)
            # User-level title wins over the built-in of the same name.
            self.assertEqual(user_dir / "title.py", by_name["title"].source)

    def test_project_layouts_still_beat_user_layouts(self):
        import os
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            config_home = tmpdir / "config"
            user_dir = config_home / "pitchfork" / "_layouts"
            user_dir.mkdir(parents=True)
            (user_dir / "thing.py").write_text(
                "def match(slide):\n    return False\n\ndef html(slide, md):\n    return '<div>user</div>'\n"
            )

            project = tmpdir / "project"
            (project / "_layouts").mkdir(parents=True)
            (project / "_layouts" / "thing.py").write_text(
                "def match(slide):\n    return False\n\ndef html(slide, md):\n    return '<div>project</div>'\n"
            )
            deck = project / "deck.md"
            deck.write_text("# Hi")

            with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config_home)}):
                layouts = load_layouts(deck, cwd=project)

            thing = next(l for l in layouts if l.name == "thing")
            self.assertEqual(project / "_layouts" / "thing.py", thing.source)


if __name__ == "__main__":
    unittest.main()
