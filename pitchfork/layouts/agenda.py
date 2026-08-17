"""
Agenda layout
builds the running order from <!-- MARK: --> chapters,
so the agenda slide can't drift out of sync with the deck it describes.

Explicit only: put ::layout:agenda:: at the top of a slide. Anything you write
on the slide is rendered above the list, so you can provide your own headline

Agenda Layout only provides the list itself

    ::layout:agenda::
    ## Agenda

Drop the same slide in again between sections and it re-renders with your
current position marked: each item carries state as a class, so you can style it

    .pf-agenda-item.is-done       chapters already covered
    .pf-agenda-item.is-current    the chapter this slide sits in
    .pf-agenda-item.is-upcoming   still to come

"""
import html as _html


def match(slide) -> bool:
    # Never auto-selected: an agenda is a deliberate slide, and the chapter
    # list looks nothing like the slide's own content.
    return False


def html(slide, md, deck) -> str:
    preamble = f'<div class="agenda-preamble">{md(slide.content)}</div>' if slide.content.strip() else ""

    chapters = deck.chapters if deck else []
    if not chapters:
        hint = (
            '<p class="agenda-empty" style="opacity: 0.85; font-size: 0.8em;">No chapters found! tag slides with '
            "<code>&lt;!-- MARK: Title --&gt;</code> to build this list.</p>"
        )
        return f'<div class="slide-layout agenda">{preamble}{hint}</div>'

    # The chapter this slide belongs to is the last one that opened at or before it. 
    # An agenda placed before any chapter mark has none, and every item reads as upcoming.
    current = -1
    for i, chapter in enumerate(chapters):
        if chapter.index <= slide.index:
            current = i
        else:
            break

    # If the agenda slide itself opens the first chapter (e.g. an "Agenda"
    # MARK sitting on this same slide), listing that chapter would just
    # repeat the slide's own heading right below it. Leave it out.
    if chapters[0].index == slide.index:
        chapters = chapters[1:]
        current -= 1

    items = []
    for i, chapter in enumerate(chapters):
        state = "done" if i < current else "current" if i == current else "upcoming"
        items.append(
            f'<li class="pf-agenda-item is-{state}" data-state="{state}">'
            f"{_html.escape(chapter.title)}</li>"
        )

    return (
        '<div class="slide-layout agenda">'
        f"{preamble}"
        f'<ol class="pf-agenda">{"".join(items)}</ol>'
        "</div>"
    )
