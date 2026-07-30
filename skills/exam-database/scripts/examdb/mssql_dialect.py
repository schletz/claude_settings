"""SQL Server dialect."""

from __future__ import annotations

from .column import Column
from .dialect import Dialect
from .table import Table


class MssqlDialect(Dialect):
    """SQL Server: Unicode strings (NVARCHAR, N'...'), BIT for booleans, IDENTITY keys."""

    name = "mssql"

    _TYPES = {"int": "INTEGER", "bigint": "BIGINT", "float": "FLOAT", "text": "NVARCHAR(MAX)", "bool": "BIT",
              "date": "DATE", "datetime": "DATETIME2(0)"}

    def column_type(self, column: Column) -> str:
        if column.type == "string":
            return f"NVARCHAR({column.length})"
        if column.type == "decimal":
            return f"DECIMAL({column.precision},{column.scale})"
        return self._TYPES[column.type]

    def identity_clause(self) -> str:
        return "IDENTITY(1,1)"

    def bool_literal(self, value: bool) -> str:
        return "1" if value else "0"

    def string_literal(self, value: str) -> str:
        return "N" + super().string_literal(value)

    # SQL Server treats NULLs as equal in UNIQUE constraints, so a nullable unique column
    # could hold only one NULL. A filtered index enforces uniqueness for the non-NULL values only.
    nulls_distinct_in_unique = False

    def filtered_unique_index(self, table: Table, group: tuple[str, ...], nullable: list[str]) -> str:
        condition = " AND ".join(f"{name} IS NOT NULL" for name in nullable)
        return (f"CREATE UNIQUE INDEX UX_{table.name}_{'_'.join(group)} ON {table.name} ({', '.join(group)}) "
                f"WHERE {condition};")

    def before_inserts(self, table: Table) -> list[str]:
        # Explicit key values keep the dump identical to the verified SQLite data.
        return [f"SET IDENTITY_INSERT {table.name} ON;"] if table.identity_column else []

    def after_inserts(self, table: Table) -> list[str]:
        return [f"SET IDENTITY_INSERT {table.name} OFF;"] if table.identity_column else []
