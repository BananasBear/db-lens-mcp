"""MCP tool registration."""

from __future__ import annotations

import re
from typing import Any, Protocol

from db_lens_mcp.application.database_inspection_service import DatabaseInspectionService
from db_lens_mcp.application.query_inspection_service import QueryInspectionService
from db_lens_mcp.errors import DbLensError
from db_lens_mcp.domain.risk_rules import RiskRules
from db_lens_mcp.domain.sql_guard import SqlGuard
from db_lens_mcp.infrastructure.config.config_loader import ConfigLoader
from db_lens_mcp.infrastructure.mysql.connection_factory import MySqlConnectionFactory
from db_lens_mcp.infrastructure.mysql.explain_runner import MySqlExplainRunner
from db_lens_mcp.infrastructure.mysql.metadata_reader import MySqlMetadataReader
from db_lens_mcp.infrastructure.secrets.secret_store import SecretStore


class ToolRegistrar(Protocol):
    """Subset of FastMCP needed for registering tools."""

    def tool(self) -> Any:
        """Return the tool decorator."""


def register_tools(
    server: ToolRegistrar,
    database_service: DatabaseInspectionService | None = None,
    query_service: QueryInspectionService | None = None,
) -> None:
    """Register the fixed first-phase MCP tool surface."""

    connection_factory = None
    if database_service is None:
        secret_store = SecretStore()
        config_loader = ConfigLoader()
        connection_factory = MySqlConnectionFactory(
            config_loader=config_loader,
            secret_store=secret_store,
        )
        database_service = DatabaseInspectionService(
            metadata_reader=MySqlMetadataReader(connection_factory=connection_factory)
        )
    if query_service is None:
        if connection_factory is None:
            secret_store = SecretStore()
            config_loader = ConfigLoader()
            connection_factory = MySqlConnectionFactory(
                config_loader=config_loader,
                secret_store=secret_store,
            )
        query_service = QueryInspectionService(
            sql_guard=SqlGuard(),
            risk_rules=RiskRules(),
            explain_runner=MySqlExplainRunner(connection_factory=connection_factory),
            metadata_service=database_service,
        )

    @server.tool()
    def list_databases(profile: str) -> dict[str, Any]:
        """Get visible databases for a configured profile."""

        try:
            return {
                "profile": profile,
                "databases": [
                    {"name": name}
                    for name in database_service.list_databases(profile)
                ],
            }
        except DbLensError as exc:
            return tool_error("list_databases", exc, profile=profile)

    @server.tool()
    def list_tables(profile: str, database: str, keyword: str | None = None) -> dict[str, Any]:
        """Get tables in a database, optionally filtered by keyword."""

        try:
            return {
                "profile": profile,
                "database": database,
                "tables": database_service.list_tables(profile, database, keyword),
            }
        except DbLensError as exc:
            return tool_error("list_tables", exc, profile=profile, database=database)

    @server.tool()
    def describe_table(profile: str, database: str, table: str) -> dict[str, Any]:
        """Get table columns, primary key, and comments."""

        try:
            schema = database_service.describe_table(profile, database, table)
            return {
                "profile": profile,
                "database": database,
                "table": table,
                "columns": [
                    {
                        "name": column.name,
                        "type": column.type,
                        "nullable": column.nullable,
                        "default": column.default,
                        "primary_key": column.primary_key,
                        "comment": column.comment,
                    }
                    for column in schema.columns
                ],
                "primary_key": schema.primary_key,
                "comment": schema.comment,
            }
        except DbLensError as exc:
            return tool_error(
                "describe_table", exc, profile=profile, database=database, table=table
            )

    @server.tool()
    def list_indexes(profile: str, database: str, table: str) -> dict[str, Any]:
        """Get table indexes."""

        try:
            indexes = database_service.list_indexes(profile, database, table)
            return {
                "profile": profile,
                "database": database,
                "table": table,
                "indexes": [
                    {
                        "name": index.name,
                        "unique": index.unique,
                        "type": index.type,
                        "columns": index.columns,
                        "cardinality": index.cardinality,
                    }
                    for index in indexes
                ],
            }
        except DbLensError as exc:
            return tool_error("list_indexes", exc, profile=profile, database=database, table=table)

    @server.tool()
    def get_table_stats(profile: str, database: str, table: str) -> dict[str, Any]:
        """Get estimated table statistics from metadata."""

        try:
            stats = database_service.get_table_stats(profile, database, table)
            return {
                "profile": profile,
                "database": database,
                "table": table,
                "row_count_estimate": stats.row_count_estimate,
                "data_length_bytes": stats.data_length_bytes,
                "index_length_bytes": stats.index_length_bytes,
                "updated_at": stats.updated_at,
                "source": stats.source,
            }
        except DbLensError as exc:
            return tool_error(
                "get_table_stats", exc, profile=profile, database=database, table=table
            )

    @server.tool()
    def explain_select(profile: str, database: str, sql: str) -> dict[str, Any]:
        """Run EXPLAIN for a single SELECT query after safety validation."""

        result = query_service.inspect_query(
            sql,
            profile=profile,
            database=database,
            include_metadata=False,
        )
        return {
            "profile": profile,
            "database": database,
            "accepted": result.accepted,
            "query_type": result.query_type,
            "explain": _explain_response(result.explain_summary),
            "risk_hints": _risk_hint_response(result.risk_hints),
            "reason": _safe_reason(result.reason),
            "risk": result.risk,
        }

    @server.tool()
    def inspect_query(profile: str, database: str, sql: str) -> dict[str, Any]:
        """Return database context for a single SELECT query."""

        result = query_service.inspect_query(sql, profile=profile, database=database)
        return {
            "profile": profile,
            "database": database,
            "accepted": result.accepted,
            "query_type": result.query_type,
            "referenced_tables": result.referenced_tables,
            "table_context": _table_context_response(result),
            "metadata_errors": _metadata_error_response(result.metadata_errors),
            "explain": _explain_response(result.explain_summary),
            "risk_hints": _risk_hint_response(result.risk_hints),
            "ai_summary": result.ai_summary,
            "reason": _safe_reason(result.reason),
            "risk": result.risk,
        }


