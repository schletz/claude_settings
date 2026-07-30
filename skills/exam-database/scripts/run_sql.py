"""Runs SQL against the SQLite build database and prints the results as Markdown tables.

Usage:
    python run_sql.py <file.db> <statement-or-file.sql>

Meant for exploring the generated data. Every statement runs on an in-memory copy,
so nothing is changed; persistent changes belong into the spec (fixtures, post_sql).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from examdb.console import use_utf8_output
from examdb.sqlite_tools import connect, format_table, split_statements


def main() -> int:
    """Entry point; returns the process exit code."""
    use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db")
    parser.add_argument("sql", help="SQL text or path to a .sql file")
    args = parser.parse_args()
    source = Path(args.sql)
    sql = source.read_text(encoding="utf-8") if source.suffix == ".sql" and source.is_file() else args.sql

    copy = sqlite3.connect(":memory:")
    connect(args.db).backup(copy)
    for statement in split_statements(sql):
        try:
            cursor = copy.execute(statement)
        except sqlite3.Error as e:
            print(f"ERROR: {e}\n  in: {statement}")
            return 1
        if cursor.description:
            rows = cursor.fetchall()
            print(f"{len(rows)} rows\n{format_table([d[0] for d in cursor.description], rows, limit=50)}\n")
        else:
            print(f"{cursor.rowcount} rows affected\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
