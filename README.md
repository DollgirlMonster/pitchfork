# Pitchfork

Write slides in Markdown, present in the browser. Easy as.

If this software is useful, please donate! I can't live without you.
[Support Monthly](https://patreon.com/ellieonline)
[One-Off Donation](https://ko-fi.com/ellieonline)

## Install

```bash
cd /path/to/pitchfork
pip install -e .
```

## Quickstart

```bash
mkdir my-talk && cd my-talk/
pitchfork init          # creates .pitchfork and styles.css
pitchfork new slides.md # scaffold a deck
pitchfork serve         # opens slides in the browser, live-reloads on updates
```

## Deck syntax

```markdown
# Slide title
## Subtitle

%%%
Speaker notes go here — full markdown supported.

- bullet points, HTML, links, whatever
- anything goes

---

## Next slide
Content here. Layout is auto-detected.

![placeholder](https://placehold.co/600x400)

---

# slide: two-column

::left::
## Left column
- Info can go here

::right::
## Right column
- Or over here

---
```

**Slide breaks:** `---` on its own line  
**Notes delimiter:** `%%%` on its own line — everything until the next `---` is notes  
**Explicit layout override:** `# slide: <layout>` as the first line of a slide

Easy, huh?

## Custom Layout Files

Drop a `layoutname.py` file into a `_layouts/` folder with your deck. It MUST include two functions:

```python
# _layouts/big-number.py

def match(slide) -> bool:
    """Return True to claim this slide."""
    """Returns `True` when there are no zones and the trimmed content is numeric, allowing a trailing `%`."""
    content = slide.content.strip().removesuffix("%").strip()
    return slide.zones == [] and content.isdigit()

def html(slide, md) -> str:
    """Return an HTML string. md() converts markdown → HTML."""
    return f'<div class="slide-layout" style="font-size: 4rem;">{md(slide.content)}</div>'
```

`slide.content` is the slide body, `slide.zones` holds `::zone::` regions, `slide.notes` holds speaker notes.

Sidecar layouts take priority over built-ins. A file at `_layouts/body.py` replaces the built-in `body` layout.

## Auto-Detected Layouts

| Content | Layout |
|---|---|
| Only headings (≤2) | `title` |
| Only a single heading | `section` |
| `::left::` / `::right::` zones | `two-column` |
| Mostly code blocks | `code` |
| Image + text | `image-right` |
| Everything else | `body` (or `default_layout` from `.pitchfork`) |


## Views

| URL | Description |
|---|---|
| `/slides` | Fullscreen current slide. `←`/`→` or `j`/`k` to navigate. `p` opens presenter view, `n` opens notes view, `t` pops out a timer widget. |
| `/notes` | Slide strip + full notes panel. Synced with slides view. |
| `/presenter` | Current slide, next slide, notes, and stopwatch. |

All views stay in sync via WebSocket.

## Sidecar — `.pitchfork`

```toml
[deck]
default_layout = "body"   # fallback when layout can't be guessed

[export]
resolution = "1920x1080"
```

## Styling — `styles.css`

Override CSS variables or add your own rules:

```css
:root {
  --pf-bg:         oklch(99% 0.01 240);
  --pf-fg:         oklch(25% 0.02 240);
  --pf-accent:     oklch(65% 0.18 260);
  --pf-draw-color: oklch(65% 0.18 260);

  --pf-font-body:   system-ui, sans-serif;
  --pf-font-code:   'JetBrains Mono', monospace;
  --pf-font-size:   clamp(1rem, 2.5vw, 2rem);
  /* and more... */
}
```

### Logo

You can add a logo to your deck for a touch of subtle branding. Simply place a file called `logo.png` in the slide deck directory's root, and Pitchfork will display it at low opacity in the bottom-left corner of each slide.

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

## Export

Pitchfork can export your deck to PDF (via Playwright), or a self-contained HTML folder

- PDF export (requires Playwright + Chromium):

```bash
pip install playwright
playwright install chromium
pitchfork export talk.md
```

This writes `talk.pdf` next to your source file.

- HTML file export:

```bash
pitchfork export talk.md --html
```

This creates a totally self-contained `talk.html/` which includes images, CSS, and JS