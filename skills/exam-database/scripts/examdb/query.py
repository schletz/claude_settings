"""Exam query with its correct solution and the wrong variants it must tell apart."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .spec_error import SpecError
from .wrong_variant import WrongVariant

DEFAULT_MAX_ROWS = 15

_DML = re.compile(r"^\s*(INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Query:
    """One exam task.

    Attributes:
        id: Short identifier used in reports.
        topic: Exam topic, e.g. "left-join", "group-by", "not-exists", "dml".
        task: Task text for the students (German).
        sql: Correct solution; used for every dialect without an override.
        sql_by_dialect: Dialect-specific solutions keyed by 'sqlite', 'mssql' or 'postgres'.
        wrong: Wrong variants in SQLite syntax.
        ordered: Whether row order is part of the expected result.
        max_rows: Upper limit of result rows so students can still check the result by eye.
    """

    id: str
    topic: str
    task: str
    sql: str
    sql_by_dialect: dict[str, str]
    wrong: tuple[WrongVariant, ...]
    ordered: bool
    max_rows: int

    def sql_for(self, dialect: str) -> str:
        """Solution for the given dialect, falling back to the generic one."""
        return self.sql_by_dialect.get(dialect, self.sql)

    @property
    def is_dml(self) -> bool:
        """True for INSERT, UPDATE and DELETE tasks."""
        return bool(_DML.match(self.sql_for("sqlite")))


def load_queries(path: str | Path) -> list[Query]:
    """Reads a queries file (see references/queries-format.md).

    Raises:
        SpecError: If required fields are missing or ids are duplicated.
    """
    try:
        raw: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SpecError(f"{path} is not valid JSON: {e}") from e
    default_max = int(raw.get("max_rows", DEFAULT_MAX_ROWS))
    queries = []
    for item in raw.get("queries", []):
        missing = {"id", "task", "sql"} - set(item)
        if missing:
            raise SpecError(f"Query {item.get('id', '?')}: missing {sorted(missing)}.")
        queries.append(Query(
            id=str(item["id"]),
            topic=item.get("topic", ""),
            task=item["task"],
            sql=item["sql"],
            sql_by_dialect=dict(item.get("sql_by_dialect", {})),
            wrong=tuple(WrongVariant(w["label"], w["sql"]) for w in item.get("wrong", [])),
            ordered=bool(item.get("ordered", False)),
            max_rows=int(item.get("max_rows", default_max)),
        ))
    ids = [q.id for q in queries]
    if len(set(ids)) != len(ids):
        raise SpecError("Query ids must be unique.")
    return queries
