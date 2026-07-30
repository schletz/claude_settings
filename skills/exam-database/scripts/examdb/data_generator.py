"""Generation of all rows of a schema: fixtures, generated rows and foreign keys."""

from __future__ import annotations

import random
from typing import Any

from faker import Faker

from .column import Column
from .schema import Schema
from .spec_error import SpecError
from .table import Table
from .value_factory import ValueFactory

Row = dict[str, Any]

CHILDLESS = "_childless"
STREAM = "_stream"
_MAX_ATTEMPTS = 500


class DataGenerator:
    """Generates the rows of every table in dependency order.

    Fixture rows and generated rows share one numbering. Fixture rows without an explicit
    key get random positions, so edge-case rows do not cluster at the start of a table
    where students would spot the pattern.

    Every row draws from its own random stream (seed, table, row position). Adding a
    fixture or changing another table therefore leaves the values of the generated rows
    untouched; at most their key numbers shift. Edge cases that were already verified
    survive the next fix.
    """

    def __init__(self, schema: Schema) -> None:
        self._schema = schema
        self._rng = random.Random()
        self._fake = Faker(schema.locale)
        self._values = ValueFactory(self._rng, self._fake, schema.reference_date)
        self._rows: dict[str, list[Row]] = {}
        self._pools: dict[tuple[str, str], tuple[list[Any], list[float]]] = {}

    def generate(self) -> dict[str, list[Row]]:
        """Returns the rows per table name; keys starting with '_' are metadata, not columns."""
        for table in self._schema.tables:
            self._rows[table.name] = self._generate_table(table)
        return self._rows

    def _stream(self, *parts: object) -> str:
        """Seed string of an independent random stream."""
        return ":".join(map(str, (self._schema.seed, *parts)))

    def _reseed_row(self, table: Table, key: str) -> None:
        seed = self._stream(table.name, key)
        self._rng.seed(seed)
        self._fake.seed_instance(seed)

    def _generate_table(self, table: Table) -> list[Row]:
        fixtures = [self._canonical_fixture(table, f) for f in self._schema.fixtures.get(table.name, [])]
        total = len(fixtures) + table.rows
        numbered = _numbered_column(table)
        numbers = self._assign_numbers(table, numbered, fixtures, total)
        unique_groups = _unique_groups(table)
        seen: dict[tuple[str, ...], set[tuple[Any, ...]]] = {g: set() for g in unique_groups}

        rows: list[Row] = []
        for index in range(total):
            fixture = fixtures[index] if index < len(fixtures) else {}
            stream = f"fixture{index}" if fixture else f"row{index - len(fixtures)}"
            self._reseed_row(table, stream)
            for _ in range(_MAX_ATTEMPTS):
                row = self._generate_row(table, fixture, numbers[index], index, rows)
                row[STREAM] = stream
                keys = {g: tuple(row[c] for c in g) for g in unique_groups}
                violated = [g for g, key in keys.items() if None not in key and key in seen[g]]
                if not violated:
                    break
                # Retrying cannot help when the fixture itself fixes every colliding value.
                if all(c in fixture for g in violated for c in g):
                    raise SpecError(f"Fixture row {fixture} of '{table.name}' violates unique {violated}.")
            else:
                raise SpecError(f"'{table.name}': no unique row found after {_MAX_ATTEMPTS} attempts. "
                                "Offer more distinct values (choice list, faker provider) or lower 'rows'.")
            for group, key in keys.items():
                if None not in key:
                    seen[group].add(key)
            rows.append(row)

        if numbered:
            rows.sort(key=lambda r: r[numbered.name])
        return rows

    def _generate_row(self, table: Table, fixture: Row, number: int | None, index: int,
                      previous: list[Row]) -> Row:
        numbered = _numbered_column(table)
        row: Row = {CHILDLESS: bool(fixture.get(CHILDLESS, False))}
        for column in table.columns:
            if column.name in fixture:
                row[column.name] = fixture[column.name]
            elif numbered is not None and column is numbered:
                row[column.name] = number
            elif column.null_ratio and self._rng.random() < column.null_ratio:
                row[column.name] = None
            elif column.references:
                row[column.name] = self._pick_reference(table, column, previous)
            else:
                row[column.name] = self._values.generate(column, row, index)
        return row

    def _pick_reference(self, table: Table, column: Column, previous: list[Row]) -> Any:
        target_table, target_column = column.references
        if target_table == table.name:
            # Self-references point to rows generated earlier; the dump exporter orders the inserts.
            candidates = [r[target_column] for r in previous if r[target_column] is not None]
            return self._rng.choice(candidates) if candidates else None
        pool, weights = self._pool(table, column)
        if not pool:
            if column.nullable:
                return None
            raise SpecError(f"'{table.name}.{column.name}' references '{target_table}', which has no usable rows.")
        # Weighted rendezvous hashing: every candidate gets a stable score for this pick, the best
        # one wins. Adding a parent row changes only the picks the new parent wins, unlike
        # random.choices, where inserting into the list moves the picks of all later positions.
        # The salt comes from the row's own stream, so unique retries still get a fresh pick.
        salt = self._rng.random()
        best = max(range(len(pool)),
                   key=lambda i: random.Random(f"{salt}:{pool[i][1]}").random() ** (1 / weights[i]))
        return pool[best][0]

    def _pool(self, table: Table, column: Column) -> tuple[list[tuple[Any, str]], list[float]]:
        """Parent (key, stream) pairs a foreign key may point to, limited by ``coverage``, weighted by ``skew``.

        ``coverage`` < 1 leaves a share of parents without children; ``skew`` > 0 makes a few
        parents very popular, so GROUP BY results differ clearly and ties become unlikely.
        """
        cache_key = (table.name, column.name)
        if cache_key not in self._pools:
            target_table, target_column = column.references
            parents = [r for r in self._rows[target_table] if not r[CHILDLESS] and r[target_column] is not None]
            # Order parents by a score derived from their stream, not by key: when a fixture shifts
            # the key numbers of the parent table, children still pick the same parent rows.
            parents.sort(key=lambda r: random.Random(self._stream(table.name, column.name, r[STREAM])).random())
            candidates = [(r[target_column], r[STREAM]) for r in parents]
            coverage = float(column.gen.get("coverage", 1.0))
            pool = candidates[: max(1, round(coverage * len(candidates)))] if candidates else []
            skew = float(column.gen.get("skew", 0.0))
            self._pools[cache_key] = (pool, [1 / (i + 1) ** skew for i in range(len(pool))])
        return self._pools[cache_key]

    def _assign_numbers(self, table: Table, numbered: Column | None, fixtures: list[Row],
                        total: int) -> list[int | None]:
        """Assigns key numbers 1..n; explicit fixture keys are kept, the other fixtures are scattered."""
        if numbered is None:
            return [None] * total
        explicit = [f.get(numbered.name) for f in fixtures]
        used = {n for n in explicit if n is not None}
        needed = total - len(used)
        free: list[int] = []
        candidate = 1
        while len(free) < needed:
            if candidate not in used:
                free.append(candidate)
            candidate += 1
        open_fixtures = sum(1 for n in explicit if n is None)
        for_fixtures = random.Random(self._stream(table.name, "numbers")).sample(free, open_fixtures)
        for_generated = iter(sorted(set(free) - set(for_fixtures)))
        fixture_numbers = iter(for_fixtures)
        numbers: list[int | None] = [n if n is not None else next(fixture_numbers) for n in explicit]
        numbers.extend(next(for_generated) for _ in range(total - len(fixtures)))
        return numbers

    @staticmethod
    def _canonical_fixture(table: Table, fixture: Row) -> Row:
        return {(k if k.startswith("_") else table.column(k).name): v for k, v in fixture.items()}


def _numbered_column(table: Table) -> Column | None:
    """The integer key column that receives sequential numbers, if the table has one."""
    if len(table.primary_key) != 1:
        return None
    column = table.column(table.primary_key[0])
    if column.identity or (column.type in ("int", "bigint") and not column.gen and not column.references):
        return column
    return None


def _unique_groups(table: Table) -> list[tuple[str, ...]]:
    groups = [tuple(table.column(c).name for c in table.primary_key)]
    groups += [(c.name,) for c in table.columns if c.unique]
    groups += [tuple(table.column(c).name for c in g) for g in table.unique]
    return list(dict.fromkeys(groups))
