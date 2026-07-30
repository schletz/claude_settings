"""Helpers for running statements against the SQLite build database."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Any

ResultRows = list[tuple[Any, ...]]


@dataclass(frozen=True)
class DmlOutcome:
    """Effect of a DML statement executed on a throwaway copy of the database.

    Attributes:
        rowcount: Sum of affected rows over all statements.
        fingerprint: Hash of the complete database content afterwards.
        error: Error message if a statement failed (e.g. a foreign key violation).
    """

    rowcount: int
    fingerprint: str
    error: str | None


def connect(path: str) -> sqlite3.Connection:
    """Opens the build database with foreign keys enforced."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def split_statements(sql: str) -> list[str]:
    """Splits a script at statement boundaries, also within a line, without breaking string literals."""
    statements, current = [], ""
    for char in sql:
        current += char
        # complete_statement knows about quotes and comments, so a ';' inside 'a;b' does not split.
        if char == ";" and sqlite3.complete_statement(current):
            statements.append(current)
            current = ""
    statements.append(current)
    return [s.strip() for s in statements if s.strip(" \t\r\n;")]


def run_select(connection: sqlite3.Connection, sql: str) -> tuple[list[str], ResultRows]:
    """Executes a query and returns column names and rows."""
    cursor = connection.execute(sql)
    columns = [d[0] for d in cursor.description or []]
    return columns, cursor.fetchall()


def run_dml_on_copy(connection: sqlite3.Connection, sql: str) -> DmlOutcome:
    """Executes DML on an in-memory copy so every task starts from the original data."""
    copy = sqlite3.connect(":memory:")
    connection.backup(copy)
    copy.execute("PRAGMA foreign_keys = ON")
    rowcount, error = 0, None
    try:
        for statement in split_statements(sql):
            rowcount += max(copy.execute(statement).rowcount, 0)
        copy.commit()
    except sqlite3.Error as e:
        copy.rollback()
        error = str(e)
    outcome = DmlOutcome(rowcount, fingerprint(copy), error)
    copy.close()
    return outcome


def fingerprint(connection: sqlite3.Connection) -> str:
    """Hash over the sorted content of all tables; equal hashes mean equal data."""
    digest = hashlib.sha256()
    tables = [r[0] for r in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for table in tables:
        rows = sorted(map(repr, connection.execute(f"SELECT * FROM {table}")))
        digest.update(f"{table}:{len(rows)}:{'|'.join(rows)}".encode())
    return digest.hexdigest()


def format_table(columns: list[str], rows: ResultRows, limit: int | None = None) -> str:
    """Renders a result as a Markdown table; NULL is shown explicitly."""
    shown = rows if limit is None else rows[:limit]
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for row in shown:
        lines.append("| " + " | ".join(format_cell(v) for v in row) + " |")
    if limit is not None and len(rows) > limit:
        lines.append(f"| ... {len(rows) - limit} more rows |")
    return "\n".join(lines)


def format_cell(value: Any) -> str:
    """Renders a result value for the students; NULL is spelled out."""
    if value is None:
        return "NULL"
    if isinstance(value, float):
        # SQLite sums binary floats (235.04999999999998); students expect 235.05.
        return repr(round(value, 6))
    return str(value)
