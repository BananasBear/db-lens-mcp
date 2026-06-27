"""SQL safety guard.

Only single SELECT-like queries are allowed. The guard uses sqlglot at runtime
and exposes a small parser injection point so tests can run without network
dependency installation in this local workspace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from db_lens_mcp.errors import SafetyError


@dataclass(frozen=True)
class SafeSelectQuery:
    """A SQL statement that passed the project safety boundary."""

    sql: str
    referenced_tables: list[str]
    has_placeholders: bool = False
    params: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class SqlGuard:
    """Validate user SQL before any database layer can see it."""

    parser: Callable[[str], Any] | None = None

    def validate_select(self, sql: str, params: list[Any] | None = None) -> SafeSelectQuery:
        """Validate a SELECT query.

        The method intentionally returns a typed `SafeSelectQuery` instead of a
        raw SQL string so database adapters can only receive already-vetted SQL.
        """

        normalized = sql.strip()
        if not normalized:
            raise SafetyError("SQL must not be empty.")
        if _looks_like_multi_statement(normalized):
            raise SafetyError("Only single SELECT statements are allowed.")
        expression = self._parse(normalized)
        if not _is_select_expression(expression):
            raise SafetyError("Only single SELECT statements are allowed.")
        referenced_tables = _extract_tables(expression)
        return SafeSelectQuery(
            sql=normalized,
            referenced_tables=referenced_tables,
            has_placeholders=_has_placeholders(normalized),
            params=params or [],
        )

    def _parse(self, sql: str) -> Any:
        parser = self.parser or _sqlglot_parse_one
        try:
            return parser(sql)
        except SafetyError:
            raise
        except Exception as exc:
            raise SafetyError("SQL could not be parsed as MySQL SELECT.") from exc


def _sqlglot_parse_one(sql: str) -> Any:
    try:
        import sqlglot
    except ModuleNotFoundError as exc:
        raise SafetyError("sqlglot is not installed. Install project dependencies.") from exc
    return sqlglot.parse_one(sql, read="mysql")


def _looks_like_multi_statement(sql: str) -> bool:
    """Reject semicolon-separated statements without trying to be a SQL parser."""

    stripped = sql.rstrip()
    if ";" not in stripped:
        return False
    return not stripped.endswith(";") or ";" in stripped[:-1]


def _is_select_expression(expression: Any) -> bool:
    expression_name = expression.__class__.__name__.lower()
    if expression_name == "select":
        return True
    if expression_name == "with":
        inner = getattr(expression, "this", None)
        return inner is not None and inner.__class__.__name__.lower() == "select"
    return False


def _extract_tables(expression: Any) -> list[str]:
    tables: list[str] = []
    find_all = getattr(expression, "find_all", None)
    if callable(find_all):
        try:
            import sqlglot

            table_expressions = find_all(sqlglot.expressions.Table)
        except ModuleNotFoundError:
            table_expressions = []
        for table in table_expressions:
            table_name = getattr(table, "name", None)
            if table_name and table_name not in tables:
                tables.append(table_name)
    explicit_tables = getattr(expression, "referenced_tables", None)
    if explicit_tables:
        for table_name in explicit_tables:
            if table_name not in tables:
                tables.append(table_name)
    return tables


def _has_placeholders(sql: str) -> bool:
    return bool(re.search(r"(\?|%s|:[A-Za-z_][A-Za-z0-9_]*)", sql))
