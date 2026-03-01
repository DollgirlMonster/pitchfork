"""
Body layout — the default fallback. Renders plain markdown content.
match() always returns False because this layout is used as the
explicit fallback in renderer.py, not through auto-selection.
"""


def match(slide) -> bool:
    return False


def html(slide, md) -> str:
    return f'<div class="slide-layout body">{md(slide.content)}</div>'
