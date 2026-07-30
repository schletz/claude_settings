"""Loads a dump into a fresh target database and compares the query results with SQLite.

Usage:
    python verify_dump.py <dump.sql> --dialect sqlite|mssql|postgres [--db <file.db> --queries <queries.json>]

For mssql and postgres a temporary Docker container is started and removed afterwards.
Without --db/--queries only the loading of the dump is tested. With them, every correct
solution runs on the target (dialect override if present) and is compared with the SQLite
result: row counts must match, value differences (e.g. integer division in AVG on SQL Server)
are reported. Exit code 1 if loading fails or any result differs.
"""

from __future__ import annotations

import argparse
import sys
import time
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

from examdb.console import use_utf8_output
from examdb.dialects import DIALECT_NAMES
from examdb.mssql_container import MssqlContainer
from examdb.postgres_container import PostgresContainer
from examdb.query import Query, load_queries
from examdb.query_target import QueryTarget
from examdb.result_compare import normalize_rows
from examdb.spec_error import SpecError
from examdb.sqlite_target import SqliteTarget
from examdb.sqlite_tools import connect, run_dml_on_copy, run_select


def main() -> int:
    """Entry point; returns the process exit code."""
    use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dump", type=Path)
    parser.add_argument("--dialect", required=True, choices=DIALECT_NAMES)
    parser.add_argument("--db", help="SQLite build database used as reference")
    parser.add_argument("--queries", help="queries file whose solutions are compared")
    args = parser.parse_args()
    if bool(args.db) != bool(args.queries):
        parser.error("--db and --queries must be given together")
    try:
        queries = load_queries(args.queries) if args.queries else []
    except SpecError as e:
        print(f"Spec error: {e}", file=sys.stderr)
        return 1

    script = args.dump.read_text(encoding="utf-8-sig")
    started = time.monotonic()
    try:
        with _open_target(args.dialect) as target:
            print(f"Target {args.dialect} ready after {time.monotonic() - started:.0f}s")
            try:
                target.load_script(script)
            except RuntimeError as e:
                print(f"ERROR: dump does not load:\n{e}")
                return 1
            print(f"Dump loaded: {args.dump}")
            differences = sum(_compare(target, args.db, q, args.dialect) for q in queries)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if queries:
        print(f"{len(queries)} solutions compared, {differences} differ from SQLite.")
    return 1 if differences else 0


def _open_target(dialect: str) -> AbstractContextManager[QueryTarget]:
    match dialect:
        case "mssql":
            return MssqlContainer()
        case "postgres":
            return PostgresContainer()
        case _:
            return nullcontext(SqliteTarget())


def _compare(target: QueryTarget, db: str, query: Query, dialect: str) -> bool:
    """Prints the comparison of one query; returns True if the target deviates from SQLite."""
    reference = connect(db)
    try:
        if query.is_dml:
            expected = run_dml_on_copy(reference, query.sql_for("sqlite")).rowcount
            actual = target.execute_dml(query.sql_for(dialect))
            ok = expected == actual
            print(f"[{query.id}] {'ok' if ok else 'DIFF'}: {actual} rows affected (SQLite: {expected})")
            return not ok
        _, rows = run_select(reference, query.sql_for("sqlite"))
        actual_rows = target.query(query.sql_for(dialect))
    except RuntimeError as e:
        print(f"[{query.id}] ERROR on {dialect}: {e}")
        return True
    finally:
        reference.close()

    expected_norm = normalize_rows(rows, ordered=False)
    actual_norm = normalize_rows(actual_rows, ordered=False)
    if len(expected_norm) != len(actual_norm):
        print(f"[{query.id}] DIFF: {len(actual_norm)} rows on {dialect}, {len(expected_norm)} on SQLite")
        return True
    if expected_norm != actual_norm:
        sample = next((a, e) for a, e in zip(actual_norm, expected_norm) if a != e)
        print(f"[{query.id}] DIFF: same row count, different values, e.g. {dialect} {sample[0]} vs SQLite {sample[1]}")
        return True
    if query.ordered and normalize_rows(rows, True) != normalize_rows(actual_rows, True):
        print(f"[{query.id}] DIFF: same rows, different order; ORDER BY has ties, add a tie-breaker")
        return True
    print(f"[{query.id}] ok: {len(actual_norm)} rows")
    return False


if __name__ == "__main__":
    sys.exit(main())
