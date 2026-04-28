"""
Export utilities for Pitchfork
"""
from pathlib import Path
import base64
import mimetypes
import os
import re
import shutil
import sys
import tempfile
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


def _embed_local_images(html: str, deck_dir: Path) -> str:
    """Replace relative <img src="..."> paths with base64 data URIs."""
    def replace(m: re.Match) -> str:
        src = m.group(1)
        if src.startswith(("data:", "http:", "https:", "//")):
            return m.group(0)
        img_path = deck_dir / (src[1:] if src.startswith("/") else src)
        if img_path.exists():
            mime = mimetypes.guess_type(str(img_path))[0] or "image/png"
            b64 = base64.b64encode(img_path.read_bytes()).decode()
            return f'src="data:{mime};base64,{b64}"'
        return m.group(0)
    return re.sub(r'src="([^"]+)"', replace, html)


# Measures whether .slide-layout overflows its container and returns the scale
# needed to fit it, or 1.0 if it fits already.
#
# pre/code elements default to overflow:auto + flex:1, which hides their true
# height from scrollHeight. We release them first so the full content is visible
# to the measurement, then compute scale from scroll vs client dimensions.
_MEASURE_SCALE_JS = """
() => {
    const slide = document.querySelector('.export-slide');
    if (!slide) return 1.0;
    const inner = slide.querySelector('.slide-layout') || slide;

    // Release pre elements from flex/scroll containment so their full height is measurable.
    inner.querySelectorAll('pre').forEach(p => {
        p.style.overflow = 'visible';
        p.style.maxHeight = 'none';
        p.style.flex = 'none';
        p.style.height = 'auto';
        p.style.whiteSpace = 'pre-wrap';
        p.style.wordBreak = 'break-word';
    });

    // Temporarily make overflow visible so scrollWidth/scrollHeight reflect true content size.
    const prevSlide = slide.style.overflow;
    const prevInner = inner.style.overflow;
    slide.style.overflow = 'visible';
    inner.style.overflow = 'visible';

    const scaleW = slide.clientWidth  / inner.scrollWidth;
    const scaleH = slide.clientHeight / inner.scrollHeight;

    slide.style.overflow = prevSlide;
    inner.style.overflow = prevInner;

    const fit = Math.min(1.0, scaleW, scaleH);
    // Ignore sub-pixel rounding differences.
    return fit >= 0.98 ? 1.0 : Math.max(fit, 0.1);
}
"""


def _build_slide_html(slide_html: str, css: str, head_tags: str,
                      logo_uri: str, index: int, total: int, title: str) -> str:
    logo    = f'<img class="slide-logo" src="{logo_uri}" alt="logo">\n' if logo_uri else ""
    counter = f'<div class="slide-counter">{index + 1} / {total}</div>'
    return (
        f'<!doctype html><html lang="en"><head>'
        f'<meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title} — Slide {index + 1}</title>'
        f'{head_tags}<style>{css}</style>'
        f'</head><body>'
        f'<div class="export-slide">{slide_html}\n{logo}{counter}</div>'
        f'</body></html>'
    )


