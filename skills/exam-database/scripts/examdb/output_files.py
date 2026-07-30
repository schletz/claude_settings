"""Writes a task sheet together with its model solution."""

from __future__ import annotations

from pathlib import Path


def solution_path(sheet: Path) -> Path:
    """Path of the model solution next to a sheet: tasks.md -> tasks_loesung.md."""
    return sheet.with_name(f"{sheet.stem}_loesung{sheet.suffix}")


def write_sheet_pair(sheet: Path, sheet_text: str, solution_text: str, encoding: str = "utf-8") -> None:
    """Writes the students' sheet and the model solution side by side.

    Both are always written together so the solution can never drift from the sheet the
    students received.
    """
    for path, text in ((sheet, sheet_text), (solution_path(sheet), solution_text)):
        path.write_text(text, encoding=encoding)
        print(f"Wrote {path}")
