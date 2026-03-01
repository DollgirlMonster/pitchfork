"""
Discovers and loads layout plugins.

Load order (first match wins):
  1. Sidecar _layouts/ folder next to the deck file (user-defined)
  2. Built-in layouts (pitchfork/layouts/)

Within each group, files are loaded alphabetically. Prefix filenames
with numbers (e.g. 01-my-layout.py) to control ordering explicitly.

Each layout file must expose:
  match(slide) -> bool   — return True if this layout should handle the slide
  html(slide, md) -> str — render and return an HTML string
"""
import importlib.util
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Layout:
    name: str
    match: Callable   # (slide) -> bool
    html: Callable    # (slide, md) -> str
    source: Path      # for logging / debugging


def _load_layout_file(path: Path) -> Optional[Layout]:
    """Load a single .py layout file. Returns None on any error."""
    try:
        spec = importlib.util.spec_from_file_location(f"_pf_layout_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not (hasattr(mod, "match") and hasattr(mod, "html")):
            logger.warning("Layout %s is missing match() or html() — skipping", path.name)
            return None
        return Layout(name=path.stem, match=mod.match, html=mod.html, source=path)
    except Exception as exc:
        logger.warning("Failed to load layout %s: %s", path.name, exc)
        return None


def load_layouts(deck_path: Path) -> List[Layout]:
    """
    Return an ordered list of layouts. Sidecar layouts come first so they
    take priority over built-ins with the same name. Within each group,
    files are sorted alphabetically.
    """
    layouts: List[Layout] = []
    seen_names: set = set()

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

    # 1. Sidecar layouts win
    _load_dir(deck_path.parent / "_layouts", "sidecar")

    # 2. Built-in layouts
    _load_dir(Path(__file__).parent / "layouts", "built-in")

    return layouts


def pick_layout(layouts: List[Layout], slide, explicit_name: Optional[str] = None) -> Optional[Layout]:
    """
    If explicit_name is given, return the matching layout by name (or None).
    Otherwise walk the list and return the first layout whose match() is truthy.
    """
    if explicit_name:
        return next((l for l in layouts if l.name == explicit_name), None)
    return next((l for l in layouts if l.match(slide)), None)
