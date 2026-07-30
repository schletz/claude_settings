"""Root of the schema spec: tables, fixtures and post-processing SQL."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .spec_error import SpecError
from .table import Table


@dataclass(frozen=True)
class Schema:
    """A validated schema spec.

    Attributes:
        name: Name of the database, used for file names and dump headers.
        seed: Random seed; the same spec and seed always produce the same data.
        locale: Faker locale, e.g. ``de_AT``.
        reference_date: Fixed "today" for default date ranges, keeps builds reproducible.
        tables: Tables in dependency order (referenced tables first).
        fixtures: Hand-written rows per table name, inserted alongside the generated rows.
        post_sql: SQLite statements executed after generation to shape edge cases.
    """

    name: str
    seed: int
    locale: str
    reference_date: date
    tables: tuple[Table, ...]
    fixtures: dict[str, list[dict[str, Any]]]
    post_sql: tuple[str, ...]

    def table(self, name: str) -> Table:
        """Returns the table with the given name (case-insensitive).

        Raises:
            SpecError: If no such table exists.
        """
        for table in self.tables:
            if table.name.lower() == name.lower():
                return table
        raise SpecError(f"Unknown table '{name}'.")

    @staticmethod
    def load(path: str | Path) -> Schema:
        """Reads and validates a spec file.

        Raises:
            SpecError: If the spec is inconsistent (unknown references, cycles, bad fixtures, ...).
        """
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SpecError(f"{path} is not valid JSON: {e}") from e

        unknown = set(raw) - {"name", "seed", "locale", "reference_date", "tables", "fixtures", "post_sql"}
        if unknown:
            raise SpecError(f"Spec: unknown top-level keys {sorted(unknown)}.")
        tables = [Table.from_dict(t) for t in raw.get("tables", [])]
        if not tables:
            raise SpecError("Spec has no tables.")
        lowered = [t.name.lower() for t in tables]
        if len(set(lowered)) != len(lowered):
            raise SpecError("Spec has duplicate table names (case-insensitive).")

        by_name = {t.name.lower(): t for t in tables}
        tables = [_resolve_references(t, by_name) for t in tables]
        fixtures = {by_name[_require_table(n, by_name)].name: rows for n, rows in raw.get("fixtures", {}).items()}
        for table_name, rows in fixtures.items():
            _check_fixtures(by_name[table_name.lower()], rows)

        return Schema(
            name=raw.get("name", Path(path).stem),
            seed=int(raw.get("seed", 42)),
            locale=raw.get("locale", "de_AT"),
            reference_date=date.fromisoformat(raw.get("reference_date", date.today().isoformat())),
            tables=tuple(_dependency_order(tables)),
            fixtures=fixtures,
            post_sql=tuple(raw.get("post_sql", ())),
        )


def _require_table(name: str, by_name: dict[str, Table]) -> str:
    if name.lower() not in by_name:
        raise SpecError(f"Unknown table '{name}'.")
    return name.lower()


def _resolve_references(table: Table, by_name: dict[str, Table]) -> Table:
    """Replaces referenced names by their canonical spelling and validates the targets."""
    columns = []
    for column in table.columns:
        if column.references:
            target = by_name[_require_table(column.references[0], by_name)]
            target_column = target.column(column.references[1])
            is_key = target.primary_key == (target_column.name,) or target_column.unique
            if not is_key:
                raise SpecError(f"'{table.name}.{column.name}' must reference a single-column primary key "
                                f"or unique column, '{target.name}.{target_column.name}' is neither.")
            if target is table and not column.nullable:
                raise SpecError(f"Self-reference '{table.name}.{column.name}' must be nullable "
                                "(the first row has nobody to point to).")
            column = dataclasses.replace(column, references=(target.name, target_column.name))
        columns.append(column)
    return dataclasses.replace(table, columns=tuple(columns))


def _check_fixtures(table: Table, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        for key in row:
            if not key.startswith("_"):
                table.column(key)


def _dependency_order(tables: list[Table]) -> list[Table]:
    """Sorts tables so that every table comes after the tables it references (stable Kahn sort)."""
    remaining = list(tables)
    ordered: list[Table] = []
    placed: set[str] = set()
    while remaining:
        ready = [t for t in remaining if {d.lower() for d in t.dependencies()} <= placed]
        if not ready:
            cycle = ", ".join(t.name for t in remaining)
            raise SpecError(f"Foreign keys form a cycle between: {cycle}. Make one reference a separate table "
                            "or drop it.")
        for table in ready:
            ordered.append(table)
            placed.add(table.name.lower())
            remaining.remove(table)
    return ordered
