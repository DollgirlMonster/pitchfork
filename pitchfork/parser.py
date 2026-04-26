"""
Parser for Pitchfork .md deck files.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Slide:
    index: int
    layout: Optional[str]
    content: str
    notes: str
    zones: Dict[str, str] = field(default_factory=dict)
    chapter: Optional[str] = None


def detect_layout(content: str, zones: dict) -> Optional[str]:
    """Heuristic layout detection based on content. Returns None if no guess can be made."""
    stripped = content.strip()

    if zones:
        keys = set(zones.keys())
        if {"left", "right"} & keys:
            return "two-column"

    lines = [l for l in stripped.splitlines() if l.strip()]
    heading_lines = [l for l in lines if l.startswith("#")]
    body_lines = [l for l in lines if not l.startswith("#")]

    if heading_lines and not body_lines:
        return "title" if len(heading_lines) <= 2 else "section"

    if len(lines) == 1 and lines[0].startswith("# "):
        return "section"

    # Count lines inside fenced code blocks
    code_lines = 0
    in_fence = False
    for line in stripped.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue  # don't count the fence markers themselves
        if in_fence:
            code_lines += 1
    total_lines = max(len(stripped.splitlines()), 1)
    if code_lines / total_lines > 0.5 and total_lines > 3:
        return "code"

    if re.search(r"!\[.*?\]\(.*?\)", stripped):
        return "image-right"

    return None


def parse_zones(content: str) -> Tuple[str, Dict[str, str]]:
    """Extract ::zone:: markers from content, return cleaned content and zones dict."""
    zone_pattern = re.compile(r"^::(\w+)::\s*$", re.MULTILINE)
    matches = list(zone_pattern.finditer(content))

    if not matches:
        return content, {}

    zones = {}
    for i, match in enumerate(matches):
        zone_name = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        zones[zone_name] = content[start:end].strip()

    # Content before first zone becomes preamble (usually the slide title)
    preamble = content[: matches[0].start()].strip()
    return preamble, zones


def extract_marks(source: str) -> List[Tuple[int, str]]:
    """Return a list of (char_offset, title) for every <!-- MARK: ... --> comment.

    The offset points to the start of the comment so it can be compared against
    the character positions of each raw slide chunk after splitting on ``---``.
    """
    mark_pattern = re.compile(r"<!--\s*MARK:\s*(.+?)\s*-->")
    return [(m.start(), m.group(1)) for m in mark_pattern.finditer(source)]


def parse_deck(source: str, default_layout: str = "body") -> List[Slide]:
    """Parse a full .md deck string into a list of Slide objects."""
    # Pre-pass: collect MARK positions before any splitting modifies offsets.
    marks = extract_marks(source)

    # Split on slide breaks (--- on its own line)
    raw_slides = re.split(r"^\s*---\s*$", source, flags=re.MULTILINE)

    # Build chunk start offsets by walking separator matches in the source.
    # chunk_offsets[i] is the character position where raw_slides[i] begins.
    chunk_offsets: List[int] = [0]
    for m in re.finditer(r"^\s*---\s*$", source, flags=re.MULTILINE):
        chunk_offsets.append(m.end())

    # For each MARK, find which raw chunk it lives in and attach the chapter
    # title to that same slide. The MARK comment sits inside the slide body
    # it names, not before the separator that precedes it.
    # Last MARK in a chunk wins if there are multiple.
    mark_for_chunk: dict = {}
    for mark_offset, mark_title in marks:
        for i, start in enumerate(chunk_offsets):
            end = chunk_offsets[i + 1] if i + 1 < len(chunk_offsets) else len(source)
            if start <= mark_offset < end:
                mark_for_chunk[i] = mark_title
                break

    slides = []
    for i, raw in enumerate(raw_slides):
        if not raw.strip():
            continue

        # Split on notes delimiter %%%
        parts = re.split(r"^\s*%%%\s*$", raw, maxsplit=1, flags=re.MULTILINE)
        slide_body = parts[0].strip()
        notes = parts[1].strip() if len(parts) > 1 else ""

        # Check for explicit layout override: first line like "::layout:name::"
        explicit_layout = None
        layout_marker = re.match(r"^::layout:([^\s:]+)::\s*$", slide_body, re.MULTILINE)
        if layout_marker:
            explicit_layout = layout_marker.group(1)
            slide_body = slide_body[layout_marker.end():].strip()

        # Parse zone markers
        content, zones = parse_zones(slide_body)

        # Determine layout
        if explicit_layout:
            layout = explicit_layout
        else:
            layout = detect_layout(content, zones) or default_layout

        slides.append(Slide(
            index=len(slides),
            layout=layout,
            content=content,
            notes=notes,
            zones=zones,
            chapter=mark_for_chunk.get(i),
        ))

    return slides
