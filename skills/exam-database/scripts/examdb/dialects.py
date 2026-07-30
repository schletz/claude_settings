"""Lookup of dialects by name."""

from __future__ import annotations

from .dialect import Dialect
from .mssql_dialect import MssqlDialect
from .postgres_dialect import PostgresDialect
from .sqlite_dialect import SqliteDialect

DIALECT_NAMES: tuple[str, ...] = ("sqlite", "mssql", "postgres")


def get_dialect(name: str) -> Dialect:
    """Returns the dialect for 'sqlite', 'mssql' or 'postgres'."""
    dialects: dict[str, type[Dialect]] = {"sqlite": SqliteDialect, "mssql": MssqlDialect,
                                          "postgres": PostgresDialect}
    return dialects[name]()
