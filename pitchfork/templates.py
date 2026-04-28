"""
HTML page templates for /slides, /notes, /presenter, and /timer views.
"""

from pathlib import Path

_TMPL = Path(__file__).resolve().parent / "templates"


def _load(head_file: str, body_file: str, title: str) -> str:
    head = (_TMPL / head_file).read_text(encoding="utf-8").replace("{title}", title)
    body = (_TMPL / body_file).read_text(encoding="utf-8")
    return head + "\n" + body

# TODO: use the title (filename?) of the loaded slides.md for the page title
SLIDES_PAGE    = _load("head.html", "slides.html",    "Pitchfork")
NOTES_PAGE     = _load("head.html", "notes.html",     "Pitchfork Notes")
PRESENTER_PAGE = _load("head.html", "presenter.html", "Pitchfork Presenter")
TIMER_PAGE     = _load("head.html", "timer.html",     "Pitchfork Timer")
