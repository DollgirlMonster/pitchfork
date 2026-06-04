"""
Renders Slide objects to HTML fragments using markdown + highlight.js.
Layout selection is handled by layout_loader.
"""
from pathlib import Path
from typing import List

import re
import html
import markdown
from pitchfork.layout_loader import Layout, load_layouts, pick_layout
from pitchfork.parser import Slide

# Module-level layout list — populated by init_layouts() at startup.
_layouts: List[Layout] = []
# Fallback body layout used when nothing else matches.
_body_layout: Layout = Layout(
    name="body",
    match=lambda slide: False,
    html=lambda slide, md_fn: f'<div class="slide-layout body">{md_fn(slide.content)}</div>',
    source=Path(__file__),
)


def init_layouts(deck_path: Path) -> None:
    """Load (or reload) layouts for the given deck. Call at startup and on file-change."""
    global _layouts
    _layouts = load_layouts(deck_path)


def md(text: str) -> str:
    """Convert markdown to HTML."""
    if not text:
        return ""

    result = markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br", "sane_lists", "pymdownx.tasklist"],
    )

    # Problem: nl2br doesn't know about HTML structure, so it inserts <br> on
    # every newline including inside raw <script>/<style> blocks, causing a 
    # syntax error when the browser tries to parse <br> as JS or CSS
    # Solution: after rendering, strip <br> back to newlines inside those blocks.
    # Fenced code examples are safe to ignore here because the fenced_code
    # extension already HTML-escapes them to &lt;script&gt; before nl2br runs.
    def _remove_br(m: re.Match) -> str:
        return re.sub(r'<br\s*/?>', '\n', m.group(0))

    _SCRIPT_STYLE_BR_RE = re.compile(
        r'<(script|style)\b[^>]*>.*?</\1>',
        re.DOTALL | re.IGNORECASE,
    )

    return _SCRIPT_STYLE_BR_RE.sub(_remove_br, result)


_MD_QR_ANCHOR_RE = re.compile(
    r'(?i)<a\b[^>]*href=("|\')(?P<href>.*?)(?:\1)[^>]*>\s*(?:<(?:strong|b)>)?\s*qr\s*(?:</(?:strong|b)>)?\s*</a>'
)


def replace_qr_placeholders(html_text: str) -> str:
    """Replace `<a ...>QR</a>` anchors with `.pf-qr` placeholders.

    This is a separate step in the rendering pipeline so `md()` stays
    focused on markdown → HTML conversion.
    """

    def _repl(m):
        href = m.group('href').strip()
        href_esc = html.escape(href, quote=True)
        return f'<div class="pf-qr" data-value="{href_esc}" data-size="160"></div>'

    return _MD_QR_ANCHOR_RE.sub(_repl, html_text)


def render_slide_html(slide: Slide) -> str:
    """Render a slide's content area as an HTML fragment."""
    layout = pick_layout(_layouts, slide, explicit_name=slide.layout) or _body_layout
    try:
        html_out = layout.html(slide, md)
        return replace_qr_placeholders(html_out)
    except Exception as exc:
        return (
            f'<div class="slide-layout body error">'
            f"<p><strong>Layout error ({layout.name}):</strong> {exc}</p>"
            f"{replace_qr_placeholders(md(slide.content))}</div>"
        )


def render_notes_html(slide: Slide) -> str:
    if not slide.notes.strip():
        return '<div class="notes-empty">No notes for this slide.</div>'
    return f'<div class="notes-content">{replace_qr_placeholders(md(slide.notes))}</div>'


def slides_to_json_payload(slides: List[Slide]) -> List[Dict]:
    """Serialize slides to a JSON-safe list for WebSocket reload."""
    return [
        {
            "index": s.index,
            "layout": s.layout,
            "html": render_slide_html(s),
            "notes": render_notes_html(s),
            "chapter": s.chapter,
        }
        for s in slides
    ]


def chapters_json_payload(slides: List[Slide]) -> List[Dict]:
    """Return a compact [{index, title}] list for slides that open a new chapter."""
    return [
        {"index": s.index, "title": s.chapter}
        for s in slides
        if s.chapter is not None
    ]
