"""SQL safety guard.

Only single SELECT-like queries are allowed. This module intentionally remains
small in the skeleton; full sqlglot validation lands in the SQL safety phase.
"""

from __future__ import annotations

from dataclasses import dataclass

from db_lens_mcp.errors import SafetyError


@dataclass(frozen=True)
class SafeSelectQuery:
    """A SQL statement that passed the project safety boundary."""

    sql: str
    referenced_tables: list[str]
    has_placeholders: bool = False


class SqlGuard:
    """Validate user SQL before any database layer can see it."""

    def validate_select(self, sql: str) -> SafeSelectQuery:
        """Validate a SELECT query.

        This skeleton performs only a conservative placeholder implementation:
        all non-empty SQL is rejected until sqlglot validation is implemented.
        Keeping the method strict prevents accidental unsafe behavior while the
        project is still at the skeleton stage.
        """

        normalized = sql.strip()
        if not normalized:
            raise SafetyError("SQL must not be empty.")
        raise SafetyError("SQL validation is not implemented yet.")
