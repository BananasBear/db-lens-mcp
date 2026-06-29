"""MySQL EXPLAIN runner."""

from __future__ import annotations

from dataclasses import dataclass

from db_lens_mcp.domain.models import ExplainSummary
from db_lens_mcp.domain.sql_guard import SafeSelectQuery
from db_lens_mcp.errors import DatabaseAccessError
from db_lens_mcp.errors import SafetyError
from db_lens_mcp.infrastructure.mysql.connection_factory import MySqlConnectionFactory


@dataclass(frozen=True)
class MySqlExplainRunner:
    """Run EXPLAIN only for SQL already accepted by SqlGuard."""

    connection_factory: MySqlConnectionFactory

    def explain(self, profile: str, database: str, query: SafeSelectQuery) -> ExplainSummary:
        if not isinstance(query, SafeSelectQuery):
            raise SafetyError("EXPLAIN requires a SafeSelectQuery.")
        _profile_name, profile_config = self.connection_factory.get_profile_config(profile)
        if database not in profile_config.databases:
            raise SafetyError("EXPLAIN database must be configured for the profile.")
        if query.has_placeholders and not query.params:
            return ExplainSummary(status="skipped_missing_params", tables=query.referenced_tables)
        if query.has_placeholders and not _uses_only_pymysql_placeholders(query.sql):
            return ExplainSummary(
                status="skipped_unsupported_placeholder_style",
                tables=query.referenced_tables,
            )
        explain_sql = "EXPLAIN " + query.sql.rstrip(";")
        with self._connection(profile, database) as connection:
            rows = _fetch_all(connection, explain_sql, tuple(query.params) if query.params else None)
        return _summarize_explain(rows)

    def _connection(self, profile: str, database: str):
        return self.connection_factory.create(profile, database=database)


def _fetch_all(connection: object, sql: str, params: tuple | None = None) -> list[dict]:
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
    except Exception as exc:
        raise DatabaseAccessError("EXPLAIN query failed.") from exc


def _summarize_explain(rows: list[dict]) -> ExplainSummary:
    tables: list[str] = []
    access_types: list[str] = []
    used_indexes: list[str] = []
    total_rows = 0
    has_rows = False
    extra: list[str] = []
    for row in rows:
        table = row.get("table")
        if table and table not in tables:
            tables.append(table)
        access_type = row.get("type")
        if access_type and access_type not in access_types:
            access_types.append(access_type)
        key = row.get("key")
        if key and key not in used_indexes:
            used_indexes.append(key)
        estimated_rows = row.get("rows")
        if estimated_rows is not None:
            has_rows = True
            total_rows += int(estimated_rows)
        extra_value = row.get("Extra")
        if extra_value:
            extra.append(extra_value)
    return ExplainSummary(
        status="ok",
        tables=tables,
        access_types=access_types,
        used_indexes=used_indexes,
        estimated_rows=total_rows if has_rows else None,
        extra=extra,
    )


def _uses_only_pymysql_placeholders(sql: str) -> bool:
    return "?" not in sql and not _has_named_placeholder(sql)


def _has_named_placeholder(sql: str) -> bool:
    import re

    return bool(re.search(r":[A-Za-z_][A-Za-z0-9_]*", sql))
