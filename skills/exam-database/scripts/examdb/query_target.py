"""Interface of a database a dump is verified against."""

from __future__ import annotations

from typing import Protocol


class QueryTarget(Protocol):
    """A loaded target database that can answer the exam queries.

    Cells are returned as text (or None for NULL); comparison normalizes them.
    """

    def load_script(self, script: str) -> None:
        """Executes the complete dump; raises RuntimeError with the database message on failure."""

    def query(self, sql: str) -> list[tuple[str | None, ...]]:
        """Runs a SELECT and returns its rows; raises RuntimeError on failure."""

    def execute_dml(self, sql: str) -> int:
        """Runs DML inside a rolled-back transaction and returns the affected row count."""
