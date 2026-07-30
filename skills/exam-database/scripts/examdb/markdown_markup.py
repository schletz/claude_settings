"""Markdown syntax for task sheets."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .data_model_markdown import render_data_model
from .dialect import Dialect
from .markup import Markup
from .schema import Schema
from .sqlite_tools import format_table


class MarkdownMarkup(Markup):
    """Markdown; the data model is a column table per table, since Markdown has no diagrams."""

    def document_start(self, title: str) -> list[str]:
        return [f"# {title}", ""]

    def heading(self, level: int, text: str) -> str:
        return f"{'#' * level} {text}"

    def bold(self, text: str) -> str:
        return f"**{text}**"

    def table(self, columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
        return format_table(list(columns), [tuple(r) for r in rows])

    def code(self, sql: str) -> str:
        return f"```sql\n{sql.strip()}\n```"

    def data_model(self, schema: Schema, dialect: Dialect, er_layout: Sequence[str]) -> str:
        return render_data_model(schema, dialect)
