# Pitchfork

Write slides in Markdown, present in the browser. Easy as.

If this software is useful, please donate! I can't live without you.
[Support Monthly](https://patreon.com/ellieonline)
[One-Off Donation](https://ko-fi.com/ellieonline)

## Install

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
| **Slide breaks** | `---` on its own line
| **Notes delimiter** | `%%%` on its own line — everything until the next `---` is notes |
| **Explicit layout override** | `::layout:<layout-name>::` as the first line of a slide. More info about Layouts in the Layouts section below. |
| **Chapter marker** | `<!-- MARK: Chapter Title -->` tags the slide as a chapter start (and highlights it in the VSCode sidebar!) |

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
                 [--html]        Export as self-contained HTML folder (Doesn't work yet!!!)
```

## Views

| URL | Description |
|---|---|
| `/slides` | Fullscreen current slide. `←`/`→` or `j`/`k` to navigate. `p` opens presenter view, `n` opens notes view, `t` pops out a timer widget; see below for more info. |
| `/notes` | Slide strip + full notes panel. Synced with slides view. Press `c` to open the chapter jump menu. |
| `/presenter` | Current slide, next slide, notes, and stopwatch. Press `c` to open the chapter jump menu. |

All views stay in sync via WebSocket.

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

A `§ Chapter Title` indicator appears in all views to help you and your audience keep track of where you are and what's next. Press `c` in `notes` or `presenter` view to open the chapter jump menu, where you can jump directly to any chapter.

## Layouts
### Built-In Layouts

| Content | Layout |
|---|---|
| Only headings (≤2) | `title` |
| Only a single heading | `section` |
| `::left::` / `::right::` zones | `two-column` |
| Mostly code blocks | `code` |
| Image + text | `image-right` |
| Everything else | `body` (or `default_layout` from `.pitchfork`) |


### Custom Layouts

Drop a `layoutname.py` file into the `_layouts/` folder in your working directory to define a custom layout. 

Custom layouts take priority over built-in ones. They must include the `match()` and `html()`  functions in order to work:

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

    /* Body font stack (used for slide content) */
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

### Timer Widget

Pitchfork exposes a countdown timer at the `/timer` endpoint. You can pop it out in presenter view with the `t` key, or embed it directly into your slides with an iframe.

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

## QR Codes

Links whose text is "QR" (case-insensitive) are converted into QR codes when you present your slides. The QR code will size to fit the available width.

Style `.pf-qr` to override its appearance

Usage:

```markdown
[QR](https://example.com)
```
