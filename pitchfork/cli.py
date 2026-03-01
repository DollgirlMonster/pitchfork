"""
Pitchfork CLI — serve, init, new, export
"""
import argparse
import asyncio
import json
import sys
import webbrowser
from pathlib import Path
from typing import Optional

# I'm still using 3.8, :')
try:
    import tomllib
except ImportError:
    import tomli as tomllib


DEFAULT_CSS = """\
/* Pitchfork Styles
   Override any CSS variable or add your own
   rules here. See pitchfork.css for layout
   classes you can target. */

@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Mono:wght@400;500&display=swap');

:root {
  --pf-bg:         oklch(98% 0.01 95);
  --pf-fg:         oklch(22% 0.02 30);
  --pf-accent:     oklch(65% 0.19 35);
  --pf-muted:      oklch(60% 0.03 30);
  --pf-border:     oklch(90% 0.01 95);

  --pf-font-body:  'Instrument Serif', Georgia, serif;
  --pf-font-code:  'DM Mono', 'JetBrains Mono', monospace;
  --pf-font-size:  clamp(1rem, 2.5vw, 2rem);

  --pf-draw-color: oklch(65% 0.19 35);
  --pf-draw-width: 4;
}
"""

DEFAULT_SIDECAR = """\
[deck]
default_layout = "body"

[export]
resolution = "1920x1080"
"""

EXAMPLE_DECK = """\
# My Presentation
## Made with Pitchfork

%%%
- Notes are optional -- just put them under a `%%%` separator.
- They won't show in the slides, but you can see them in presenter view by pressing 'n' or 'p'
    - But you may already know that

---

## Why plain text?

- Version controllable
- Editable in any editor
- Fast to write

---

<iframe src="/timer" style="width:100%;height:100%;border:none;"></iframe>
Embed timers, videos, web content, whatever you need.

%%%
You can also press 't' to open the timer in a pop-out window

---

# slide: two-column

::left::
## Before
```xml
<key:presentation>
  <key:slide-list>
    ...
```

::right::
## After
```markdown
# My Slide
- plain text
- readable diffs
```

%%%
You have full control over the layout with simple tags, or let Pitchfork auto-detect based on content.
Choose from:
- `body` (default)
- `two-column`
- `image-right`
- `title`
- `section`
- `code`

---

# slide: image-right

## A picture is worth a thousand words

Use `# slide: image-right` to place an image on the right.
Images can be local files or remote URLs.

![placeholder](https://placehold.co/600x400)

%%%
This layout auto-detects too — if your slide has an image and text,
Pitchfork will pick image-right without needing the explicit tag.

---

<div style="margin: auto">
  <h1>Thank You</h1>
</div>

- [Support Monthly](https://patreon.com/ellieonline)
- [One-Off Donation](https://ko-fi.com/ellieonline)

%%%
If Pitchfork improves your workflow, please donate! I can't live without you.

- [Support Monthly](https://patreon.com/ellieonline)
- [One-Off Donation](https://ko-fi.com/ellieonline)
"""


