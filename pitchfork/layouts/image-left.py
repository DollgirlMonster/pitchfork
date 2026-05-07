"""
Image-left layout — image on the left, text on the right.
Auto-selected when a markdown image precedes the slide's text content.
"""
import re

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")


def match(slide) -> bool:
    clean = _COMMENT_RE.sub("", slide.content)
    images = _IMAGE_RE.findall(clean)
    if len(images) != 1:
        return False
    img_match = _IMAGE_RE.search(clean)
    before = clean[: img_match.start()].strip()
    after = clean[img_match.end() :].strip()
    return not before and bool(after)


def html(slide, md) -> str:
    img_match = _IMAGE_RE.search(slide.content)
    if img_match:
        img = md(img_match.group(0))
        text_body = md(slide.content.replace(img_match.group(0), "").strip())
        return (
            '<div class="slide-layout image-left">'
            f'<div class="image-img">{img}</div>'
            f'<div class="image-text">{text_body}</div>'
            "</div>"
        )
    # Fallback
    return f'<div class="slide-layout body">{md(slide.content)}</div>'
