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
from pitchfork.renderer import init_layouts, slides_to_json_payload, chapters_json_payload

DEBOUNCE_SECONDS = 0.15


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
        self._timers: Dict[Path, threading.Timer] = {}

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        changed = Path(event.src_path).resolve()
        if changed == self.deck_path:
            self._debounce(changed, self._reload_deck)
        elif changed == self.css_path:
            self._debounce(changed, self._css_reload)
        elif changed.suffix == ".py" and (
            self.layouts_dir in changed.parents
            or self.deck_layouts_dir in changed.parents
        ):
            self._debounce(changed, self._reload_deck)

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


def start_watcher(
    deck_path: Path,
    css_path: Path,
    server,
    loop: asyncio.AbstractEventLoop,
    cwd: Optional[Path] = None,
) -> Observer:
    handler = DeckChangeHandler(deck_path, css_path, server, loop, cwd=cwd)
    observer = Observer()
    observer.schedule(handler, str(deck_path.parent), recursive=False)
    # If styles.css lives in a different directory (e.g. cwd when deck is in a subfolder),
    # watch that directory too so hot-reload still fires on CSS changes.
    if css_path.parent.resolve() != deck_path.parent.resolve():
        observer.schedule(handler, str(css_path.parent), recursive=False)
    layouts_dir = deck_path.parent / "_layouts"
    if layouts_dir.is_dir():
        observer.schedule(handler, str(layouts_dir), recursive=False)
    # Also watch cwd/_layouts when it differs from the deck's _layouts
    cwd_resolved = (cwd or deck_path.parent).resolve()
    cwd_layouts_dir = cwd_resolved / "_layouts"
    if cwd_resolved != deck_path.parent.resolve() and cwd_layouts_dir.is_dir():
        observer.schedule(handler, str(cwd_layouts_dir), recursive=False)
    observer.start()
    return observer
