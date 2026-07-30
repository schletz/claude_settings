#!/usr/bin/env python3
"""Convert a right-to-left AsciiDoc file (Arabic, Hebrew, Persian) to PDF.

asciidoctor-pdf cannot shape Arabic letters or lay out right-to-left text. This script
renders the document with the HTML backend of the asciidoctor/docker-asciidoctor image,
injects assets/rtl.css and prints the page to PDF with Playwright's Chromium.

Usage:
    python convert_rtl_to_pdf.py <working_dir> <adoc_filename>

- working_dir: directory containing the .adoc file (mounted into the container).
- adoc_filename: name of the .adoc file, relative to working_dir.
"""
import argparse
import os
import pathlib
import re
import shlex
import sys
import uuid

from convert_to_pdf import cleanup_generated_svgs, run_in_container

RTL_CSS = pathlib.Path(__file__).resolve().parent.parent / "assets" / "rtl.css"
FOOTER_TEMPLATE = (
    '<div style="width:100%;text-align:center;font-size:9px;color:#555;'
    'font-family:Segoe UI,Arial,sans-serif"><span class="pageNumber"></span></div>'
)


def build_shell_command(adoc_filename: str, html_filename: str) -> str:
    parts = [
        "asciidoctor",
        "-r", "asciidoctor-mathematical",
        "-r", "asciidoctor-diagram",
        "-a", "allow-uri-read",
        "-a", "stem",
        "-a", "mathematical-format=svg",
        # Embed diagrams as data URIs, so the HTML is self-contained and the SVGs can be removed.
        "-a", "data-uri",
        # Web fonts and the Font Awesome icons come from a CDN and have no Arabic glyphs.
        "-a", "webfonts!",
        "-a", "icons!",
        "-a", "nofooter",
        "-o", html_filename,
        adoc_filename,
    ]
    command = " ".join(shlex.quote(p) for p in parts)
    return f"{command} && rm -rf .asciidoctor"


def apply_rtl(html: str, css: str) -> str:
    """Set dir="rtl" on the root element and append the RTL stylesheet to the head."""
    html = re.sub(r"<html\b", '<html dir="rtl"', html, count=1)
    return html.replace("</head>", f"<style>\n{css}\n</style>\n</head>", 1)


def print_to_pdf(html_path: str, pdf_path: str) -> None:
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright for Python is missing. Install it with "
            "'pip install playwright' and 'python -m playwright install chromium'."
        )
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(pathlib.Path(html_path).as_uri(), wait_until="load")
            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={"top": "2cm", "bottom": "2cm", "left": "1.8cm", "right": "1.8cm"},
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=FOOTER_TEMPLATE,
            )
            browser.close()
    except PlaywrightError as exc:
        raise RuntimeError(
            f"Printing with Chromium failed. If the browser is missing, run "
            f"'python -m playwright install chromium'. ({exc})"
        )


def convert(working_dir: str, adoc_filename: str) -> str:
    working_dir = os.path.abspath(working_dir)
    adoc_path = os.path.join(working_dir, adoc_filename)
    if not os.path.isfile(adoc_path):
        raise FileNotFoundError(f"AsciiDoc file not found: {adoc_path}")

    basename, _ = os.path.splitext(adoc_filename)
    pdf_path = os.path.join(working_dir, f"{basename}.pdf")
    # The HTML is an intermediate file next to the source, hidden and unique like the theme copy.
    html_filename = f".asciidoc-rtl-{uuid.uuid4().hex}.html"
    html_path = os.path.join(working_dir, html_filename)

    try:
        run_in_container(working_dir, build_shell_command(adoc_filename, html_filename))
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(apply_rtl(html, RTL_CSS.read_text(encoding="utf-8")))
        print_to_pdf(html_path, pdf_path)
    finally:
        if os.path.isfile(html_path):
            os.remove(html_path)
        cleanup_generated_svgs(working_dir)

    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("working_dir", help="Directory containing the .adoc file")
    parser.add_argument("adoc_filename", help="Name of the .adoc file, relative to working_dir")
    args = parser.parse_args()

    try:
        pdf_path = convert(args.working_dir, args.adoc_filename)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"PDF created: {pdf_path}")


if __name__ == "__main__":
    main()
