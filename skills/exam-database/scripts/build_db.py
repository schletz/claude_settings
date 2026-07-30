"""Builds the SQLite exam database from a schema spec.

Usage:
    python build_db.py <spec.json> [--db <file.db>]

The database is rebuilt from scratch on every run, so the same spec and seed always yield
the same data. Afterwards the script prints statistics that show which edge cases exist
(parents without children, NULLs, duplicate names).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any

from examdb.console import use_utf8_output
from examdb.data_generator import DataGenerator
from examdb.schema import Schema
from examdb.spec_error import SpecError
from examdb.sqlite_dialect import SqliteDialect
from examdb.table import Table


def main() -> int:
    """Entry point; returns the process exit code."""
    use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--db", type=Path, help="output file (default: spec name with .db)")
    args = parser.parse_args()
    db_path: Path = args.db or args.spec.with_suffix(".db")

    try:
        schema = Schema.load(args.spec)
        rows = DataGenerator(schema).generate()
    except SpecError as e:
        print(f"Spec error: {e}", file=sys.stderr)
        return 1

    db_path.unlink(missing_ok=True)
    connection = sqlite3.connect(db_path, isolation_level=None)
    try:
        _create(connection, schema, rows)
    except (SpecError, sqlite3.Error) as e:
        connection.close()
        db_path.unlink(missing_ok=True)
        print(f"Build failed: {e}", file=sys.stderr)
        return 1

    print(f"Built {db_path}\n")
    _print_statistics(connection, schema)
    connection.close()
    return 0


def _create(connection: sqlite3.Connection, schema: Schema, rows: dict[str, list[dict[str, Any]]]) -> None:
    dialect = SqliteDialect()
    for table in schema.tables:
        connection.execute(dialect.create_table(table))

    # Foreign keys are checked once at the end to report every violation, not just the first.
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("BEGIN")
    for table in schema.tables:
        _insert(connection, table, rows[table.name])
    for statement in schema.post_sql:
        try:
            connection.execute(statement)
        except sqlite3.Error as e:
            raise SpecError(f"post_sql statement failed ({e}): {statement}") from e
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        details = "; ".join(f"{t} rowid {r} -> {p}" for t, r, p, _ in violations[:10])
        raise SpecError(f"{len(violations)} foreign key violations: {details}")
    connection.execute("COMMIT")
    connection.execute("PRAGMA foreign_keys = ON")


def _insert(connection: sqlite3.Connection, table: Table, rows: list[dict[str, Any]]) -> None:
    names = [c.name for c in table.columns]
    sql = f"INSERT INTO {table.name} ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})"
    for row in rows:
        try:
            connection.execute(sql, [row[n] for n in names])
        except sqlite3.Error as e:
            values = {n: row[n] for n in names}
            raise SpecError(f"Insert into {table.name} failed ({e}): {values}") from e


def _print_statistics(connection: sqlite3.Connection, schema: Schema) -> None:
    def scalar(sql: str) -> int:
        return connection.execute(sql).fetchone()[0]

    print("## Rows")
    for table in schema.tables:
        print(f"- {table.name}: {scalar(f'SELECT COUNT(*) FROM {table.name}')}")

    print("\n## Foreign keys (parents without children are the LEFT JOIN edge cases)")
    for table in schema.tables:
        for column in table.foreign_keys:
            parent, key = column.references
            childless = scalar(f"SELECT COUNT(*) FROM {parent} p WHERE NOT EXISTS "
                               f"(SELECT 1 FROM {table.name} c WHERE c.{column.name} = p.{key})")
            nulls = scalar(f"SELECT COUNT(*) FROM {table.name} WHERE {column.name} IS NULL")
            print(f"- {table.name}.{column.name} -> {parent}.{key}: {childless} {parent} rows without "
                  f"{table.name}, {nulls} NULL")

    print("\n## NULL values in nullable columns")
    for table in schema.tables:
        for column in table.columns:
            if column.nullable and not column.references:
                nulls = scalar(f"SELECT COUNT(*) FROM {table.name} WHERE {column.name} IS NULL")
                hint = " (nullable but no NULLs: set null_ratio if NULL handling should be tested)" if not nulls else ""
                print(f"- {table.name}.{column.name}: {nulls} NULL{hint}")

    print("\n## Repeated values in non-unique text columns (GROUP BY name vs. id)")
    for table in schema.tables:
        for column in table.columns:
            if column.type == "string" and not column.unique and not column.references:
                repeated = scalar(f"SELECT COUNT(*) FROM (SELECT {column.name} FROM {table.name} "
                                  f"WHERE {column.name} IS NOT NULL GROUP BY {column.name} HAVING COUNT(*) > 1)")
                distinct = scalar(f"SELECT COUNT(DISTINCT {column.name}) FROM {table.name}")
                print(f"- {table.name}.{column.name}: {distinct} distinct, {repeated} occur more than once")


if __name__ == "__main__":
    sys.exit(main())
