"""
Section layout — a single heading line used as a divider between sections.
Auto-selected when the slide is exactly one line starting with '# '.
"""


def match(slide) -> bool:
    lines = [l for l in slide.content.strip().splitlines() if l.strip()]
    return len(lines) == 1 and lines[0].startswith("# ")


def html(slide, md) -> str:
    return f'<div class="slide-layout section">{md(slide.content)}</div>'
