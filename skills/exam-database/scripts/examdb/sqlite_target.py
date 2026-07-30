"""In-memory SQLite database used to verify a SQLite dump."""

from __future__ import annotations

import sqlite3

from .sqlite_tools import split_statements


class SqliteTarget:
    """Loads a SQLite dump into memory; implements the QueryTarget protocol."""

    def __init__(self) -> None:
        self._connection = sqlite3.connect(":memory:", isolation_level=None)

    def load_script(self, script: str) -> None:
        """Executes the complete dump; raises RuntimeError with the first error messages."""
        try:
            self._connection.executescript(script)
        except sqlite3.Error as e:
            raise RuntimeError(str(e)) from e

    def query(self, sql: str) -> list[tuple[str | None, ...]]:
        """Runs a SELECT and returns its rows as text cells, None for NULL."""
        try:
            rows = self._connection.execute(sql).fetchall()
        except sqlite3.Error as e:
            raise RuntimeError(str(e)) from e
        return [tuple(None if v is None else str(v) for v in row) for row in rows]

    def execute_dml(self, sql: str) -> int:
        """Runs DML inside a rolled-back transaction and returns the affected row count."""
        self._connection.execute("SAVEPOINT verify")
        try:
            return sum(max(self._connection.execute(s).rowcount, 0) for s in split_statements(sql))
        except sqlite3.Error as e:
            raise RuntimeError(str(e)) from e
        finally:
            self._connection.execute("ROLLBACK TO verify")
            self._connection.execute("RELEASE verify")
