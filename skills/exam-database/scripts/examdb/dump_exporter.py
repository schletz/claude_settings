"""Rendering of a complete SQL dump (schema + data) from a built SQLite database."""

from __future__ import annotations

import sqlite3
from typing import Any

from .dialect import Dialect
from .schema import Schema
from .table import Table


class DumpExporter:
    """Writes schema and data of the SQLite build database as a script for one dialect.

    The SQLite database is the single source of truth: it already contains the fixtures
    and the effects of ``post_sql``, so every dialect receives exactly the verified data.
    """

    def __init__(self, schema: Schema, dialect: Dialect, connection: sqlite3.Connection) -> None:
        self._schema = schema
        self._dialect = dialect
        self._connection = connection

    def render(self) -> str:
        """Returns the dump as a single string."""
        tables = self._schema.tables
        data = {t.name: self._read_rows(t) for t in tables}
        summary = ", ".join(f"{t.name} ({len(data[t.name])})" for t in tables)
        out: list[str] = [
            f"-- Database: {self._schema.name}",
            f"-- Dialect: {self._dialect.name}",
            f"-- Tables: {summary}",
            "",
            *self._dialect.header(),
            *(self._dialect.drop_table(t) for t in reversed(tables)),
            "",
        ]
        for table in tables:
            out += [self._dialect.create_table(table), ""]
        out.append("BEGIN TRANSACTION;")
        for table in tables:
            out += self._dialect.before_inserts(table)
            out += (self._insert(table, row) for row in data[table.name])
            out += self._dialect.after_inserts(table)
            out.append("")
        out.append("COMMIT;")
        out += self._dialect.after_data(tables)
        return "\n".join(out) + "\n"

    def _read_rows(self, table: Table) -> list[dict[str, Any]]:
        names = [c.name for c in table.columns]
        order = ", ".join(table.primary_key)
        cursor = self._connection.execute(f"SELECT {', '.join(names)} FROM {table.name} ORDER BY {order}")
        rows = [dict(zip(names, values)) for values in cursor.fetchall()]
        return _parents_first(table, rows)

    def _insert(self, table: Table, row: dict[str, Any]) -> str:
        names = ", ".join(c.name for c in table.columns)
        values = ", ".join(self._dialect.literal(row[c.name], c) for c in table.columns)
        return f"INSERT INTO {table.name} ({names}) VALUES ({values});"


def _parents_first(table: Table, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Orders rows of a self-referencing table so that every referenced row is inserted first.

    SQL Server and PostgreSQL check foreign keys per statement, so a manager must exist
    before the employees pointing to it. Rows keep their key order wherever possible.
    """
    self_refs = [c for c in table.foreign_keys if c.references[0] == table.name]
    if not self_refs:
        return rows
    ordered: list[dict[str, Any]] = []
    inserted: dict[str, set[Any]] = {c.references[1]: set() for c in self_refs}
    pending = list(rows)
    while pending:
        progress = False
        for row in list(pending):
            if all(row[c.name] is None or row[c.name] in inserted[c.references[1]] for c in self_refs):
                ordered.append(row)
                for target in inserted:
                    inserted[target].add(row[target])
                pending.remove(row)
                progress = True
        if not progress:
            # A cycle within the table; keep the remaining order and let the target database report it.
            ordered.extend(pending)
            break
    return ordered
