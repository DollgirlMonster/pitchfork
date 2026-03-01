"""
Title layout — used for slides with only headings and no body text,
up to 2 heading lines. Centred, large type.
Auto-selected when there are 1–2 heading lines and no body lines.
"""


def match(slide) -> bool:
    lines = [l for l in slide.content.strip().splitlines() if l.strip()]
    heading_lines = [l for l in lines if l.startswith("#")]
    body_lines = [l for l in lines if not l.startswith("#")]
    return bool(heading_lines and not body_lines and len(heading_lines) <= 2)


def html(slide, md) -> str:
    return f'<div class="slide-layout title">{md(slide.content)}</div>'
