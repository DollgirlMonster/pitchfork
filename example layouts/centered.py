"""
    Centered body layout. Puts stuff in the center on-demand
"""


def match(slide) -> bool:
    return False


def html(slide, md) -> str:
    body = md(slide.content)
    highlight = md(slide.zones.get("highlight", ""))
    return (
        '<style>.slide-layout.centered * {text-align: center; margin-left: auto; margin-right: auto;}</style>' +
        '<div class="slide-layout body centered">' +
        body +
        "</div>"
    )
