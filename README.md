# Pitchfork

Write slides in Markdown, present in the browser. Easy as.

![Pitchfork](/screenshots/title-slide.png)

If this software is useful, please donate! I can't live without you.
[Support Monthly](https://patreon.com/ellieonline)
[One-Off Donation](https://ko-fi.com/ellieonline)

## Features

- Draw on slides!
- Soundboard support!
- Arbitrary extension via `<iframe>` and `.py` layout files!
- Live-reload during edit!

![Drawing on Slides](/screenshots/draw.png)

## Install

First, download Pitchfork. Then, install with `pip`:
```bash
cd /path/to/pitchfork
pip install .
```

## Quickstart

```bash
mkdir my-talk && cd my-talk/
pitchfork init          # creates .pitchfork and styles.css
pitchfork new slides.md # scaffold a deck
pitchfork serve         # opens slides in the browser, live-reloads on updates
```

## Deck syntax

| Feature | Syntax / Usage |
|---|---|
| **Slide breaks** | `---` on its own line |
| **Reveal step** | `--` on its own line |
| **Notes delimiter** | `%%%` on its own line — everything until the next `---` is notes |
| **Explicit layout override** | `::layout:<layout-name>::` as the first line of a slide. More info about Layouts in the Layouts section below. |
| **Chapter marker** | `<!-- MARK: Chapter Title -->` tags the slide as a chapter start (and highlights it in the VSCode sidebar!) |


| ![Pitchfork](/screenshots/what-is-usability.png) | ![Code](/screenshots/what-is-usability-code.png) |
|---|---|

### Example:
```markdown
::layout:title::
# Deck Title
## Example Content

- Slide content; text, images, whatever you like.

%%%
Speaker notes go here — full markdown supported.

- bullet points, HTML, links, whatever you need
- [ ] Checkboxes work too, for step-by-step notes!

---

::layout:agenda::
## Today's Agenda

%%%
- The `agenda` layout automatically builds a list from the deck's chapters. Anything you write on the slide renders above the list.

---

<!-- MARK: Chapter Title 
-->
## Here's Another Slide
- Slide Layout is auto-detected based on content
- You can override it by putting `::layout:<layout-name>::` at the very top of the slide
- You can also add custom layouts with your own auto-detection logic!

![example image](https://placehold.co/600x400)

---
# Another Layout Example

::left::
## Left column
- Info can go here

::right::
## Right column
- Or over here

---
```

Easy, huh?

## CLI reference

```
pitchfork init [--bare]          Initialize project in current folder
pitchfork new <file.md>          Scaffold a new deck
pitchfork serve [file.md]        Serve with live reload (auto-discovers if omitted)
              [--port N]         HTTP port (default 1312; WS on port+1)
              [--no-open]        Don't open browser automatically
pitchfork export <file.md>       Export to PDF (requires playwright)
                 [--html]        Export as self-contained HTML folder
pitchfork doctor [file.md]       Check decks for things that fail quietly
                                 (checks every deck in the project if omitted)
```

## Views

| URL | Description |
|---|---|
| `/slides` | Fullscreen current slide — this is the one your audience sees. `←`/`→` or `j`/`k` to navigate. |
| `/notes` | Slide strip + full notes panel. This is the view to present from. |
| `/timer` | A countdown timer, embeddable in a slide or popped out on its own. |

Both views stay in sync over a WebSocket, so you can drive from either one.

### Keys

| Key | | Where |
|---|---|---|
| `←` `→` `↑` `↓` `j` `k` `space` | Move through the deck, one reveal step at a time | both |
| `n` | Pop out the notes view | slides |
| `t` | Pop out the timer | both |
| `c` | Chapter jump menu | notes |
| `g` | Slide overview — every slide as a thumbnail, grouped by chapter; click one to jump | notes |
| `backspace` | Clear anything you've drawn on the slide | slides |
| `1`–`9` | Soundboard, if you've configured one | notes |

## Chapters

Add `<!-- MARK: Chapter Title -->` comments to your deck to define chapters. Place the comment anywhere in a slide's block to tag the slide as the opening of a chapter.

I recommend putting the closing `-->` on its own line, because as of this writing VS Code displays it as a string literal otherwise.

```markdown
<!-- MARK: Introduction
-->

## Why plaintext?

- Version controllable
- Fast to write
- Corpo-free
- Radically portable

---

<!-- MARK: Demo
-->

## Live Demo
```

A `§ Chapter Title` indicator appears in all views to help you and your audience keep track of where you are and what's next. Press `c` in `notes` view to open the chapter jump menu, where you can jump directly to any chapter, or `g` for the slide overview, where slides are grouped under their chapter headings.

## Reveal Steps

`--` splits a slide into steps. Everything above the first `--` shows immediately; each keypress reveals the next chunk before moving on to the next slide.

```markdown
## The Persuasive Formula

- Verb
--
- Benefit
--
- Urgent time or place
```

Steps work inside zones too:

```markdown
::left::
Before: 26%
--
After: 92%

::right::
![diagram](img/process.png)
```

## Layouts
### Built-In Layouts

| Content | Layout |
|---|---|
| Only headings (≤2) | `title` |
| Only a single heading | `section` |
| `::left::` / `::right::` zones | `two-column` |
| Mostly code blocks | `code` |
| An image, then text | `image-left` |
| Text, then an image | `image-right` |
| Everything else | `body` (or `default_layout` from `.pitchfork`) |
| `::layout:agenda::` | builds a list from the Deck's Chapters, see below |

#### Agenda Layout

`::layout:agenda::` builds a list from your `<!-- MARK: -->` chapters. Anything you write on the slide renders above the list:

Drop the same slide in again between sections and it re-renders showing where
you are. Each item includes stylable classes:

```css
.pf-agenda-item.is-done      { opacity: 0.35 }        /* already covered */
.pf-agenda-item.is-current   { color: var(--pf-accent) }
.pf-agenda-item.is-upcoming  { }                      /* still to come */
```

### Custom Layouts

Drop a `layoutname.py` file into the `_layouts/` folder in your working directory to define a custom layout. 

Layouts are found in this order, and the first one to claim a slide wins:

| | Where | For |
|---|---|---|
| 1 | `_layouts/` in your working directory | all decks in this project |
| 2 | `_layouts/` next to a deck file in a subfolder | one specific deck |
| 3 | `~/.config/pitchfork/_layouts/` | every project on your computer |
| 4 | Built-in | everyone |

Custom layouts must include the `match()` and `html()` functions in order to work:

> `match()` describes logic for when to apply the layout

> `html()` returns an HTML string describing the slide layout. The `md()` function is passed in to convert markdown to HTML.

> `slide.content` is the slide body, `slide.zones` holds `::zone::` regions, `slide.notes` holds speaker notes.

Here's an example:

```python
# _layouts/big-number.py

def match(slide) -> bool:
    """Return True to claim this slide."""
    """Returns `True` when there are no zones and the trimmed content is numeric, allowing a trailing `%`."""
    content = slide.content.strip().removesuffix("%").strip()
    return slide.zones == [] and content.isdigit()

def html(slide, md) -> str:
    """Return an HTML string. md() converts markdown to HTML."""
    return """
        <div class="slide-layout" style="
            font-size: 4rem;
            display: flex;
            align-items: center;
            justify-content: center;
        ">{content}</div>
    """.format(content=md(slide.content))
```

#### Layouts that need the whole deck

`html()`'s `deck` parameter gives optional deck-wide context to your Layout.

```python
def html(slide, md, deck) -> str:
    ...
```

| | |
|---|---|
| `deck.slides` | every parsed slide |
| `deck.chapters` | `<!-- MARK: -->` chapters, each with `.index` and `.title` |
| `deck.config` | the `.pitchfork` sidecar, parsed |
| `deck.path` | the deck file's path |

This is how the built-in `agenda` layout knows your chapters. It's also handy for creating
layouts that need more info than just one slide, such as rendering the next slides for a transition animation, or creating a title layout that reads the course name out of your sidecar:

```toml
# .pitchfork
...

[vars]
course = "UI/UX"
```

```python
# _layouts/title.py
""" A smart title layout that reads the course name from the project sidecar and the session number from the deck filename. """

import re
def match(slide) -> bool:
    # override default title layout
    if slide.zones:
        return False
    content = re.compile(r'<!--.*?-->', re.DOTALL).sub('', slide.content)
    lines = [l for l in content.strip().splitlines() if l.strip()]
    heading_lines = [l for l in lines if l.startswith("#")]
    body_lines = [l for l in lines if not l.startswith("#")]
    return bool(heading_lines and not body_lines and len(heading_lines) <= 2)

def html(slide, md, deck) -> str:
    course = deck.config.get("vars", {}).get("course", "")
    session = re.search(r"\d+", deck.path.stem)
    return (
        '<div class="slide-layout title">'
        f'<p class="session">Session {session.group() if session else ""}</p>'
        f'<h1>{course}</h1>{md(slide.content)}'
        '</div>'
    )
```

## Little Extras
### `.pitchfork` Sidecar

Defines default layout and export settings. Example:

```toml
[deck]
default_layout = "body"   # fallback when layout can't be guessed

[export]
resolution = "1080x720"
```

### `styles.css` Styling
Override CSS variables or add your own rules. You're da boss.

```css
:root {
    /* Background color for slides and page backgrounds */
    --pf-bg:            oklch(99% 0.01 240);
    /* Primary foreground / body text color */
    --pf-fg:            oklch(25% 0.02 240);
    /* Accent color used for links, highlights, and active UI */
    --pf-accent:        oklch(65% 0.18 260);
    /* Muted / tertiary text color (counters, hints) */
    --pf-muted:         #888888;
    /* Border / separator color */
    --pf-border:        #e0e0e0;

    /* Heading font stack for slide content*/
    --pf-font-header:   system-ui, sans-serif;
    /* Body font stack for slide content*/
    --pf-font-body:     system-ui, sans-serif;
    /* Monospace font stack used for code blocks and thumbnails */
    --pf-font-code:     'JetBrains Mono', 'Fira Code', monospace;
    /* Font used for speaker notes / notes panel */
    --pf-font-notes:    'Atkinson Hyperlegible', system-ui, sans-serif;
    /* Base responsive font size for slides */
    --pf-font-size:     clamp(1rem, 2.5vw, 2rem);

    /* Height of the bottom chapter/thumbnail strip */
    --pf-strip-height:  180px;
    /* Width of each thumbnail in the strip */
    --pf-thumb-width:   240px;

    /* Color used for in-slide drawing/annotation */
    --pf-draw-color:    oklch(65% 0.18 260);
    /* Stroke width (px) for drawing annotations */
    --pf-draw-width:    4;
}
```

### Logo

You can add a logo to your deck for a touch of subtle branding. Place a `logo.png` in your working directory, and Pitchfork will display it at low opacity in the bottom-right corner of each slide.


### Timer Widget

Pitchfork exposes a countdown timer at the `/timer` endpoint. You can pop it out from either view with the `t` key, or embed it directly into your slides with an iframe.

`/timer` supports an optional `duration` query parameter to set the initial countdown time. You can use flexible time formats:

- `?duration=5m30s` — 5 minutes, 30 seconds
- `?duration=5m` — 5 minutes
- `?duration=100s` — 100 seconds
- `?duration=50m30s` — 50 minutes, 30 seconds

If not provided, the timer defaults to 5 minutes. You can also type directly into the timer.

An Example:

```
::left::
# Lunch Break

::right::
<iframe src="/timer?duration=15m" height=200></iframe>
```

### QR Codes

Links whose text is "QR" (case-insensitive) are converted into QR codes when you present your slides. The QR code will size to fit the available width.

Style `.pf-qr` to override its appearance

Usage:

```markdown
[QR](https://example.com)
```

### Soundboard

Add a `[soundboard]` section in your `.pitchfork` sidecar to define links to sound effects for your deck. Trigger them using the numpad keys.

```
[soundboard]
1 = "soundboard/Bingo!.mp3"
3 = "soundboard/Buzzer.mp3"
7 = "soundboard/Mission Start.mp3"
```

## Doctor

Pitchfork is forgiving at render time on purpose: a missing image is just a
broken image, an unknown layout name falls back to bare rendering, and a zone
no layout uses simply doesn't appear. That's the right call in front of a room,
but it means mistakes surface during class instead of at your desk.

`pitchfork doctor` is where they surface early.

```bash
pitchfork doctor              # check every deck in the project
pitchfork doctor slides.md    # check one deck
```

```
  Session 14.md
    ✗   160  missing media: img/wk14/dont-make-me-think.jpeg
    !   176  empty QR target: ![QR]()
            renders an empty QR code on the slide

  TODO
    ·   176  [comment]   Session 14.md: Add QR code linking to survey

  1 error, 1 warning, 1 TODO across 14 decks.
```

With no filename, doctor checks every deck `serve` would offer you — so the two
commands never disagree about what counts as a deck.

If doctor itself crashes on a check, it says so and labels the finding a
`doctor bug` rather than blaming your deck, and the remaining checks still run.
Set `PITCHFORK_DOCTOR_STRICT=1` to get the traceback instead.

It reports and never edits. `✗` marks things that are broken on the slide,
`!` marks things that are probably not what you meant, and the TODO section
lists every `TODO`/`FIXME` in your decks, tagged by where it lives:

| Tag | Meaning |
|---|---|
| `[ON SLIDE]` | in slide content — your audience will read it |
| `[notes]` | in speaker notes — only you see it |
| `[comment]` | inside an HTML comment — invisible |

`- [ ]` checkboxes are not treated as TODOs, since those are the step-by-step
notes feature.

What it looks for:

| Check | |
|---|---|
| Missing images, media, and iframe sources | resolved the same way the server resolves them |
| Unknown `::layout:name::` | falls back to bare rendering, silently |
| Zone content no layout renders | `::left::` on a layout that only draws `slide.content` |
| Layout that raises | shows the error before your audience does |
| `::layout:` marker not on the slide's first line | ignored where it sits |
| Unclosed HTML comments | a `<!--` closed with a bare `>` swallows the rest |
| Malformed `/timer` query strings | `&duration=` silently falls back to 5 minutes |
| More than one `%%%` in a slide | only the first splits notes |
| Empty `[QR]()` targets and empty `<!-- MARK: -->` titles | |
| Sidecar problems | bad `resolution`, soundboard slots outside 1–9, missing sound files, unknown `default_layout` |

Examples inside fenced code blocks and `inline code` are skipped, so a deck that
teaches Pitchfork syntax doesn't report itself.

## Export

Pitchfork can export your deck to PDF, or a self-contained HTML folder. 

### PDF Export
PDF export requires Playwright & Chromium:

```bash
pip install playwright
playwright install chromium
pitchfork export slides.md
```

This writes `slides.pdf` next to your source file.

### HTML Export

```bash
pitchfork export slides.md --html
```

This writes a self-contained `slides.html` which includes images, CSS, and JS