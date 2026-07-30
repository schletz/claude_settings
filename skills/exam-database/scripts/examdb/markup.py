"""Text markup a task sheet is written in."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from .dialect import Dialect
from .schema import Schema


class Markup(ABC):
    """Syntax of one document format; the sheet content is the same for every format."""

    @abstractmethod
    def document_start(self, title: str) -> list[str]:
        """Lines that open the document, ending with a blank line."""

    @abstractmethod
    def heading(self, level: int, text: str) -> str:
        """Section heading; level 2 is a top-level section below the title."""

    def paragraph(self, text: str) -> str:
        """Running text as given in the task file."""
        return text.strip()

    @abstractmethod
    def bold(self, text: str) -> str:
        """Strongly emphasized inline text."""

    @abstractmethod
    def table(self, columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
        """Result table with a header row; NULL is shown explicitly."""

    @abstractmethod
    def code(self, sql: str) -> str:
        """SQL code block."""

    @abstractmethod
    def data_model(self, schema: Schema, dialect: Dialect, er_layout: Sequence[str]) -> str:
        """Data model section with types of the target dialect and the table descriptions.

        Args:
            schema: Schema whose tables are described.
            dialect: Target dialect for the column types.
            er_layout: PlantUML layout lines for formats that draw an ER diagram.
        """
