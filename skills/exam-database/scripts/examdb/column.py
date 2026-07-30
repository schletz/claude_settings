"""Column definition of the schema spec."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

from .reserved_words import RESERVED_WORDS
from .spec_error import SpecError

ColumnType = Literal["int", "bigint", "decimal", "float", "string", "text", "bool", "date", "datetime"]
COLUMN_TYPES: tuple[str, ...] = get_args(ColumnType)

GEN_KEYS: frozenset[str] = frozenset(
    {"faker", "args", "choice", "weights", "range", "hours", "offset_from", "unit", "sequence", "start", "const",
     "coverage", "skew"}
)

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def check_identifier(name: str, what: str) -> None:
    """Rejects names that would need quoting in at least one dialect.

    Args:
        name: The identifier to check.
        what: Human-readable description used in the error message.

    Raises:
        SpecError: If the name contains non-ASCII characters, spaces or is a reserved word.
    """
    if not _IDENTIFIER.match(name):
        raise SpecError(f"{what} '{name}': only ASCII letters, digits and '_' are allowed (no umlauts).")
    if name.upper() in RESERVED_WORDS:
        raise SpecError(f"{what} '{name}' is a reserved SQL keyword; choose another name (e.g. 'Customer{name}').")


@dataclass(frozen=True)
class Column:
    """A single column including the rules used to generate its values.

    Attributes:
        name: Column name, unquoted in all dialects.
        type: Neutral type; each dialect maps it to its own SQL type.
        length: Maximum length for ``string`` columns.
        precision: Total digits for ``decimal`` columns.
        scale: Digits after the decimal point for ``decimal`` columns.
        nullable: Whether NULL is allowed.
        unique: Whether the column carries a single-column UNIQUE constraint.
        pk: Whether the column is (part of) the primary key.
        identity: Whether the database assigns the value (auto increment).
        references: Target of a foreign key as ``(table, column)``.
        default: Portable SQL expression used as DEFAULT.
        null_ratio: Share of generated rows that receive NULL.
        gen: Generator rule, see references/spec-format.md.
    """

    name: str
    type: ColumnType
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    nullable: bool = False
    unique: bool = False
    pk: bool = False
    identity: bool = False
    references: tuple[str, str] | None = None
    default: str | None = None
    null_ratio: float = 0.0
    gen: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(raw: dict[str, Any], table_name: str) -> Column:
        """Creates a column from its JSON representation and validates it in isolation."""
        name = raw.get("name", "")
        where = f"Column '{table_name}.{name}'"
        check_identifier(name, "Column")
        unknown = set(raw) - {"name", "type", "length", "precision", "scale", "nullable", "unique", "pk",
                              "identity", "references", "default", "null_ratio", "gen"}
        if unknown:
            raise SpecError(f"{where}: unknown keys {sorted(unknown)}.")

        col_type = raw.get("type")
        if col_type not in COLUMN_TYPES:
            raise SpecError(f"{where}: type must be one of {list(COLUMN_TYPES)}, got '{col_type}'.")
        if col_type == "string" and not raw.get("length"):
            raise SpecError(f"{where}: string columns need a 'length'.")

        references = None
        if "references" in raw:
            parts = str(raw["references"]).split(".")
            if len(parts) != 2:
                raise SpecError(f"{where}: 'references' must look like 'Table.Column'.")
            references = (parts[0], parts[1])

        gen = dict(raw.get("gen", {}))
        unknown_gen = set(gen) - GEN_KEYS
        if unknown_gen:
            raise SpecError(f"{where}: unknown generator keys {sorted(unknown_gen)}.")

        nullable = bool(raw.get("nullable", False))
        null_ratio = float(raw.get("null_ratio", 0.0))
        if null_ratio and not nullable:
            raise SpecError(f"{where}: 'null_ratio' requires 'nullable': true.")

        identity = bool(raw.get("identity", False))
        if identity and col_type not in ("int", "bigint"):
            raise SpecError(f"{where}: identity columns must be int or bigint.")

        return Column(
            name=name,
            type=col_type,
            length=raw.get("length"),
            precision=raw.get("precision", 10 if col_type == "decimal" else None),
            scale=raw.get("scale", 2 if col_type == "decimal" else None),
            nullable=nullable,
            unique=bool(raw.get("unique", False)),
            pk=bool(raw.get("pk", False)),
            identity=identity,
            references=references,
            default=raw.get("default"),
            null_ratio=null_ratio,
            gen=gen,
        )
