"""SQLite dialect."""

from __future__ import annotations

from .column import Column
from .dialect import Dialect


class SqliteDialect(Dialect):
    """SQLite: dates are stored as ISO text, booleans as 0/1."""

    name = "sqlite"

    _TYPES = {"int": "INTEGER", "bigint": "INTEGER", "float": "REAL", "text": "TEXT", "bool": "BOOLEAN",
              "date": "DATE", "datetime": "DATETIME"}

    def column_type(self, column: Column) -> str:
        if column.type == "string":
            return f"VARCHAR({column.length})"
        if column.type == "decimal":
            return f"DECIMAL({column.precision},{column.scale})"
        return self._TYPES[column.type]

    def identity_clause(self) -> str:
        # An INTEGER PRIMARY KEY is the auto-increment rowid alias in SQLite.
        return ""

    def bool_literal(self, value: bool) -> str:
        return "1" if value else "0"

    def header(self) -> list[str]:
        return ["PRAGMA foreign_keys = ON;"]
