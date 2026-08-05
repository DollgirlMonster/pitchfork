"""
Discovers and loads layout plugins.

Load order (first match wins):
  1. cwd/_layouts                   root where pitchfork was launched
  2. deck_dir/_layouts              sidecar next to the deck file (when different from cwd)
  3. ~/.config/pitchfork/_layouts   layouts shared across all your projects
  4. Built-in layouts               (pitchfork/layouts/)

Within each group, files are loaded alphabetically. Prefix filenames
with numbers (e.g. 01-my-layout.py) to control ordering explicitly.

Each layout file must expose:
  match(slide) -> bool   — return True if this layout should handle the slide
  html(slide, md) -> str — render and return an HTML string

html() may optionally take a third argument to receive whole-deck context:
  html(slide, md, deck) -> str
where deck exposes .slides, .chapters, .config and .path. Layouts that only
declare two parameters are called with two. I didn't know you could do that in Python!
"""
import importlib.util
import inspect
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Fallback layout name used when a slide isn't claimed by match() and no
# (or an invalid) default_layout is configured. Other modules import this to stay DRY
DEFAULT_LAYOUT_NAME = "body"


@dataclass
class Layout:
    name: str
    match: Callable   # (slide) -> bool
    html: Callable    # (slide, md) -> str, or (slide, md, deck) -> str
    source: Path      # for logging / debugging
    wants_deck: bool = False


def _wants_deck(fn: Callable) -> bool:
    """True when html() can accept a third positional `deck` argument.

    Checked once at load time rather than per render.
    TODO: This could cause issues when developing layouts; investigate if PITA
    """
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    positional = 0
    for param in sig.parameters.values():
        if param.kind is param.VAR_POSITIONAL:
            return True
        if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
            positional += 1
    return positional >= 3


def _load_layout_file(path: Path) -> Optional[Layout]:
    """Load a single .py layout file. Returns None on any error."""
    try:
        spec = importlib.util.spec_from_file_location(f"_pf_layout_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not (hasattr(mod, "match") and hasattr(mod, "html")):
            logger.warning("Layout %s is missing match() or html() — skipping", path.name)
            return None
        return Layout(
            name=path.stem, match=mod.match, html=mod.html, source=path,
            wants_deck=_wants_deck(mod.html),
        )
    except Exception as exc:
        logger.warning("Failed to load layout %s: %s", path.name, exc)
        return None


def user_layouts_dir() -> Path:
    """Layouts shared across every project. Looks for $XDG_CONFIG_HOME."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "pitchfork" / "_layouts"


def load_layouts(deck_path: Path, cwd: Optional[Path] = None) -> List[Layout]:
    """
    Return an ordered list of layouts. Load order (first match wins):
      1. cwd/_layouts (root where pitchfork was launched, when different from deck dir)
      2. deck_path.parent/_layouts (sidecar next to the deck file)
      3. ~/.config/pitchfork/_layouts (shared across projects)
      4. Built-in layouts
    Within each group, files are sorted alphabetically.
    """
    layouts: List[Layout] = []
    seen_names: set[str] = set()

    def _load_dir(directory: Path, label: str) -> None:
        if not directory.is_dir():
            return
        for f in sorted(directory.glob("*.py")):
            if f.name.startswith("_"):
                continue
            layout = _load_layout_file(f)
            if layout is None:
                continue
            if layout.name in seen_names:
                logger.debug("Layout '%s' from %s shadowed by earlier entry — skipping", layout.name, label)
                continue
            layouts.append(layout)
            seen_names.add(layout.name)
            logger.debug("Loaded layout '%s' from %s", layout.name, label)

    cwd = cwd or deck_path.parent

    # 1. cwd/_layouts wins (root where pitchfork was launched)
    _load_dir(cwd / "_layouts", "cwd")

    # 2. Sidecar layouts next to deck (only when different from cwd)
    if cwd.resolve() != deck_path.parent.resolve():
        _load_dir(deck_path.parent / "_layouts", "sidecar")

    # 3. User-level layouts, shared across projects
    _load_dir(user_layouts_dir(), "user config")

    # 4. Built-in layouts
    _load_dir(Path(__file__).parent / "layouts", "built-in")

    return layouts


def lookup_by_name(layouts: List[Layout], name: str) -> Optional[Layout]:
    """Return the layout with this exact name, or None"""
    return next((l for l in layouts if l.name == name), None)


def detect(layouts: List[Layout], slide) -> Optional[Layout]:
    """Walk the list and return the first layout whose match() is truthy"""
    return next((l for l in layouts if l.match(slide)), None)


def resolve_layout(layouts: List[Layout], slide, default_name: str) -> Optional[Layout]:
    """
    Decide which layout renders this slide

    An explicit ::layout:name:: marker: look it up by name
        A typo'd override should fall to the body fallback, not get silently reinterpreted by auto-detect.
    
    Otherwise: auto-detect via match(), 
    Then the configured default_layout name
    
    Returns None only if nothing at all resolves"""
    if slide.layout:
        return lookup_by_name(layouts, slide.layout)
    return detect(layouts, slide) or lookup_by_name(layouts, default_name)
