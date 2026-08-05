"""
HTML page templates for /slides, /notes, /presenter, and /timer views.
"""

from pathlib import Path

_TMPL = Path(__file__).resolve().parent / "templates"

# Navigation/helper functions shared by all views
_SHARED_NAV_JS = (_TMPL / "slide-controls.js").read_text(encoding="utf-8")
def _load(head_file: str, body_file: str, title: str, shared_nav_js: bool = False) -> str:
    head = (_TMPL / head_file).read_text(encoding="utf-8").replace("{title}", title)
    body = (_TMPL / body_file).read_text(encoding="utf-8")
    if shared_nav_js:
        # Prepend as its own <script> block ahead of the page's own script.
        body = body.replace("<script>", f"<script>\n{_SHARED_NAV_JS}\n</script>\n<script>", 1)
    return head + "\n" + body

# TODO: use the title (filename?) of the loaded slides.md for the page title
SLIDES_PAGE    = _load("head.html", "slides.html",    "Pitchfork",           shared_nav_js=True)
NOTES_PAGE     = _load("head.html", "notes.html",     "Pitchfork Notes",     shared_nav_js=True)
PRESENTER_PAGE = _load("head.html", "presenter.html", "Pitchfork Presenter", shared_nav_js=True)
TIMER_PAGE     = _load("head.html", "timer.html",     "Pitchfork Timer")
