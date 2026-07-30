"""Renders the SQL answer sheet the students fill in during the exam.

Usage:
    python render_answer_sheet.py <file.db> <queries.json> --dialect sqlite|mssql|postgres
                                  --mode result|count|both|none [-o <angabe.sql>]

Every task gets a fixed block: separator line, "AUFGABE n von X", the task text, optionally
the expected result, and an empty "Lösung:" section for the student's SQL. The separator
lines and headings are the anchors for automated grading, so the layout must stay
identical across exams. The expected results come from the SQLite build database.

With -o, the model solution <angabe>_loesung.sql is written next to the sheet: the same
file with the solution SQL (target dialect) in every "Lösung:" section. Without -o, the
model solution is printed.
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

from examdb.console import use_utf8_output
from examdb.dialects import DIALECT_NAMES
from examdb.expected_result import HINT_MODES, describe_expected
from examdb.output_files import write_sheet_pair
from examdb.query import load_queries
from examdb.spec_error import SpecError
from examdb.sqlite_tools import connect

SEPARATOR = "-- " + "*" * 97
_TEXT_WIDTH = len(SEPARATOR)

_HEADER = """\
-- PRÜFUNG IN DATENBANKEN
--
-- Schreiben Sie Ihre Lösungen zur entsprechenden Aufgabe in diese SQL Datei.
-- Füllen Sie vorher Klasse, Name und Datum aus.
-- ÄNDERN SIE NICHTS AM AUFBAU DER SQL DATEI!
-- Entfernen Sie keine Kommentare und Trennzeilen, sonst kann die Datei nicht korrekt bewertet werden.

{separator}
-- Vorname: (Vorname)
-- Zuname:  (Zuname)
-- Klasse:  (Klasse)
-- Datum:   (Datum)
{separator}
"""


def comment(text: str, wrap: bool) -> list[str]:
    """Turns text into SQL comment lines.

    Args:
        text: Text, possibly with line breaks.
        wrap: Wrap long lines at the separator width. Off for Markdown tables, whose rows
            must stay on one line.
    """
    lines = []
    for line in text.splitlines():
        parts = textwrap.wrap(line, _TEXT_WIDTH - 3) if wrap and line.strip() else [line]
        lines += [f"-- {part}".rstrip() for part in parts]
    return lines


def task_block(number: int, total: int, task: str, hints: list[str], solution: str = "") -> list[str]:
    """One task framed by separator lines; the solution section stays empty unless given."""
    lines = ["", SEPARATOR, f"-- AUFGABE {number} von {total}", *comment(task, wrap=True), "--"]
    for hint in hints:
        lines += [*comment(hint, wrap=not hint.startswith("|")), "--"]
    lines.append("-- Lösung:")
    if solution:
        # The terminator lets the whole file run as one script, e.g. in psql.
        lines += [solution if solution.endswith(";") else solution + ";"]
    return lines + ["", SEPARATOR]


def main() -> int:
    """Entry point; returns the process exit code."""
    use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db")
    parser.add_argument("queries")
    parser.add_argument("--dialect", required=True, choices=DIALECT_NAMES, help="dialect of the model solution")
    parser.add_argument("--mode", choices=HINT_MODES, required=True,
                        help="what the students get: the result table, only the row count, both, or nothing")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    try:
        queries = load_queries(args.queries)
    except SpecError as e:
        print(f"Spec error: {e}", file=sys.stderr)
        return 1

    connection = connect(args.db)
    header = _HEADER.format(separator=SEPARATOR).rstrip("\n")
    sheet = [header]
    solution = [header.replace("-- PRÜFUNG IN DATENBANKEN", "-- PRÜFUNG IN DATENBANKEN (MUSTERLÖSUNG)", 1)]
    for number, query in enumerate(queries, start=1):
        hints = describe_expected(connection, query, args.mode)
        sheet += task_block(number, len(queries), query.task, hints)
        solution += task_block(number, len(queries), query.task, hints, query.sql_for(args.dialect).strip())
    connection.close()
    sheet_text, solution_text = "\n".join(sheet) + "\n", "\n".join(solution) + "\n"
    if args.output:
        # The BOM makes SQL Server Management Studio detect UTF-8; otherwise umlauts are garbled.
        write_sheet_pair(args.output, sheet_text, solution_text, encoding="utf-8-sig")
    else:
        print(solution_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
