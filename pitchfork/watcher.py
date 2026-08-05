"""
File watcher — triggers re-parse and WebSocket broadcast on changes.
"""
import asyncio
import json
import threading
from pathlib import Path
from typing import Dict, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from pitchfork.parser import parse_deck
from pitchfork.renderer import init_deck, init_layouts, slides_to_json_payload, chapters_json_payload

DEBOUNCE_SECONDS = 0.15

# Filetypes we care about for asset reloads
def _asset_extensions() -> set:
    from pitchfork.server import MIME_TYPES
    return set(MIME_TYPES)


def _is_noise(path: Path) -> bool:
    """Skip dotfiles, dot-directories and __pycache__
    """
    return any(part.startswith(".") or part == "__pycache__" for part in path.parts)


class DeckChangeHandler(FileSystemEventHandler):
    def __init__(
        self,
        deck_path: Path,
        css_path: Path,
        server,
        loop: asyncio.AbstractEventLoop,
        cwd: Optional[Path] = None,
    ):
        self.deck_path = deck_path.resolve()
        self.css_path = css_path.resolve()
        self.cwd = (cwd or deck_path.parent).resolve()
        self.layouts_dir = self.cwd / "_layouts"
        self.deck_layouts_dir = deck_path.parent.resolve() / "_layouts"
        self.server = server
        self.loop = loop
        self.asset_extensions = _asset_extensions()
        self._timers: Dict[Path, threading.Timer] = {}

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._handle(event)
        dest = getattr(event, "dest_path", None)
        if dest:
            self._dispatch(Path(dest).resolve())

    def _handle(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._dispatch(Path(event.src_path).resolve())

    def _dispatch(self, changed: Path) -> None:
        """Route a changed file to a full re-parse, a cheap reload, or nothing."""
        if _is_noise(changed):
            return

        # Our own export output lands next to the deck; don't reload for it
        if changed in (self.deck_path.with_suffix(".html"), self.deck_path.with_suffix(".pdf")):
            return

        if changed == self.deck_path:
            self._debounce(changed, self._reload_deck)
        elif changed == self.css_path:
            self._debounce(changed, self._css_reload)
        elif changed.suffix == ".py" and (
            self.layouts_dir in changed.parents
            or self.deck_layouts_dir in changed.parents
        ):
            self._debounce(changed, self._reload_deck)
        elif changed.suffix.lower() in self.asset_extensions:
            # Assets don't change the markdown, so skip the re-parse and just tell the browser to grab new bytes
            self._debounce(changed, self._asset_reload)

    def _debounce(self, key: Path, fn) -> None:
        """Cancel any pending call for this key and schedule a fresh one."""
        existing = self._timers.get(key)
        if existing:
            existing.cancel()
        timer = threading.Timer(DEBOUNCE_SECONDS, fn)
        timer.daemon = True
        self._timers[key] = timer
        timer.start()

    def _reload_deck(self) -> None:
        try:
            init_layouts(self.deck_path, cwd=self.cwd, default_layout=self.server.default_layout)
            source = self.deck_path.read_text(encoding="utf-8")
            slides = parse_deck(source)
            init_deck(slides, self.deck_path, getattr(self.server, "config", {}))
            self.server.set_slides_json(json.dumps(slides_to_json_payload(slides)))
            self.server.set_chapters_json(json.dumps(chapters_json_payload(slides)))
            asyncio.run_coroutine_threadsafe(
                self.server.broadcast({"type": "reload"}),
                self.loop,
            )
            print(f"  ↻  Reloaded {self.deck_path.name} ({len(slides)} slides)")
        except Exception as exc:
            print(f"  ✗  Parse error: {exc}")

    def _css_reload(self) -> None:
        asyncio.run_coroutine_threadsafe(
            self.server.broadcast({"type": "reload"}),
            self.loop,
        )
        print("  ↻  styles.css updated")

    def _asset_reload(self) -> None:
        asyncio.run_coroutine_threadsafe(
            self.server.broadcast({"type": "reload"}),
            self.loop,
        )
        print("  ↻  assets updated")


def start_watcher(
    deck_path: Path,
    css_path: Path,
    server,
    loop: asyncio.AbstractEventLoop,
    cwd: Optional[Path] = None,
) -> Observer:
    handler = DeckChangeHandler(deck_path, css_path, server, loop, cwd=cwd)
    observer = Observer()

    # Watch the deck, the CSS, and any _layouts directories in the cwd and deck dir.
    roots = [(cwd or deck_path.parent).resolve()]
    for extra in (deck_path.parent.resolve(), css_path.parent.resolve()):
        # Only add paths that aren't already covered by a root we're watching.
        if not any(extra == r or r in extra.parents for r in roots):
            roots.append(extra)

    for root in roots:
        if root.is_dir():
            observer.schedule(handler, str(root), recursive=True)

    observer.start()
    return observer