def export_deck(deck_path: Path, html: bool = False) -> None:
    from pitchfork.parser import parse_deck
    from pitchfork.renderer import render_slide_html, init_layouts

    if not deck_path.exists():
        print(f"  File not found: `{deck_path}`")
        sys.exit(1)

    config = load_config(deck_path)
    ex_cfg = config.get("export", {})
    dk_cfg = config.get("deck", {})

    default_layout = dk_cfg.get("default_layout", "body")
    resolution     = ex_cfg.get("resolution", "1080x720")
    dpi            = float(ex_cfg.get("dpi", 96.0))

    try:
        w, h = map(int, resolution.split("x"))
    except Exception:
        w, h = 1920, 1080

    source = deck_path.read_text(encoding="utf-8")
    slides = parse_deck(source, default_layout)
    total  = len(slides)
    init_layouts(deck_path)

    pkg_dir = Path(__file__).resolve().parent
    pitchfork_css = (pkg_dir / "pitchfork.css").read_text(encoding="utf-8")
    user_css_path = deck_path.parent / "styles.css"
    user_css = user_css_path.read_text(encoding="utf-8") if user_css_path.exists() else ""

    logo_uri = ""
    logo_path = deck_path.parent / "logo.png"
    if logo_path.exists():
        logo_uri = "data:image/png;base64," + base64.b64encode(logo_path.read_bytes()).decode()

    w_in, h_in = w / dpi, h / dpi
    export_css = f"""
    html, body {{ margin: 0; padding: 0; overflow: hidden;
        background: var(--pf-bg, #fff); color: var(--pf-fg, #000);
        -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .export-slide {{ position: relative; box-sizing: border-box;
        width: 100vw; height: 100vh; overflow: hidden; }}
    .export-slide .slide-layout {{ max-width: 100%; box-sizing: border-box; }}
    .export-slide * {{ max-width: 100%; box-sizing: border-box; }}
    .export-slide pre, .export-slide code {{
        white-space: pre-wrap !important;
        word-break: break-word !important;
        overflow-wrap: anywhere !important; }}
    .export-slide table {{ width: 100% !important; table-layout: fixed; }}
    .slide-logo {{ position: fixed; bottom: 1rem; left: 1.5rem;
        height: 2rem; width: auto; opacity: 0.15; pointer-events: none; z-index: 50; }}
    .slide-counter {{ position: fixed; bottom: 1rem; right: 1.5rem;
        font-size: 0.75rem; color: var(--pf-muted, #666);
        font-family: var(--pf-font-code, monospace); opacity: 0.5; }}
    @media print {{
        .export-slide {{ break-after: page; page-break-after: always; display: block !important; }}
    }}
    @page {{ size: {w_in:.4f}in {h_in:.4f}in; margin: 0 }}
    """

    head_tags = """
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Mono:wght@400;500&display=swap">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>
    window.__pf_highlight_done = false;
    document.addEventListener("DOMContentLoaded", () => {
        try {
            if (window.hljs) hljs.highlightAll();
        } finally {
            window.__pf_highlight_done = true;
        }
    });
    </script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <script>
    window.__pf_qr_done = false;
    (function(){
        function pfRenderQRs(root) {
            try {
                root = root || document;
                const nodes = root.querySelectorAll(".pf-qr");
                nodes.forEach(node => {
                    const value = node.dataset.value || "";
                    const rect = node.getBoundingClientRect();
                    const clientW = Math.floor(node.clientWidth || 0);
                    const clientH = Math.floor(node.clientHeight || 0);
                    const availW = clientW || Math.floor(rect.width || 0);
                    const availH = clientH || Math.floor(rect.height || 0);
                    if ((!availW && !availH) || (availW < 16 && availH < 16)) return;
                    let size = 0;
                    if (availW && availH) size = Math.max(16, Math.min(availW, availH));
                    else size = Math.max(16, availW || availH || 16);
                    if (node.dataset.renderedSize && parseInt(node.dataset.renderedSize, 10) === size) return;
                    node.innerHTML = "";
                    try {
                        new QRCode(node, {
                            text: value,
                            width: size,
                            height: size,
                            colorDark: '#000000',
                            colorLight: '#ffffff'
                        });
                        node.dataset.renderedSize = String(size);
                    } catch (e) {
                        node.innerHTML = "";
                        const a = document.createElement('a');
                        a.href = value;
                        a.textContent = value;
                        node.appendChild(a);
                    }
                });
            } catch (e) {
                console.error('pfRenderQRs', e);
            }
        }
        window.pfRenderQRs = pfRenderQRs;
        document.addEventListener('DOMContentLoaded', function() {
            try { pfRenderQRs(); } catch (e) {}
            setTimeout(function(){ window.__pf_qr_done = true; }, 200);
        });
    })();
    </script>
    """
    full_css = f"{pitchfork_css}\n{user_css}\n{export_css}"

    # ── HTML export ──────────────────────────────────────────────────────────
    if html:
        parts = [f'<div class="export-slide">{render_slide_html(s)}</div>' for s in slides]
        slides_html = _embed_local_images("\n".join(parts), deck_path.parent)

        overlay  = (f'<img id="slide-logo" src="{logo_uri}" alt="logo">' if logo_uri else "")
        overlay += f'<div id="slide-counter">1 / {total}</div>'

        html_nav_css = """
        .export-slide { display: none; }
        .export-slide.active { display: block; }
        #slide-logo { position: fixed; bottom: 1rem; left: 1.5rem;
            height: 2rem; width: auto; opacity: 0.15; pointer-events: none; z-index: 50; }
        #slide-counter { position: fixed; bottom: 1rem; right: 1.5rem;
            font-size: 0.75rem; color: var(--pf-muted, #666);
            font-family: var(--pf-font-code, monospace); opacity: 0.5; }
        """

        nav_script = """<script>
(function(){
  const slides = Array.from(document.querySelectorAll('.export-slide'));
  const counter = document.getElementById('slide-counter');
  let idx = 0;
  const show = i => {
    idx = ((i % slides.length) + slides.length) % slides.length;
    slides.forEach((s, n) => s.classList.toggle('active', n === idx));
    if (counter) counter.textContent = `${idx + 1} / ${slides.length}`;
    window.scrollTo(0, 0);
  };
  document.addEventListener('keydown', e => {
    if (e.target.matches('input,textarea')) return;
    if (['ArrowRight','ArrowDown','PageDown',' '].includes(e.key))  { e.preventDefault(); show(idx + 1); }
    if (['ArrowLeft','ArrowUp','PageUp','Backspace'].includes(e.key)) { e.preventDefault(); show(idx - 1); }
  });
  show(0);
})();
</script>"""

        out_html = deck_path.with_suffix(".html")
        out_html.write_text(
            f'<!doctype html><html lang="en"><head>'
            f'<meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{deck_path.name} — Export</title>'
            f'{head_tags}<style>{full_css}\n{html_nav_css}</style>'
            f'</head><body>\n{slides_html}\n{overlay}\n{nav_script}\n</body></html>',
            encoding="utf-8",
        )
        print(f"  Wrote HTML to `{out_html}`!")
        return

    # ── PDF export ───────────────────────────────────────────────────────────
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

    debug = bool(int(os.environ.get("PITCHFORK_EXPORT_DEBUG", "0")))
    out_pdf = deck_path.with_suffix(".pdf")
    tmpdir  = tempfile.mkdtemp(prefix="pitchfork-export-")
    tmp_pdfs: list[str] = []
    scaled_slides: list[tuple[int, int]] = []

    print("  Workin' on it!")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page    = browser.new_page(viewport={"width": w, "height": h})

            for i, s in enumerate(slides):
                slide_html = _embed_local_images(render_slide_html(s), deck_path.parent)
                page.set_content(
                    _build_slide_html(slide_html, full_css, head_tags, logo_uri, i, total, deck_path.name),
                    wait_until="networkidle",
                )
                try:
                    page.emulate_media(media="print")
                    page.wait_for_function("window.__pf_highlight_done === true", timeout=2000)
                except Exception:
                    pass

                scale: float = page.evaluate(_MEASURE_SCALE_JS)
                if debug:
                    print(f"  Slide {i + 1}: scale {scale:.4f}")

                if scale < 0.999:
                    # Overflow: shrink the slide to fit within the page.
                    # We scale the .export-slide element itself using CSS transform
                    # with transform-origin: top left, then shift it to center it.
                    # This avoids body.zoom which incorrectly shifts content rightward.
                    percent = int(round(scale * 100))
                    scaled_slides.append((i + 1, percent))
                    print(f"  Slide {i + 1}: overflow, shrunk to {percent}%")
                    offset_x = round((1.0 - scale) * w / 2, 2)
                    offset_y = round((1.0 - scale) * h / 2, 2)
                    page.evaluate(
                        f"""
                        const el = document.querySelector('.export-slide');
                        el.style.transformOrigin = 'top left';
                        el.style.transform = 'scale({scale}) translate({offset_x / scale}px, {offset_y / scale}px)';
                        """
                    )

                tmp_pdf = os.path.join(tmpdir, f"slide-{i:03}.pdf")
                page.pdf(path=tmp_pdf, print_background=True, prefer_css_page_size=True)
                tmp_pdfs.append(tmp_pdf)

            browser.close()

        if scaled_slides:
            print("  Slides scaled: " + ", ".join(f"{n}:{p}%" for n, p in scaled_slides))

        merger = PdfMerger()
        for ppath in tmp_pdfs:
            merger.append(ppath)
        with open(out_pdf, "wb") as f:
            merger.write(f)
        merger.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"  Exported PDF to `{out_pdf}`!")
