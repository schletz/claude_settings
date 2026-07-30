"""Table definition of the schema spec."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .column import Column, check_identifier
from .spec_error import SpecError


@dataclass(frozen=True)
class Table:
    """A table with its columns, keys and constraints.

    Attributes:
        name: Table name, unquoted in all dialects.
        rows: Number of rows the generator creates in addition to the fixtures.
        columns: Columns in declaration order; generators may only refer to earlier columns.
        primary_key: Names of the primary key columns.
        unique: Multi-column UNIQUE constraints.
        checks: Portable SQL expressions rendered as CHECK constraints.
        description: Meaning of the table for the students (German), shown with the data model.
    """

    name: str
    rows: int
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    unique: tuple[tuple[str, ...], ...]
    checks: tuple[str, ...]
    description: str = ""

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> Table:
        """Creates a table from its JSON representation and validates it in isolation."""
        name = raw.get("name", "")
        check_identifier(name, "Table")
        unknown = set(raw) - {"name", "rows", "columns", "primary_key", "unique", "checks", "description"}
        if unknown:
            raise SpecError(f"Table '{name}': unknown keys {sorted(unknown)}.")

        columns = tuple(Column.from_dict(c, name) for c in raw.get("columns", []))
        if not columns:
            raise SpecError(f"Table '{name}' has no columns.")
        lowered = [c.name.lower() for c in columns]
        if len(set(lowered)) != len(lowered):
            raise SpecError(f"Table '{name}' has duplicate column names (case-insensitive).")

        column_pk = tuple(c.name for c in columns if c.pk)
        table_pk = tuple(raw.get("primary_key", ()))
        if column_pk and table_pk:
            raise SpecError(f"Table '{name}': use either 'pk' on columns or 'primary_key', not both.")
        primary_key = column_pk or table_pk
        if not primary_key:
            raise SpecError(f"Table '{name}' has no primary key.")

        table = Table(
            name=name,
            rows=int(raw.get("rows", 0)),
            columns=columns,
            primary_key=primary_key,
            unique=tuple(tuple(u) for u in raw.get("unique", ())),
            checks=tuple(raw.get("checks", ())),
            description=str(raw.get("description", "")),
        )
        for key_column in primary_key + tuple(c for group in table.unique for c in group):
            table.column(key_column)
        identities = [c for c in columns if c.identity]
        if identities and (len(primary_key) != 1 or identities[0].name != primary_key[0] or len(identities) > 1):
            raise SpecError(f"Table '{name}': only a single-column primary key can be an identity.")
        return table

    def column(self, name: str) -> Column:
        """Returns the column with the given name (case-insensitive).

        Raises:
            SpecError: If the table has no such column.
        """
        for column in self.columns:
            if column.name.lower() == name.lower():
                return column
        raise SpecError(f"Table '{self.name}' has no column '{name}'.")

    @property
    def identity_column(self) -> Column | None:
        """The auto-increment primary key column, if any."""
        return next((c for c in self.columns if c.identity), None)

    @property
    def foreign_keys(self) -> tuple[Column, ...]:
        """All columns that reference another (or the same) table."""
        return tuple(c for c in self.columns if c.references)

    def dependencies(self) -> set[str]:
        """Names of the other tables this table references (self-references excluded)."""
        return {c.references[0] for c in self.foreign_keys if c.references[0].lower() != self.name.lower()}