def find_deck(cwd: Path) -> Optional[Path]:
    """Find a .md file in a Pitchfork project dir."""
    sidecar = cwd / ".pitchfork"
    if not sidecar.exists():
        return None
    mds = list(cwd.glob("*.md"))
    if len(mds) == 1:
        return mds[0]
    if len(mds) > 1:
        print("Multiple .md files found:")
        for i, p in enumerate(mds):
            print(f"  {i+1}. {p.name}")
        choice = input("Pick one (number): ").strip()
        try:
            return mds[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice.")
            sys.exit(1)
    return None


def load_config(deck_path: Path) -> dict:
    sidecar = deck_path.parent / ".pitchfork"
    if sidecar.exists():
        with open(sidecar, "rb") as f:
            return tomllib.load(f)
    return {}


EXAMPLE_LAYOUT = '''\
"""
Example custom layout — rename this file and edit match() / html() to taste.

Place layout files in _layouts/ next to your deck. They are tried before
the built-in layouts, so a layout here with the same name as a built-in
will override it. Within this folder, files are loaded alphabetically;
prefix with numbers (01-, 02- ...) to control priority.

Each file must expose two functions:
  match(slide) -> bool   return True to claim this slide
  html(slide, md) -> str return the rendered HTML string
"""


def match(slide) -> bool:
    # Example: claim slides that have a ::highlight:: zone
    return "highlight" in slide.zones


def html(slide, md) -> str:
    body = md(slide.content)
    highlight = md(slide.zones.get("highlight", ""))
    return (
        '<div class="slide-layout body custom-highlight">' +
        body +
        '<div class="highlight-box">' + highlight + "</div>" +
        "</div>"
    )
'''

def cmd_init(args):
    cwd = Path.cwd()
    sidecar = cwd / ".pitchfork"
    css = cwd / "styles.css"
    layouts_dir = cwd / "_layouts"

    if sidecar.exists():
        print("  .pitchfork already exists — skipping sidecar.")
    else:
        sidecar.write_text(DEFAULT_SIDECAR)
        print("  ✓  Created .pitchfork")

    if args.bare:
        return

    if css.exists():
        print("  styles.css already exists — skipping.")
    else:
        css.write_text(DEFAULT_CSS)
        print("  ✓  Created styles.css")

    if layouts_dir.exists():
        print("  _layouts/ already exists — skipping.")
    else:
        layouts_dir.mkdir()
        (layouts_dir / "example.py").write_text(EXAMPLE_LAYOUT)
        print("  ✓  Created _layouts/  (add custom layout plugins here)")

    print("\n  Run `pitchfork new talk.md` to create a deck.")


def cmd_new(args):
    path = Path(args.file)
    if path.exists():
        print(f"  {path} already exists.")
        sys.exit(1)
    path.write_text(EXAMPLE_DECK)
    print(f"  ✓  Created {path}")


def cmd_serve(args):
    from pitchfork.parser import parse_deck
    from pitchfork.renderer import slides_to_json_payload
    from pitchfork.server import PitchforkServer
    from pitchfork.watcher import start_watcher

    cwd = Path.cwd()

    if args.file:
        deck_path = Path(args.file)
    else:
        deck_path = find_deck(cwd)
        if not deck_path:
            print("  No .pitchfork sidecar found. Run `pitchfork init` first, or specify a file.")
            sys.exit(1)

    if not deck_path.exists():
        print(f"  File not found: {deck_path}")
        sys.exit(1)

    css_path = deck_path.parent / "styles.css"
    config = load_config(deck_path)
    default_layout = config.get("deck", {}).get("default_layout", "body")
    port = args.port    # TODO: handle port in use; just go up 2 at a time until we find a free one

    # Initial parse
    from pitchfork.renderer import init_layouts
    init_layouts(deck_path)
    source = deck_path.read_text(encoding="utf-8")
    slides = parse_deck(source, default_layout)
    slides_json = json.dumps(slides_to_json_payload(slides))

    server = PitchforkServer(deck_path, css_path, host="localhost", port=port)
    server.default_layout = default_layout
    server.set_slides_json(slides_json)

    print(f"\n   On Deck — {deck_path.name} ({len(slides)} slides)")

    async def main():
        loop = asyncio.get_running_loop()
        watcher = start_watcher(deck_path, css_path, server, loop)
        try:
            if not args.no_open:
                webbrowser.open(f"http://localhost:{port}/slides")
            await server.start()
        finally:
            watcher.stop()
            watcher.join()

    asyncio.run(main())


def cmd_export(args):
    from pitchfork.exporter import export_deck
    export_deck(Path(args.file), html=args.html)

def main():
    parser = argparse.ArgumentParser(prog="pitchfork", description="Pitchfork is a plain-text slide tool")
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize a Pitchfork project in the current folder")
    p_init.add_argument("--bare", action="store_true", help="Only create .pitchfork, no styles.css")

    # new
    p_new = sub.add_parser("new", help="Create a new deck file")
    p_new.add_argument("file", help="Filename, e.g. talk.md")

    # serve
    p_serve = sub.add_parser("serve", help="Serve a deck with live reload")
    p_serve.add_argument("file", nargs="?", help="Deck .md file (auto-detected if omitted)")
    p_serve.add_argument("--port", type=int, default=3000, help="HTTP port (default: 3000)")
    p_serve.add_argument("--no-open", action="store_true", help="Don't open browser automatically")

    # export
    p_export = sub.add_parser("export", help="Export deck to PDF or HTML")
    p_export.add_argument("file", help="Deck .md file")
    p_export.add_argument("--html", action="store_true", help="Export as self-contained HTML (DOES NOT WORK YET)")

    args = parser.parse_args()

    print("""
PITCHFORK :: Bullshit-Free Slides

If Pitchfork improves your workflow, please consider donating! I can't live without you.
   Support Monthly:  https://patreon.com/ellieonline
   One-Off Donation: https://ko-fi.com/ellieonline
""")

    if args.command == "init":
        cmd_init(args)
    elif args.command == "new":
        cmd_new(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "export":
        cmd_export(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
