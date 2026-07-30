"""Generation of single column values from a column's ``gen`` rule."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from faker import Faker

from .column import Column
from .spec_error import SpecError

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

_UNITS = {"minutes": timedelta(minutes=1), "hours": timedelta(hours=1), "days": timedelta(days=1)}


class ValueFactory:
    """Creates values for non-foreign-key columns.

    Values are returned in their SQLite storage form: dates and datetimes as ISO strings,
    booleans as 0/1, decimals as floats rounded to the column scale.
    """

    def __init__(self, rng: random.Random, fake: Faker, reference_date: date) -> None:
        self._rng = rng
        self._fake = fake
        self._reference_date = reference_date

    def generate(self, column: Column, row: dict[str, Any], row_index: int) -> Any:
        """Generates one value.

        Args:
            column: The column to fill.
            row: Values of the columns generated so far for this row (needed by ``offset_from``).
            row_index: Zero-based position of the row within its table (needed by ``sequence``).
        """
        gen = column.gen
        if "const" in gen:
            return gen["const"]
        if "choice" in gen:
            return self._rng.choices(gen["choice"], weights=gen.get("weights"))[0]
        if "sequence" in gen:
            return str(gen["sequence"]).format(int(gen.get("start", 1)) + row_index)
        if "offset_from" in gen:
            return self._offset(column, row)
        if "range" in gen:
            low, high = gen["range"]
            return self._in_range(column, low, high)
        if "faker" in gen:
            return self._from_faker(column)
        return self._default(column)

    def _offset(self, column: Column, row: dict[str, Any]) -> Any:
        base_name = column.gen["offset_from"]
        base_key = next((k for k in row if k.lower() == str(base_name).lower()), None)
        if base_key is None:
            raise SpecError(f"'{column.name}': offset_from '{base_name}' must name an earlier column of the table.")
        base = row[base_key]
        if base is None:
            return None
        low, high = column.gen.get("range", [0, 0])
        if column.type in ("date", "datetime"):
            unit = _UNITS.get(column.gen.get("unit", "days"))
            if unit is None:
                raise SpecError(f"'{column.name}': unit must be one of {list(_UNITS)}.")
            parsed = datetime.fromisoformat(str(base))
            return self._format(column, parsed + unit * self._rng.randint(int(low), int(high)))
        return self._round(column, float(base) + self._rng.uniform(float(low), float(high)))

    def _in_range(self, column: Column, low: Any, high: Any) -> Any:
        if column.type in ("date", "datetime"):
            start = datetime.fromisoformat(str(low))
            end = datetime.fromisoformat(str(high))
            if column.type == "date":
                days = (end.date() - start.date()).days
                return (start.date() + timedelta(days=self._rng.randint(0, days))).strftime(DATE_FORMAT)
            if "hours" in column.gen:
                return self._within_hours(start, end, column.gen["hours"])
            # Whole minutes keep datetimes readable for students.
            minutes = int((end - start).total_seconds() // 60)
            return (start + timedelta(minutes=self._rng.randint(0, minutes))).strftime(DATETIME_FORMAT)
        if column.type in ("int", "bigint"):
            return self._rng.randint(int(low), int(high))
        return self._round(column, self._rng.uniform(float(low), float(high)))

    def _within_hours(self, start: datetime, end: datetime, hours: list[int]) -> str:
        """Random day in [start, end] with a time between hours[0]:00 and hours[1]:00 (opening hours)."""
        first_hour, last_hour = int(hours[0]), int(hours[1])
        day = start.date() + timedelta(days=self._rng.randint(0, (end.date() - start.date()).days))
        minute = self._rng.randint(first_hour * 60, last_hour * 60)
        return (datetime.combine(day, datetime.min.time()) + timedelta(minutes=minute)).strftime(DATETIME_FORMAT)

    def _from_faker(self, column: Column) -> Any:
        method = getattr(self._fake, column.gen["faker"], None)
        if method is None:
            raise SpecError(f"'{column.name}': Faker has no provider '{column.gen['faker']}'.")
        value = method(**column.gen.get("args", {}))
        if isinstance(value, (datetime, date)):
            return self._format(column, value)
        if isinstance(value, Decimal):
            return self._round(column, float(value))
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, str):
            # Line breaks (e.g. in addresses) break the line-based result parsing of the CLI tools.
            value = value.replace("\r", "").replace("\n", ", ")
            if column.length:
                value = value[: column.length]
        return value

    def _default(self, column: Column) -> Any:
        match column.type:
            case "int" | "bigint":
                return self._rng.randint(1, 100)
            case "decimal" | "float":
                return self._round(column, self._rng.uniform(1, 1000))
            case "bool":
                return self._rng.randint(0, 1)
            case "date" | "datetime":
                end = datetime.combine(self._reference_date, datetime.min.time())
                return self._in_range(column, end - timedelta(days=730), end)
            case "text":
                return self._fake.sentence()
            case _:
                return self._fake.word()[: column.length]

    @staticmethod
    def _format(column: Column, value: date | datetime) -> str:
        if column.type == "date":
            return value.strftime(DATE_FORMAT)
        if not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time())
        return value.strftime(DATETIME_FORMAT)

    @staticmethod
    def _round(column: Column, value: float) -> float | int:
        if column.type in ("int", "bigint"):
            return round(value)
        return round(value, column.scale if column.scale is not None else 4)
