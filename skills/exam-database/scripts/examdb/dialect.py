"""Common SQL rendering shared by all target dialects."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from .column import Column
from .table import Table


class Dialect(ABC):
    """Renders DDL and INSERT literals for one database system.

    Identifiers stay unquoted on purpose: students should be able to write
    ``SELECT * FROM Customer`` in every system. The schema validation guarantees
    that this is safe (no reserved words, ASCII only).
    """

    name: str = ""
    nulls_distinct_in_unique: bool = True
    """False if a UNIQUE constraint admits only one NULL (SQL Server)."""

    @abstractmethod
    def column_type(self, column: Column) -> str:
        """SQL type of a column, without constraints."""

    @abstractmethod
    def identity_clause(self) -> str:
        """Text placed after the type of an auto-increment column."""

    @abstractmethod
    def bool_literal(self, value: bool) -> str:
        """Literal for a boolean value."""

    def string_literal(self, value: str) -> str:
        """Literal for a string value with doubled single quotes."""
        return "'" + value.replace("'", "''") + "'"

    def header(self) -> list[str]:
        """Statements placed at the top of the dump."""
        return []

    def before_inserts(self, table: Table) -> list[str]:
        """Statements placed before the INSERTs of a table."""
        return []

    def after_inserts(self, table: Table) -> list[str]:
        """Statements placed after the INSERTs of a table."""
        return []

    def after_data(self, tables: tuple[Table, ...]) -> list[str]:
        """Statements placed after all data has been committed."""
        return []

    def drop_table(self, table: Table) -> str:
        """Statement that removes the table if it exists, so the dump can be re-run."""
        return f"DROP TABLE IF EXISTS {table.name};"

    def create_table(self, table: Table) -> str:
        """CREATE TABLE statement including keys, foreign keys, unique and check constraints.

        Unique constraints over nullable columns become separate statements in dialects
        that treat NULLs as equal (see ``nulls_distinct_in_unique``).
        """
        single_pk = table.primary_key[0] if len(table.primary_key) == 1 else None
        lines = [self._column_definition(c, c.name == single_pk) for c in table.columns]
        if single_pk is None:
            lines.append(f"PRIMARY KEY ({', '.join(table.primary_key)})")
        indexes = []
        for group in [(c.name,) for c in table.columns if c.unique] + list(table.unique):
            nullable = [name for name in group if table.column(name).nullable]
            if nullable and not self.nulls_distinct_in_unique:
                indexes.append(self.filtered_unique_index(table, group, nullable))
            else:
                lines.append(f"CONSTRAINT UQ_{table.name}_{'_'.join(group)} UNIQUE ({', '.join(group)})")
        for column in table.foreign_keys:
            target_table, target_column = column.references
            lines.append(f"CONSTRAINT FK_{table.name}_{column.name} FOREIGN KEY ({column.name}) "
                         f"REFERENCES {target_table}({target_column})")
        lines.extend(f"CHECK ({check})" for check in table.checks)
        body = ",\n".join(f"    {line}" for line in lines)
        return "\n".join([f"CREATE TABLE {table.name} (\n{body}\n);", *indexes])

    def filtered_unique_index(self, table: Table, group: tuple[str, ...], nullable: list[str]) -> str:
        """Unique index that ignores rows with NULLs; needed when ``nulls_distinct_in_unique`` is False."""
        raise NotImplementedError(f"{self.name} has no filtered unique index")

    def literal(self, value: Any, column: Column) -> str:
        """Renders a value read from SQLite as a literal for this dialect."""
        if value is None:
            return "NULL"
        match column.type:
            case "bool":
                return self.bool_literal(bool(value))
            case "int" | "bigint":
                return str(int(value))
            case "decimal":
                return str(Decimal(str(value)).quantize(Decimal(1).scaleb(-(column.scale or 0))))
            case "float":
                return repr(float(value))
            case _:
                return self.string_literal(str(value))

    def _column_definition(self, column: Column, is_single_pk: bool) -> str:
        parts = [column.name, self.column_type(column)]
        if column.identity:
            parts.append(self.identity_clause())
        if is_single_pk:
            parts.append("PRIMARY KEY")
        elif not column.nullable:
            parts.append("NOT NULL")
        if column.default is not None:
            parts.append(f"DEFAULT {column.default}")
        return " ".join(p for p in parts if p)
