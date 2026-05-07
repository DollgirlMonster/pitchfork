"""
Title layout — used for slides with only headings and no body text,
up to 2 heading lines. Centred, large type.
Auto-selected when there are 1–2 heading lines and no body lines.
"""
import re

_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)


def match(slide) -> bool:
    content = _COMMENT_RE.sub('', slide.content)
    lines = [l for l in content.strip().splitlines() if l.strip()]
    heading_lines = [l for l in lines if l.startswith("#")]
    body_lines = [l for l in lines if not l.startswith("#")]
    return bool(heading_lines and not body_lines and len(heading_lines) <= 2)


def html(slide, md) -> str:
    return f'<div class="slide-layout title">{md(slide.content)}</div>'
