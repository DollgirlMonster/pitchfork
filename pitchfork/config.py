"""
Shared .pitchfork sidecar loading, used by cli.py, exporter.py, and anything
else that needs a deck's config without doctor.py's lenient error-swallowing.
"""
from pathlib import Path
try:
    import tomllib  # type: ignore
except Exception:
    import tomli as tomllib  # type: ignore


def load_config(deck_path: Path) -> dict:
    sidecar = deck_path.parent / ".pitchfork"
    if sidecar.exists():
        with open(sidecar, "rb") as f:
            return tomllib.load(f)
    return {}


def parse_resolution(resolution: str, default: tuple = (1920, 1080)) -> tuple:
    try:
        w, h = map(int, resolution.split("x"))
        return w, h
    except Exception:
        return default
