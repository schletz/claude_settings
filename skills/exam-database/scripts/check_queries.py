"""Checks exam queries against the SQLite build database.

Usage:
    python check_queries.py <file.db> <queries.json> [--mode result|count]

For every query the correct solution is executed and compared with each wrong variant.
A wrong variant that returns the same result (SELECT) or leaves the same data behind (DML)
is reported as FAIL: the data does not expose that mistake yet. With ``--mode count``
(students only get the number of rows / affected rows) a wrong variant with the same
count is a FAIL too, even if its values differ. Results larger than
``max_rows`` or empty results are reported as WARN. Exit code 1 if any FAIL or ERROR occurred.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys

from examdb.console import use_utf8_output
from examdb.query import Query, load_queries
from examdb.result_compare import same_result
from examdb.spec_error import SpecError
from examdb.sqlite_tools import connect, format_table, run_dml_on_copy, run_select


def main() -> int:
    """Entry point; returns the process exit code."""
    use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db")
    parser.add_argument("queries")
    parser.add_argument("--mode", choices=("result", "count"), default="result",
                        help="what students compare against: the result table or only the row count")
    args = parser.parse_args()
    by_count = args.mode == "count"
    try:
        queries = load_queries(args.queries)
    except SpecError as e:
        print(f"Spec error: {e}", file=sys.stderr)
        return 1

    connection = connect(args.db)
    problems = 0
    for query in queries:
        lines, failed = (_check_dml(connection, query, by_count) if query.is_dml
                         else _check_select(connection, query, by_count))
        problems += failed
        print("\n".join(lines) + "\n")
    print(f"{len(queries)} queries checked, {problems} with FAIL/ERROR.")
    return 1 if problems else 0


def _check_select(connection: sqlite3.Connection, query: Query, by_count: bool) -> tuple[list[str], bool]:
    header = f"### [{query.id}] {query.topic}"
    try:
        columns, rows = run_select(connection, query.sql_for("sqlite"))
    except sqlite3.Error as e:
        return [header, f"ERROR in correct solution: {e}"], True

    lines = [header, f"Correct solution: {len(rows)} rows"]
    if not rows:
        lines.append("WARN: empty result, almost every wrong query also returns nothing.")
    if len(rows) > query.max_rows:
        lines.append(f"WARN: more than {query.max_rows} rows, too many to check by eye.")
    lines.append(format_table(columns, rows, limit=query.max_rows + 5))

    failed = False
    for variant in query.wrong:
        try:
            _, wrong_rows = run_select(connection, variant.sql)
        except sqlite3.Error as e:
            lines.append(f"- WARN '{variant.label}': raises an error ({e}); intended?")
            continue
        if same_result(rows, wrong_rows, query.ordered):
            lines.append(f"- FAIL '{variant.label}': same result as the correct solution")
            failed = True
        elif by_count and len(wrong_rows) == len(rows):
            lines.append(f"- FAIL '{variant.label}': other values, but the same row count ({len(rows)})")
            failed = True
        else:
            lines.append(f"- ok '{variant.label}': differs ({len(wrong_rows)} rows)")
    if not query.wrong:
        lines.append("- WARN: no wrong variants defined")
    return lines, failed


def _check_dml(connection: sqlite3.Connection, query: Query, by_count: bool) -> tuple[list[str], bool]:
    header = f"### [{query.id}] {query.topic} (DML, executed on a copy)"
    correct = run_dml_on_copy(connection, query.sql_for("sqlite"))
    if correct.error:
        return [header, f"ERROR in correct solution: {correct.error}"], True

    lines = [header, f"Correct solution: {correct.rowcount} rows affected"]
    if correct.rowcount == 0:
        lines.append("WARN: no rows affected.")
    failed = False
    for variant in query.wrong:
        outcome = run_dml_on_copy(connection, variant.sql)
        if outcome.error:
            lines.append(f"- ok '{variant.label}': fails with '{outcome.error}'")
        elif outcome.fingerprint == correct.fingerprint:
            lines.append(f"- FAIL '{variant.label}': leaves the same data behind")
            failed = True
        elif by_count and outcome.rowcount == correct.rowcount:
            lines.append(f"- FAIL '{variant.label}': other data, but the same number of affected rows")
            failed = True
        else:
            lines.append(f"- ok '{variant.label}': different data ({outcome.rowcount} rows affected)")
    if not query.wrong:
        lines.append("- WARN: no wrong variants defined")
    return lines, failed


if __name__ == "__main__":
    sys.exit(main())
