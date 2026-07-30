"""Exports schema and data of the built SQLite database as a SQL dump for one dialect.

Usage:
    python export_dump.py <spec.json> <file.db> --dialect sqlite|mssql|postgres [-o <dump.sql>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from examdb.console import use_utf8_output
from examdb.dialects import DIALECT_NAMES, get_dialect
from examdb.dump_exporter import DumpExporter
from examdb.schema import Schema
from examdb.spec_error import SpecError
from examdb.sqlite_tools import connect


def main() -> int:
    """Entry point; returns the process exit code."""
    use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", type=Path)
    parser.add_argument("db", type=Path)
    parser.add_argument("--dialect", required=True, choices=DIALECT_NAMES)
    parser.add_argument("-o", "--output", type=Path, help="default: <db name>_<dialect>.sql")
    args = parser.parse_args()
    output: Path = args.output or args.db.with_name(f"{args.db.stem}_{args.dialect}.sql")

    try:
        schema = Schema.load(args.spec)
    except SpecError as e:
        print(f"Spec error: {e}", file=sys.stderr)
        return 1
    connection = connect(str(args.db))
    dump = DumpExporter(schema, get_dialect(args.dialect), connection).render()
    connection.close()
    # SSMS reads UTF-8 without BOM as ANSI and garbles umlauts; psql, however, chokes on a BOM.
    output.write_text(dump, encoding="utf-8-sig" if args.dialect == "mssql" else "utf-8")
    print(f"Wrote {output} ({len(dump.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