def tool_error(tool: str, exc: Exception, **extra: Any) -> dict[str, Any]:
    """Return a non-sensitive MCP error shape."""

    response = {
        "accepted": False,
        "reason": redact_sensitive_text(str(exc)),
        "risk": f"{tool}_failed",
    }
    response.update(extra)
    return response


def _safe_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    return redact_sensitive_text(reason)


def _explain_response(summary: Any) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "summary": {
            "status": summary.status,
            "tables": summary.tables,
            "access_types": summary.access_types,
            "used_indexes": summary.used_indexes,
            "estimated_rows": summary.estimated_rows,
            "extra": summary.extra,
        }
    }


def _table_context_response(result: Any) -> list[dict[str, Any]]:
    stats_by_table = {stats.table: stats for stats in result.stats}
    return [
        {
            "database": schema.database,
            "table": schema.table,
            "columns": _column_response(schema.columns),
            "primary_key": schema.primary_key,
            "comment": schema.comment,
            "indexes": _index_response(result.indexes.get(schema.table, [])),
            "stats": _stats_response(stats_by_table.get(schema.table)),
        }
        for schema in result.tables
    ]


def _metadata_error_response(errors: list) -> list[dict[str, str]]:
    return [
        {
            "table": error.get("table", ""),
            "reason": _safe_reason(error.get("reason")),
        }
        for error in errors
    ]


def _column_response(columns: list) -> list[dict[str, Any]]:
    return [
        {
            "name": column.name,
            "type": column.type,
            "nullable": column.nullable,
            "default": column.default,
            "primary_key": column.primary_key,
            "comment": column.comment,
        }
        for column in columns
    ]


def _index_response(indexes: list) -> list[dict[str, Any]]:
    return [
        {
            "name": index.name,
            "unique": index.unique,
            "type": index.type,
            "columns": index.columns,
            "cardinality": index.cardinality,
        }
        for index in indexes
    ]


def _stats_response(stats: Any) -> dict[str, Any] | None:
    if stats is None:
        return None
    return {
        "row_count_estimate": stats.row_count_estimate,
        "data_length_bytes": stats.data_length_bytes,
        "index_length_bytes": stats.index_length_bytes,
        "updated_at": stats.updated_at,
        "source": stats.source,
    }


def _risk_hint_response(hints: list) -> list[dict[str, Any]]:
    return [
        {
            "level": hint.level.value,
            "code": hint.code,
            "message": hint.message,
        }
        for hint in hints
    ]


def redact_sensitive_text(value: str) -> str:
    """Redact common secret fragments before returning MCP errors."""

    redacted = re.sub(
        r"(?i)(mysql|mariadb)://[^\s@]+:[^\s@]+@",
        r"\1://<redacted>:<redacted>@",
        value,
    )
    redacted = re.sub(
        r"(?i)(password|passwd|pwd|master[_-]?key)=([^\s]+)",
        r"\1=<redacted>",
        redacted,
    )
    return redacted
