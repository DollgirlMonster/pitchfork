"""
Image-right layout — text on the left, image floated to the right.
Auto-selected when the slide contains a markdown image.
"""
import re


def match(slide) -> bool:
    return bool(re.search(r"!\[.*?\]\(.*?\)", slide.content))


def html(slide, md) -> str:
    img_match = re.search(r"(!\[.*?\]\(.*?\))", slide.content)
    if img_match:
        img = md(img_match.group(1))
        text_body = md(slide.content.replace(img_match.group(1), "").strip())
        return (
            '<div class="slide-layout image-right">'
            f'<div class="image-text">{text_body}</div>'
            f'<div class="image-img">{img}</div>'
            "</div>"
        )
    # Fallback — image regex matched but md() didn't find it (shouldn't happen)
    return f'<div class="slide-layout body">{md(slide.content)}</div>'
