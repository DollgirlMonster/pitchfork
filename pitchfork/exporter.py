"""
Export utilities for Pitchfork
"""
from pathlib import Path
import re
import sys
try:
    import tomllib  # type: ignore
except Exception:
    import tomli as tomllib  # type: ignore
from typing import List


def load_config(deck_path: Path) -> dict:
    sidecar = deck_path.parent / ".pitchfork"
    if sidecar.exists():
        with open(sidecar, "rb") as f:
            return tomllib.load(f)
    return {}


def _rewrite_local_images_to_data_uri(html_str: str, deck_dir: Path) -> str:
    """Replace relative <img src="..."> with base64 data URIs for local files."""
    import base64
    import mimetypes

    def replace_src(m: re.Match) -> str:
        src = m.group(1)
        if src.startswith(("data:", "http:", "https:", "//")):
            return m.group(0)
        
        # Try to resolve the image path
        if src.startswith("/"):
            # Absolute path: try relative to deck directory root
            img_path = deck_dir / src[1:]
        else:
            # Relative path: resolve from deck directory
            img_path = deck_dir / src
        
        if img_path.exists():
            try:
                mime = mimetypes.guess_type(str(img_path))[0] or "image/png"
                b64 = base64.b64encode(img_path.read_bytes()).decode()
                return f'src="data:{mime};base64,{b64}"'
            except Exception:
                pass
        return m.group(0)

    return re.sub(r'src="([^"]+)"', replace_src, html_str)


# Make sure content that overflows the slide dimensions is shrunk 
# to fit rather than being clipped.

# What a fucking hack, I designed myself into a corner. ok:

# JavaScript injected into each slide page before PDF capture.
# Uses `zoom` on .slide-layout (scales everything uniformly).
# pre elements have overflow:auto + flex:1 by default, which means their
# internal content overflow is invisible to the parent's scrollHeight — the
# flex container never sees them as "too tall".  We fix this by:
#   1. Releasing pre elements from flex sizing and internal scrolling so their
#      full natural height expands and overflows the slide layout.
#   2. Using getBoundingClientRect() for measurement, which correctly reflects
#      CSS zoom (unlike scrollHeight which is in unzoomed coordinates).
#   3. NOT restoring pre styles after shrinking — all code must be visible.
# Returns the final scale so Python can log a per-slide warning.
_OVERFLOW_SHRINK_JS = """
() => {
    const slide = document.querySelector('.export-slide');
    if (!slide) return 1.0;
    const inner = slide.querySelector('.slide-layout');
    if (!inner) return 1.0;

    // Expand pre elements to their natural height so overflow is detectable.
    const pres = Array.from(inner.querySelectorAll('pre'));
    pres.forEach(p => {
        p.style.overflow   = 'visible';
        p.style.maxHeight  = 'none';
        p.style.flex       = 'none';
        p.style.height     = 'auto';
    });

    const slideH = slide.getBoundingClientRect().height;
    const slideW = slide.getBoundingClientRect().width;

    let scale = 1.0;
    const minScale = 0.5;
    inner.style.zoom = '100%';

    while (scale > minScale) {
        const r = inner.getBoundingClientRect();
        if (r.height <= slideH && r.width <= slideW) break;
        scale = Math.round((scale - 0.02) * 100) / 100;
        inner.style.zoom = (scale * 100).toFixed(0) + '%';
    }

    // pre styles are intentionally left expanded so all content is visible
    // .export-slide { overflow:hidden } in CSS section clips content outside 
    // the slide if we hit the minScale floor.
    return scale;
}
"""


