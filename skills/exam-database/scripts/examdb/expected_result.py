"""What the students are told about the correct result of a task."""

from __future__ import annotations

import sqlite3

from .markdown_markup import MarkdownMarkup
from .markup import Markup
from .query import Query
from .sqlite_tools import run_dml_on_copy, run_select, split_statements

# result: result table, count: number of rows, both: both, none: no hint at all.
HINT_MODES = ("result", "count", "both", "none")


def describe_expected(connection: sqlite3.Connection, query: Query, mode: str,
                      markup: Markup | None = None) -> list[str]:
    """Paragraphs describing the expected outcome of a task.

    The outcome is computed on the SQLite build database. DML tasks have no result table,
    so every mode except 'none' reports the number of affected rows for them.

    Args:
        connection: Build database.
        query: Task whose solution is executed.
        mode: One of HINT_MODES.
        markup: Document syntax; Markdown if omitted.

    Returns:
        Paragraphs without trailing blank lines; empty for mode 'none'.
    """
    if mode == "none":
        return []
    markup = markup or MarkdownMarkup()
    sql = query.sql_for("sqlite")
    if query.is_dml:
        affected = run_dml_on_copy(connection, sql).rowcount
        total = " (alle Anweisungen zusammen)" if len(split_statements(sql)) > 1 else ""
        return [f"Betroffene Datensätze{total}: {markup.bold(str(affected))}"]
    columns, rows = run_select(connection, sql)
    paragraphs = []
    if mode in ("count", "both"):
        paragraphs.append(f"Anzahl der Datensätze im Ergebnis: {markup.bold(str(len(rows)))}")
    if mode in ("result", "both"):
        paragraphs.append(markup.table(columns, rows))
    return paragraphs
