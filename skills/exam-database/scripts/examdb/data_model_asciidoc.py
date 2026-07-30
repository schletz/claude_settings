"""AsciiDoc description of the schema: PlantUML ER diagram plus table descriptions."""

from __future__ import annotations

from collections.abc import Sequence

from .column import Column
from .dialect import Dialect
from .schema import Schema
from .table import Table


def render_data_model(schema: Schema, dialect: Dialect, er_layout: Sequence[str]) -> str:
    """Renders the data model section.

    The diagram contains no layout directives of its own: how PlantUML arranges a schema
    depends on its shape, so layout lines (direction, scale, hidden links) are only added
    when the rendered page shows that they are needed.

    Args:
        schema: Schema to describe.
        dialect: Target dialect for the column types.
        er_layout: PlantUML lines inserted after the diagram header.
    """
    lines = ["== Datenmodell", "", "[plantuml,format=svg]", "----", "@startuml", "hide circle", *er_layout]
    for table in schema.tables:
        lines += _entity(table, dialect)
    for table in schema.tables:
        lines += [_relation(table, column) for column in table.foreign_keys]
    lines += ["@enduml", "----"]
    described = [t for t in schema.tables if t.description]
    if described:
        lines += ["", '[cols="1,3",options="header"]', "|===", "| Tabelle | Bedeutung", ""]
        lines += [f"| {t.name} | {t.description}" for t in described]
        lines.append("|===")
    return "\n".join(lines)


def _entity(table: Table, dialect: Dialect) -> list[str]:
    key_columns = [c for c in table.columns if c.name in table.primary_key]
    other_columns = [c for c in table.columns if c.name not in table.primary_key]
    return [f"entity {table.name} {{",
            *(_attribute(table, c, dialect) for c in key_columns), "  --",
            *(_attribute(table, c, dialect) for c in other_columns), "}"]


def _attribute(table: Table, column: Column, dialect: Dialect) -> str:
    keys = [k for k, applies in (("PK", column.name in table.primary_key), ("FK", column.references)) if applies]
    stereotype = f" <<{','.join(keys)}>>" if keys else ""
    # A leading '*' marks mandatory attributes in PlantUML's IE notation.
    mandatory = "  " if column.nullable else "  * "
    return f"{mandatory}{column.name} : {dialect.column_type(column)}{stereotype}"


def _relation(table: Table, column: Column) -> str:
    parent, _ = column.references
    parent_side = "|o" if column.nullable else "||"
    # The column name only adds information when it does not follow the <Parent>Id convention.
    label = "" if column.name.lower() == f"{parent}id".lower() else f" : {column.name}"
    return f"{parent} {parent_side}--o{{ {table.name}{label}"
