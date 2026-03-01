"""
Export utilities for Pitchfork
"""
from pathlib import Path
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


def export_deck(deck_path: Path, html: bool = False) -> None:
    from pitchfork.parser import parse_deck
    from pitchfork.renderer import render_slide_html

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

    pkg_dir = Path(__file__).resolve().parent
    pitchfork_css_path = pkg_dir / "pitchfork.css"
    pitchfork_css = pitchfork_css_path.read_text(encoding="utf-8") if pitchfork_css_path.exists() else ""
    user_css_path = deck_path.parent / "styles.css"
    user_css = user_css_path.read_text(encoding="utf-8") if user_css_path.exists() else ""

    # Prepare logo
    logo_path = deck_path.parent / "logo.png"
    logo_data_uri = ""
    if logo_path.exists():
        import base64
        try:
            b = logo_path.read_bytes()
            logo_data_uri = "data:image/png;base64," + base64.b64encode(b).decode()
        except Exception:
            logo_data_uri = ""

    # Build HTML parts for HTML-folder (references) and PDF (data URI)
    slides_html_html_parts: List[str] = []
    slides_html_pdf_parts: List[str] = []
    total = len(slides)
    for idx, s in enumerate(slides, start=1):
        body_html = render_slide_html(s)
        html_piece = f'<div class="export-slide">{body_html}'
        if logo_path.exists():
            html_piece += '<img id="slide-logo" src="logo.png" alt="logo">'
        html_piece += f'<div id="slide-counter">{idx} / {total}</div></div><div class="page-break" style="page-break-after: always;"></div>'
        slides_html_html_parts.append(html_piece)

        pdf_piece = f'<div class="export-slide">{body_html}'
        if logo_data_uri:
            pdf_piece += f'<img id="slide-logo" src="{logo_data_uri}" alt="logo">'
        pdf_piece += f'<div id="slide-counter">{idx} / {total}</div></div><div class="page-break" style="page-break-after: always;"></div>'
        slides_html_pdf_parts.append(pdf_piece)

    slides_html = "\n".join(slides_html_pdf_parts)
    slides_html_html = "\n".join(slides_html_html_parts)

    # Convert pixel resolution to inches (96 DPI fallback)
    dpi = 120.0
    w_in = w / dpi
    h_in = h / dpi

    export_styles = f"""
    html,body {{ margin:0; padding:0; background:var(--pf-bg, #fff); color:var(--pf-fg,#000); -webkit-print-color-adjust: exact; }}
    .export-slide {{ position: relative; box-sizing: border-box; width: {w_in:.2f}in; height: {h_in:.2f}in; break-after: page; page-break-after: always; overflow: hidden; display: block; padding: 0.5in; }}
    #slide-logo {{ position: absolute; bottom: 12px; left: 12px; width: 64px; height: auto; }}
    #slide-counter {{ position: absolute; bottom: 12px; right: 12px; font-size: 14px; color: var(--pf-muted, #666); }}
    @page {{ size: {w_in:.2f}in {h_in:.2f}in; margin: 0 }}
    """

    # HTML folder export
    if html:
        export_dir = deck_path.parent / f"{deck_path.stem}.export"
        export_dir.mkdir(parents=True, exist_ok=True)

        if pitchfork_css:
            (export_dir / "pitchfork.css").write_text(pitchfork_css, encoding="utf-8")
        if user_css:
            (export_dir / "styles.css").write_text(user_css, encoding="utf-8")
        if logo_path.exists():
            # copy logo.png to export folder
            try:
                (export_dir / "logo.png").write_bytes(logo_path.read_bytes())
            except Exception:
                pass

        links = ''
        if pitchfork_css:
            links += '<link rel="stylesheet" href="pitchfork.css">\n'
        if user_css:
            links += '<link rel="stylesheet" href="styles.css">\n'

        index_html = f"""<!doctype html>
<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n<title>{deck_path.name} — Export</title>\n{links}<style>{export_styles}</style>\n</head>\n<body>\n{slides_html_html}\n</body>\n</html>"""

        (export_dir / "index.html").write_text(index_html, encoding="utf-8")
        print(f"  Wrote HTML export to `{export_dir}`!")
        return

    # PDF export: render each slide separately and merge
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

    highlight_css = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">'
    highlight_script = '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>'
    highlight_init = '<script>document.addEventListener("DOMContentLoaded", ()=>{if(window.hljs) hljs.highlightAll();});</script>'
    google_fonts = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Mono:wght@400;500&display=swap">'

    out_pdf = deck_path.with_suffix('.pdf')
    import tempfile, os, shutil

    print(f"  Workin' on it!")
    tmpdir = tempfile.mkdtemp(prefix="pitchfork-export-")
    tmp_pdfs: List[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            for i, s in enumerate(slides):
                single_html = f"""<!doctype html>
<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n<title>{deck_path.name} — Slide {i+1}</title>\n{google_fonts}\n{highlight_css}\n<style>{pitchfork_css}\n{user_css}\n{export_styles}</style>\n{highlight_script}\n{highlight_init}\n</head>\n<body>\n<div class=\"export-slide\">{render_slide_html(s)}"""
                if logo_data_uri:
                    single_html += f"<img id=\"slide-logo\" src=\"{logo_data_uri}\" alt=\"logo\">"
                single_html += f"<div id=\"slide-counter\">{i+1} / {total}</div>"
                single_html += "</div>\n</body>\n</html>"
                page.set_content(single_html, wait_until="networkidle")
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
