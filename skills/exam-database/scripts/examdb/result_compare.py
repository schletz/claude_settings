"""Comparison of query results across drivers and dialects."""

from __future__ import annotations

from typing import Any, Sequence

Cell = int | float | str | None


def normalize_value(value: Any) -> Cell:
    """Maps a cell to a comparable form.

    CLI tools return text while SQLite returns Python values; numbers are compared
    rounded to 4 decimals so that 12.5, '12.50' and 12.500000 are equal.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return _number(float(value))
    text = str(value).strip()
    try:
        return _number(float(text))
    except ValueError:
        return text


def normalize_rows(rows: Sequence[Sequence[Any]], ordered: bool) -> list[tuple[Cell, ...]]:
    """Normalizes all cells; unordered results are sorted to compare them as multisets."""
    normalized = [tuple(normalize_value(v) for v in row) for row in rows]
    if not ordered:
        normalized.sort(key=lambda row: tuple((v is None, type(v).__name__, str(v)) for v in row))
    return normalized


def same_result(a: Sequence[Sequence[Any]], b: Sequence[Sequence[Any]], ordered: bool) -> bool:
    """True if both results contain the same rows (in the same order if ``ordered``)."""
    return normalize_rows(a, ordered) == normalize_rows(b, ordered)


def _number(value: float) -> int | float:
    rounded = round(value, 4)
    return int(rounded) if rounded.is_integer() else rounded
