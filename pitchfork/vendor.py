"""
Inlines remote assets for exported HTML decks

This module fetches remote assets, caches them under ``~/.cache/pitchfork/vendor/``, 
and rewrites the head tags and CSS to embed them as data URIs. 

Anything that can't be fetched keeps its original URL
"""
import base64
import hashlib
import re
import urllib.error
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

CACHE_DIR = Path.home() / ".cache" / "pitchfork" / "vendor"

# Google Fonts serves woff2 only to user agents it recognises as modern. 
# With urllib's default UA the same family comes back as format('truetype'):
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_TIMEOUT = 15

# Failures are per-URL
_failures: List[Tuple[str, str]] = []


def begin_run() -> None:
    """Reset per-export state. Called by vendor_assets()."""
    global _failures
    _failures = []


def last_failures() -> List[Tuple[str, str]]:
    """[(url, reason)] for everything that couldn't be fetched in the last run."""
    return list(_failures)


def fetch(url: str, cache_dir: Optional[Path] = None) -> Optional[Tuple[bytes, str]]:
    """Return ``(body, content_type)`` for a remote URL, or None if unreachable

    Successful fetches are cached, so once a deck has been exported every later export works offline
    """
    cache = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
    blob, meta = cache / f"{key}.bin", cache / f"{key}.type"

    if blob.exists():
        content_type = meta.read_text(encoding="utf-8").strip() if meta.exists() else ""
        return blob.read_bytes(), content_type

    try:
        req = Request(url, headers={"User-Agent": _UA})
        with urlopen(req, timeout=_TIMEOUT) as resp:
            body = resp.read()
            content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    except urllib.error.HTTPError as exc:
        # A stale or moved URL. Nothing to do with the network
        # Must precede URLError, because HTTPError is a subclass of it
        _failures.append((url, f"HTTP {exc.code}"))
        return None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            _failures.append((url, "timed out"))
        else:
            _failures.append((url, str(exc.reason)))
        return None
    except TimeoutError:
        _failures.append((url, "timed out"))
        return None
    except Exception as exc:
        _failures.append((url, type(exc).__name__))
        return None

    try:
        cache.mkdir(parents=True, exist_ok=True)
        blob.write_bytes(body)
        meta.write_text(content_type, encoding="utf-8")
    except OSError:
        pass  # We can't write the cache, but the fetch worked, so eh

    return body, content_type


from pitchfork.server import MIME_TYPES
def _data_uri(body: bytes, content_type: str, url: str) -> str:
    mime = content_type or MIME_TYPES.get(
        Path(urlparse(url).path).suffix.lower(), "application/octet-stream"
    )
    return f"data:{mime};base64,{base64.b64encode(body).decode('ascii')}"


# MARK: CSS
_CSS_URL_RE = re.compile(r"""url\(\s*(?P<q>["']?)(?P<url>[^"')]+)(?P=q)\s*\)""")
_CSS_IMPORT_RE = re.compile(
    r"""@import\s+(?:url\(\s*(?P<q1>["']?)(?P<u1>[^"')]+)(?P=q1)\s*\)"""
    r"""|(?P<q2>["'])(?P<u2>[^"']+)(?P=q2))[^;]*;""",
    re.IGNORECASE,
)


def inline_css_urls(css: str, base_url: str = "", cache_dir: Optional[Path] = None) -> str:
    """Replace remote ``url(...)`` references (fonts etc.) with data URIs."""
    def repl(m: re.Match) -> str:
        raw = m.group("url").strip()
        if raw.startswith(("data:", "#")):
            return m.group(0)
        abs_url = urljoin(base_url, raw)
        if not abs_url.startswith(("http://", "https://")):
            return m.group(0)
        got = fetch(abs_url, cache_dir)
        if got is None:
            return m.group(0)
        return f'url("{_data_uri(got[0], got[1], abs_url)}")'

    return _CSS_URL_RE.sub(repl, css)


def inline_css_imports(
    css: str, base_url: str = "", cache_dir: Optional[Path] = None, _depth: int = 0
) -> str:
    """Replace ``@import url(remote)`` with the imported stylesheet's own rules,
    so the fonts it pulls in still work with no network connection.
    """
    if _depth > 3:
        return css

    def repl(m: re.Match) -> str:
        url = (m.group("u1") or m.group("u2") or "").strip()
        abs_url = urljoin(base_url, url)
        if not abs_url.startswith(("http://", "https://")):
            return m.group(0)
        got = fetch(abs_url, cache_dir)
        if got is None:
            return m.group(0)
        text = got[0].decode("utf-8", errors="replace")
        text = inline_css_imports(text, abs_url, cache_dir, _depth + 1)
        return inline_css_urls(text, abs_url, cache_dir)

    return _CSS_IMPORT_RE.sub(repl, css)


# MARK: Head tags

_LINK_RE = re.compile(
    r"""<link\b[^>]*\bhref=(?P<q>["'])(?P<href>https?://[^"']+)(?P=q)[^>]*>""", re.IGNORECASE
)
_SCRIPT_RE = re.compile(
    r"""<script\b[^>]*\bsrc=(?P<q>["'])(?P<src>https?://[^"']+)(?P=q)[^>]*>\s*</script\s*>""",
    re.IGNORECASE,
)


def _escape_closing_tag(text: str, tag: str) -> str:
    """Stop a fetched payload from closing the block we're embedding it in."""
    return re.sub(rf"</(?={tag}\b)", lambda _m: "<\\/", text, flags=re.IGNORECASE)


def inline_head_tags(head_html: str, cache_dir: Optional[Path] = None) -> str:
    """Turn remote ``<link rel=stylesheet>`` and ``<script src>`` into inline blocks."""
    def link_repl(m: re.Match) -> str:
        tag = m.group(0)
        if "stylesheet" not in tag.lower():
            return tag
        url = m.group("href")
        got = fetch(url, cache_dir)
        if got is None:
            return tag
        css = got[0].decode("utf-8", errors="replace")
        css = inline_css_imports(css, url, cache_dir)
        css = inline_css_urls(css, url, cache_dir)
        return f"<style>\n{_escape_closing_tag(css, 'style')}\n</style>"

    def script_repl(m: re.Match) -> str:
        url = m.group("src")
        got = fetch(url, cache_dir)
        if got is None:
            return m.group(0)
        js = got[0].decode("utf-8", errors="replace")
        return f"<script>\n{_escape_closing_tag(js, 'script')}\n</script>"

    head_html = _LINK_RE.sub(link_repl, head_html)
    return _SCRIPT_RE.sub(script_repl, head_html)


def vendor_assets(
    head_tags: str, css_parts: List[str], cache_dir: Optional[Path] = None
) -> Tuple[str, List[str], int]:
    """Inline every remote asset reachable from the head tags and each CSS block.

    Returns ``(head_tags, vendored_css_parts, bytes_added)``.
    """
    begin_run()
    before = len(head_tags) + sum(len(c) for c in css_parts)
    head_tags = inline_head_tags(head_tags, cache_dir)
    vendored = []
    for css in css_parts:
        css = inline_css_imports(css, "", cache_dir)
        css = inline_css_urls(css, "", cache_dir)
        vendored.append(css)
    after = len(head_tags) + sum(len(c) for c in vendored)
    return head_tags, vendored, after - before
