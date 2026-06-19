"""
Section layout — a single heading line used as a divider between sections.
Auto-selected when the slide has more than 2 heading lines and no body text.
"""
import re

_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)


def match(slide) -> bool:
    content = _COMMENT_RE.sub('', slide.content)
    lines = [l for l in content.strip().splitlines() if l.strip()]
    heading_lines = [l for l in lines if l.startswith("#")]
    body_lines = [l for l in lines if not l.startswith("#")]
    
    # title handles 1-2 headings; section handles 3+
    return bool(heading_lines and not body_lines and len(heading_lines) > 2)


def html(slide, md) -> str:
    return f'<div class="slide-layout section">{md(slide.content)}</div>'
