"""Renders the exam tasks with expected results as Markdown or AsciiDoc, plus the model solution.

Usage:
    python render_tasks.py <file.db> <queries.json> --dialect sqlite|mssql|postgres
                           [--mode result|count|both|none] [--spec <spec.json>] [--title <text>]
                           [--intro <file>] [--er-layout <file.puml>] [-o <tasks.md|tasks.adoc>]

The expected results come from the SQLite build database, so verify_dump.py should have
confirmed beforehand that the target dialect returns the same rows. With -o, the sheet for
the students and the model solution <tasks>_loesung.<ext> are written side by side; the
solution is the same sheet with the solution SQL (target dialect) below each task. Without
-o, the model solution is printed as Markdown.

The extension of -o selects the format. With --spec the sheet contains the data model:
Markdown lists the columns per table, AsciiDoc draws a PlantUML ER diagram; both show the
table descriptions of the spec. --intro inserts a text in the output format (scenario,
hand-in instructions) below the title. --er-layout inserts PlantUML layout lines into the
diagram (e.g. "left to right direction") once the rendered PDF shows they are needed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from examdb.console import use_utf8_output
from examdb.dialects import DIALECT_NAMES, get_dialect
from examdb.expected_result import HINT_MODES, describe_expected
from examdb.markup import Markup
from examdb.markups import markup_for
from examdb.output_files import write_sheet_pair
from examdb.query import Query, load_queries
from examdb.schema import Schema
from examdb.spec_error import SpecError
from examdb.sqlite_tools import connect

_DIALECT_TITLES = {"sqlite": "SQLite", "mssql": "SQL Server", "postgres": "PostgreSQL"}


def render_preamble(markup: Markup, args: argparse.Namespace, queries: list[Query], schema: Schema | None) -> list[str]:
    """Everything between the title and the first task; identical in sheet and solution."""
    lines = [args.intro.read_text(encoding="utf-8").strip(), ""] if args.intro else []
    lines += [markup.paragraph(f"Datenbanksystem: {_DIALECT_TITLES[args.dialect]}"), ""]
    if any(q.is_dml for q in queries):
        lines += [markup.paragraph("DML-Aufgaben beziehen sich jeweils auf den Ausgangszustand der Datenbank."), ""]
    if schema:
        er_layout = [line.rstrip() for line in args.er_layout.read_text(encoding="utf-8").splitlines()
                     if line.strip()] if args.er_layout else []
        lines += [markup.data_model(schema, get_dialect(args.dialect), er_layout), ""]
    return lines


def main() -> int:
    """Entry point; returns the process exit code."""
    use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("db")
    parser.add_argument("queries")
    parser.add_argument("--dialect", required=True, choices=DIALECT_NAMES)
    parser.add_argument("--mode", choices=HINT_MODES, default="both",
                        help="what the students get: the result table, only the row count, both, or nothing")
    parser.add_argument("--spec", type=Path, help="schema spec; adds the data model section")
    parser.add_argument("--title", default="SQL Aufgaben")
    parser.add_argument("--intro", type=Path, help="text in the output format, inserted below the title")
    parser.add_argument("--er-layout", type=Path, help="PlantUML layout lines for the ER diagram (AsciiDoc only)")
    parser.add_argument("-o", "--output", type=Path, help="tasks.md or tasks.adoc")
    args = parser.parse_args()
    try:
        markup = markup_for(args.output)
    except ValueError as e:
        parser.error(str(e))
    if args.er_layout and not (args.spec and args.output and args.output.suffix.lower() == ".adoc"):
        parser.error("--er-layout needs --spec and an .adoc output; only AsciiDoc sheets draw an ER diagram.")
    try:
        queries = load_queries(args.queries)
        schema = Schema.load(args.spec) if args.spec else None
    except SpecError as e:
        print(f"Spec error: {e}", file=sys.stderr)
        return 1

    connection = connect(args.db)
    # The sheet and the solution differ only in the title and the solution blocks.
    sheet: list[str] = []
    solution: list[str] = []
    for number, query in enumerate(queries, start=1):
        task = [markup.heading(2, f"Aufgabe {number}"), "", markup.paragraph(query.task), ""]
        for paragraph in describe_expected(connection, query, args.mode, markup):
            task += [paragraph, ""]
        sheet += task
        solution += task + [markup.code(query.sql_for(args.dialect)), ""]
    connection.close()

    preamble = render_preamble(markup, args, queries, schema)
    sheet_text = "\n".join([*markup.document_start(args.title), *preamble, *sheet])
    solution_text = "\n".join([*markup.document_start(f"{args.title} (Lösung)"), *preamble, *solution])
    if args.output:
        write_sheet_pair(args.output, sheet_text, solution_text)
    else:
        print(solution_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
