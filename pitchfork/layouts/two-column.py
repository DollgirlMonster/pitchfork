"""
Two-column layout with optional preamble above the columns.
Auto-selected when the slide defines ::left:: or ::right:: zones.
"""


def match(slide) -> bool:
    return bool({"left", "right"} & set(slide.zones.keys()))


def html(slide, md) -> str:
    left = md(slide.zones.get("left", ""))
    right = md(slide.zones.get("right", ""))
    preamble = md(slide.content) if slide.content.strip() else ""
    preamble_html = f'<div class="slide-preamble">{preamble}</div>' if preamble else ""
    return (
        '<div class="slide-layout two-column">'
        + preamble_html
        + '<div class="columns">'
        + f'<div class="col col-left">{left}</div>'
        + f'<div class="col col-right">{right}</div>'
        + "</div></div>"
    )
