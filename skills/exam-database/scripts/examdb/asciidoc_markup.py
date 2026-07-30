"""AsciiDoc syntax for task sheets, ready for asciidoctor-pdf."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from .data_model_asciidoc import render_data_model
from .dialect import Dialect
from .markup import Markup
from .schema import Schema
from .sqlite_tools import format_cell

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")


class AsciiDocMarkup(Markup):
    """AsciiDoc with one sentence per line; the data model is a PlantUML ER diagram."""

    def document_start(self, title: str) -> list[str]:
        return [f"= {title}", ":source-highlighter: rouge", ":icons: font", ":lang: DE", ":hyphens:",
                ":figure-caption!:", ":toc!:", ""]

    def heading(self, level: int, text: str) -> str:
        return f"{'=' * level} {text}"

    def paragraph(self, text: str) -> str:
        # One sentence per line keeps diffs readable; AsciiDoc joins the lines again.
        return _SENTENCE_END.sub("\n", text.strip())

    def bold(self, text: str) -> str:
        return f"*{text}*"

    def table(self, columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
        # autowidth sizes columns to their content; narrow results would otherwise span the page.
        lines = ["[%header%autowidth]", "|===", "| " + " | ".join(columns), ""]
        for row in rows:
            lines += [f"| {format_cell(v)}" for v in row] + [""]
        return "\n".join(lines + ["|==="])

    def code(self, sql: str) -> str:
        return f"[source,sql]\n----\n{sql.strip()}\n----"

    def data_model(self, schema: Schema, dialect: Dialect, er_layout: Sequence[str]) -> str:
        return render_data_model(schema, dialect, er_layout)
