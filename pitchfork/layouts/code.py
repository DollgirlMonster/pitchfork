"""
Code layout — optimised for slides where the majority of content is
inside fenced code blocks. Larger code font, minimal padding.
Auto-selected when more than 50% of lines (with at least 4 total) are
inside fenced code blocks.
"""


def match(slide) -> bool:
    stripped = slide.content.strip()
    lines = stripped.splitlines()
    total = len(lines)
    if total < 4:
        return False

    code_lines = 0
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            code_lines += 1

    return (code_lines / max(total, 1)) > 0.5


def html(slide, md) -> str:
    return f'<div class="slide-layout code">{md(slide.content)}</div>'