def export_deck(deck_path: Path, html: bool = False) -> None:
    from pitchfork.parser import parse_deck
    from pitchfork.renderer import render_slide_html, init_layouts

    if not deck_path.exists():
        print(f"  File not found: `{deck_path}`")
        sys.exit(1)

    config = load_config(deck_path)
    default_layout = config.get("deck", {}).get("default_layout", "body")
    resolution = config.get("export", {}).get("resolution", "1920x1080")
    try:
        w_str, h_str = resolution.split("x")
        w, h = int(w_str), int(h_str)
    except Exception:
        w, h = 1920, 1080

    source = deck_path.read_text(encoding="utf-8")
    slides = parse_deck(source, default_layout)
    total = len(slides)

    # Load layouts so pick_layout() works; without this every slide renders as body.
    init_layouts(deck_path)

    pkg_dir = Path(__file__).resolve().parent
    pitchfork_css_path = pkg_dir / "pitchfork.css"
    pitchfork_css = pitchfork_css_path.read_text(encoding="utf-8") if pitchfork_css_path.exists() else ""
    user_css_path = deck_path.parent / "styles.css"
    user_css = user_css_path.read_text(encoding="utf-8") if user_css_path.exists() else ""

    # Logo as data URI (used in both paths so it's always self-contained)
    logo_path = deck_path.parent / "logo.png"
    logo_data_uri = ""
    if logo_path.exists():
        import base64
        try:
            b = logo_path.read_bytes()
            logo_data_uri = "data:image/png;base64," + base64.b64encode(b).decode()
        except Exception:
            logo_data_uri = ""

    # DPI set so that content isn't miniscule in the export
    dpi = 192.0
    w_in = w / dpi
    h_in = h / dpi

    # Special export styles to ensure the output is correctly sized and formatted
    export_styles = f"""
    html,body {{ margin:0; padding:0; overflow:hidden; background:var(--pf-bg, #fff); color:var(--pf-fg,#000); -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .export-slide {{ position: relative; box-sizing: border-box; width: 100vw; height: 100vh; break-after: page; page-break-after: always; overflow: hidden; }}
    #slide-logo {{ position: absolute; bottom: 12px; left: 12px; width: 64px; height: auto; }}
    #slide-counter {{ position: absolute; bottom: 12px; right: 12px; font-size: 14px; color: var(--pf-muted, #666); }}
    @page {{ size: {w_in:.4f}in {h_in:.4f}in; margin: 0 }}
    """

    highlight_css = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">'
    highlight_script = '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>'
    highlight_init = '<script>document.addEventListener("DOMContentLoaded", ()=>{if(window.hljs) hljs.highlightAll();});</script>'
    # TODO: Don't hardcode typeface; find URIs in css sidecar and embed those
    google_fonts = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Mono:wght@400;500&display=swap">'

    # --html: build a self-contained single HTML file and exit
    # All CSS is inlined; content images and logo are embedded as data URIs.
    if html:
        parts: List[str] = []
        for i, s in enumerate(slides):
            slide_html = render_slide_html(s)
            piece = f'<div class="export-slide">{slide_html}'
            if logo_data_uri:
                piece += f'<img id="slide-logo" src="{logo_data_uri}" alt="logo">'
            piece += f'<div id="slide-counter">{i + 1} / {total}</div></div>'
            parts.append(piece)

        slides_html = "\n".join(parts)
        # Embed local content images so the file is fully self-contained
        slides_html = _rewrite_local_images_to_data_uri(slides_html, deck_path.parent)

        out_html = deck_path.with_suffix(".html")
        doc = (
            f'<!doctype html>\n<html lang="en">\n<head>\n'
            f'<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{deck_path.name} — Export</title>\n'
            f'{google_fonts}\n{highlight_css}\n'
            f'<style>{pitchfork_css}\n{user_css}\n{export_styles}</style>\n'
            f'{highlight_script}\n{highlight_init}\n'
            f'</head>\n<body>\n{slides_html}\n</body>\n</html>'
        )
        out_html.write_text(doc, encoding="utf-8")
        print(f"  Wrote HTML dump to `{out_html}`!")
        return

    # PDF export: render each slide using Playwright, then merge the resulting PDFs with PyPDF2
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("  Export requires 'playwright'. Install with: pip install playwright && playwright install chromium")
        sys.exit(1)

    try:
        from PyPDF2 import PdfMerger
    except Exception:
        print("  PDF merging requires PyPDF2. Install with: pip install PyPDF2")
        sys.exit(1)

    out_pdf = deck_path.with_suffix(".pdf")
    import tempfile, os, shutil

    print(f"  Workin' on it!")
    tmpdir = tempfile.mkdtemp(prefix="pitchfork-export-")
    tmp_pdfs: List[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Viewport must match slide pixel dimensions so vw/vh units, clamp(),
            # and grid/flex layout all resolve against the correct slide geometry.
            page = browser.new_page(viewport={"width": w, "height": h})
            for i, s in enumerate(slides):
                slide_html = render_slide_html(s)
                # Rewrite local image src to data URIs so Playwright doesn't need
                # filesystem access (avoids any base_url API version differences)
                slide_html = _rewrite_local_images_to_data_uri(slide_html, deck_path.parent)
                single_html = (
                    f'<!doctype html>\n<html lang="en">\n<head>\n'
                    f'<meta charset="utf-8">\n'
                    f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
                    f'<title>{deck_path.name} — Slide {i + 1}</title>\n'
                    f'{google_fonts}\n{highlight_css}\n'
                    f'<style>{pitchfork_css}\n{user_css}\n{export_styles}</style>\n'
                    f'{highlight_script}\n{highlight_init}\n'
                    f'</head>\n<body>\n'
                    f'<div class="export-slide">{slide_html}\n'
                )
                if logo_data_uri:
                    single_html += f'<img id="slide-logo" src="{logo_data_uri}" alt="logo">\n'
                single_html += f'<div id="slide-counter">{i + 1} / {total}</div>\n'
                single_html += "</div>\n</body>\n</html>"

                page.set_content(single_html, wait_until="networkidle")

                # Shrink font if content overflows the slide boundary
                scale: float = page.evaluate(_OVERFLOW_SHRINK_JS)
                if scale < 0.99:
                    print(f"  Slide {i + 1}: text overflow detected, shrunk to {int(round(scale * 100))}%")

                tmp_pdf = os.path.join(tmpdir, f"slide-{i:03}.pdf")
                page.pdf(path=tmp_pdf, print_background=True, prefer_css_page_size=True)
                tmp_pdfs.append(tmp_pdf)
            browser.close()

        merger = PdfMerger()
        for ppath in tmp_pdfs:
            merger.append(ppath)
        with open(out_pdf, "wb") as f:
            merger.write(f)
        merger.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"  Exported PDF to `{out_pdf}`!")
