"""Turns a file on disk into a BundleFile: text, converted document or binary."""

from __future__ import annotations

import functools
import os
import re
import sys
from pathlib import Path

from bundle_format import BundleFile, normalize_text

# Binary formats that store text and are embedded as Markdown.
CONVERTIBLE = {".pdf", ".docx", ".xlsx", ".xls", ".pptx", ".epub", ".msg"}

# Languages whose type declarations are listed in the TOC.
_TYPE_LANGUAGES = {".cs", ".java"}
_TYPE_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|abstract|sealed|partial|final"
    r"|readonly|file|ref|unsafe|new|non-sealed|strictfp)\s+)*"
    r"((?:record\s+(?:class|struct)|class|interface|record|enum|struct)\s+\w+[^{;]*)"
)

def read_file(path: Path, bundle_path: str) -> BundleFile:
    """Read ``path`` and store it under ``bundle_path`` as text, Markdown or binary."""
    data = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix in CONVERTIBLE:
        text = _convert(path)
        if text is not None:
            return BundleFile(bundle_path, normalize_text(text), converted=suffix[1:])
    elif b"\x00" not in data[:8192]:
        text = normalize_text(_decode(data))
        types = _extract_types(text) if suffix in _TYPE_LANGUAGES else ""
        return BundleFile(bundle_path, text, types=types)
    return BundleFile(bundle_path, None, size=len(data))


def _decode(data: bytes) -> str:
    """Decode UTF-8 (with or without BOM); fall back to the Windows codepage."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


@functools.cache
def _markitdown():
    # Imported lazily: both converters are slow to load and only needed for documents.
    from markitdown import MarkItDown  # pylint: disable=import-outside-toplevel
    return MarkItDown()


def _convert_markitdown(path: Path) -> str:
    return _markitdown().convert(str(path)).text_content


def _convert_pymupdf(path: Path) -> str:
    import pymupdf  # pylint: disable=import-outside-toplevel
    # The layout parser prints status messages to stdout; they are not content.
    pymupdf.set_messages(path=os.devnull)
    with pymupdf.open(path) as document:
        return document.to_markdown()


def _convert(path: Path) -> str | None:
    """Convert a document to Markdown, or return None if no converter works.

    PyMuPDF keeps headings and tables of PDFs intact, where markitdown splits
    table cells into loose lines. For Office formats markitdown is better: it
    reads the document structure (lists, emphasis), while PyMuPDF renders the
    file to PDF first and has to guess it.
    """
    converters = [_convert_pymupdf, _convert_markitdown] if path.suffix.lower() == ".pdf" else [_convert_markitdown]
    for convert in converters:
        try:
            return convert(path)
        except ImportError:
            continue
        except Exception as e:  # pylint: disable=broad-exception-caught  # converters raise many types
            print(f"warning: cannot convert {path.name} ({e}), stored as binary", file=sys.stderr)
            return None
    print(f"warning: no converter installed (pip install pymupdf markitdown[all]), {path.name} is stored as binary",
          file=sys.stderr)
    return None


def _extract_types(text: str) -> str:
    """List type declarations, e.g. 'class Candidate : Person; enum Rating'."""
    declarations = []
    for line in text.split("\n"):
        if line.lstrip().startswith(("//", "*", "/*")):
            continue
        if m := _TYPE_RE.match(line):
            declaration = re.sub(r"\([^)]*\)?", "", m.group(1))  # drop primary ctor parameters
            declaration = re.split(r"\s+where\s+", declaration)[0]
            declarations.append(" ".join(declaration.split()))
    return "; ".join(declarations)
