"""
Renders Slide objects to HTML fragments using markdown + highlight.js.
Layout selection is handled by layout_loader.
"""
from pathlib import Path
from typing import Dict, List

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
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br", "sane_lists", "pymdownx.tasklist"],
    )


def render_slide_html(slide: Slide) -> str:
    """Render a slide's content area as an HTML fragment."""
    layout = pick_layout(_layouts, slide, explicit_name=slide.layout) or _body_layout
    try:
        return layout.html(slide, md)
    except Exception as exc:
        return (
            f'<div class="slide-layout body error">'
            f"<p><strong>Layout error ({layout.name}):</strong> {exc}</p>"
            f"{md(slide.content)}</div>"
        )


def render_notes_html(slide: Slide) -> str:
    if not slide.notes.strip():
        return '<div class="notes-empty">No notes for this slide.</div>'
    return f'<div class="notes-content">{md(slide.notes)}</div>'


def slides_to_json_payload(slides: List[Slide]) -> List[Dict]:
    """Serialize slides to a JSON-safe list for WebSocket reload."""
    return [
        {
            "index": s.index,
            "layout": s.layout,
            "html": render_slide_html(s),
            "notes": render_notes_html(s),
        }
        for s in slides
    ]
