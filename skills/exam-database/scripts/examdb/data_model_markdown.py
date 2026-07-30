"""Markdown description of the schema for the students' task sheet."""

from __future__ import annotations

from .dialect import Dialect
from .schema import Schema
from .table import Table


def render_data_model(schema: Schema, dialect: Dialect) -> str:
    """Lists every table with its description, column types (in the target dialect), keys and nullability."""
    parts = ["## Datenmodell", ""]
    for table in schema.tables:
        parts += [f"### {table.name}", ""]
        if table.description:
            parts += [table.description, ""]
        parts += ["| Spalte | Typ | Schlüssel | NULL erlaubt |", "|---|---|---|---|"]
        parts += [_column_row(table, name, dialect) for name in (c.name for c in table.columns)]
        parts.append("")
    return "\n".join(parts)


def _column_row(table: Table, name: str, dialect: Dialect) -> str:
    column = table.column(name)
    keys = []
    if name in table.primary_key:
        keys.append("PK")
    if column.references:
        keys.append(f"FK → {column.references[0]}.{column.references[1]}")
    if column.unique or any(name in group for group in table.unique):
        keys.append("UNIQUE")
    column_type = dialect.column_type(column) + (" (auto)" if column.identity else "")
    return f"| {name} | {column_type} | {', '.join(keys)} | {'ja' if column.nullable else 'nein'} |"
