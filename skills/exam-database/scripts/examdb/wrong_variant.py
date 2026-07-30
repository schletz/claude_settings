"""A deliberately wrong solution of an exam query."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WrongVariant:
    """A typical student mistake that the data must expose.

    Attributes:
        label: Short description of the mistake, e.g. "INNER JOIN statt LEFT JOIN".
        sql: The wrong statement in SQLite syntax.
    """

    label: str
    sql: str
