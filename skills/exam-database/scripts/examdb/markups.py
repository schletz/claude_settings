"""Lookup of the sheet markup by file extension."""

from __future__ import annotations

from pathlib import Path

from .asciidoc_markup import AsciiDocMarkup
from .markdown_markup import MarkdownMarkup
from .markup import Markup

MARKUP_EXTENSIONS: tuple[str, ...] = (".md", ".adoc")


def markup_for(path: Path | None) -> Markup:
    """Markup matching the output file; Markdown for console output.

    Raises:
        ValueError: If the extension is neither .md nor .adoc.
    """
    if path is None or path.suffix.lower() == ".md":
        return MarkdownMarkup()
    if path.suffix.lower() == ".adoc":
        return AsciiDocMarkup()
    raise ValueError(f"Output must end with one of {', '.join(MARKUP_EXTENSIONS)}, got '{path.name}'.")
