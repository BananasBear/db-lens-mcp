"""MCP tool registration."""

from __future__ import annotations

import re
from typing import Any, Protocol

from db_lens_mcp.application.database_inspection_service import DatabaseInspectionService
from db_lens_mcp.application.query_inspection_service import QueryInspectionService
from db_lens_mcp.application.table_locator_service import (
    TableLocatorService,
    TableMappingCache,
    TableResolutionError,
)
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


READ_ONLY_TOOL_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def register_tools(
    server: ToolRegistrar,
    database_service: DatabaseInspectionService | None = None,
    query_service: QueryInspectionService | None = None,
    table_locator: TableLocatorService | None = None,
) -> None:
    """Register the fixed first-phase MCP tool surface."""

    connection_factory = None
    config_loader = ConfigLoader()
    if database_service is None:
        secret_store = SecretStore()
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
    if table_locator is None:
        table_locator = TableLocatorService(
            config_loader=config_loader,
            database_service=database_service,
            cache=TableMappingCache.for_config(),
        )

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
    def list_profiles() -> dict[str, Any]:
        """List configured connection profiles without secrets."""

        try:
            return {"profiles": table_locator.list_profiles()}
        except (DbLensError, Exception) as exc:
            return tool_error("list_profiles", exc)

    @server.tool()
    def refresh_table_cache(profile: str) -> dict[str, Any]:
        """Refresh cached table-to-database mappings for a profile."""

        try:
            return table_locator.refresh_profile(profile)
        except (DbLensError, Exception) as exc:
            return tool_error("refresh_table_cache", exc, profile=profile)

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
    def find_tables(table: str, profile: str | None = None) -> dict[str, Any]:
        """Find configured databases containing a table name or keyword."""

        try:
            return table_locator.find_tables(table, profile=profile)
        except (DbLensError, Exception) as exc:
            return tool_error("find_tables", exc, profile=profile, table=table)

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
    def list_databases(profile: str | None = None) -> dict[str, Any]:
        """Get visible databases for a configured profile."""

        try:
            profile_name = profile
            if profile_name is None:
                profile_name, _profile_config = table_locator.config_loader.load().resolve_profile(profile)
            return {
                "profile": profile_name,
                "databases": [
                    {"name": name}
                    for name in database_service.list_databases(profile_name)
                ],
            }
        except (DbLensError, Exception) as exc:
            return tool_error("list_databases", exc, profile=profile)

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
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

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
    def describe_table(
        table: str,
        profile: str | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Get table columns, primary key, and comments."""

        try:
            profile_name, database_name = _resolve_table_context(
                table_locator, table, profile, database
            )
            schema = database_service.describe_table(profile_name, database_name, table)
            return {
                "profile": profile_name,
                "database": database_name,
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
        except TableResolutionError as exc:
            return table_resolution_error("describe_table", exc, profile=profile, table=table)
        except DbLensError as exc:
            return tool_error(
                "describe_table", exc, profile=profile, database=database, table=table
            )

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
    def list_indexes(
        table: str,
        profile: str | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Get table indexes."""

        try:
            profile_name, database_name = _resolve_table_context(
                table_locator, table, profile, database
            )
            indexes = database_service.list_indexes(profile_name, database_name, table)
            return {
                "profile": profile_name,
                "database": database_name,
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
        except TableResolutionError as exc:
            return table_resolution_error("list_indexes", exc, profile=profile, table=table)
        except DbLensError as exc:
            return tool_error("list_indexes", exc, profile=profile, database=database, table=table)

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
    def get_table_stats(
        table: str,
        profile: str | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Get estimated table statistics from metadata."""

        try:
            profile_name, database_name = _resolve_table_context(
                table_locator, table, profile, database
            )
            stats = database_service.get_table_stats(profile_name, database_name, table)
            return {
                "profile": profile_name,
                "database": database_name,
                "table": table,
                "row_count_estimate": stats.row_count_estimate,
                "data_length_bytes": stats.data_length_bytes,
                "index_length_bytes": stats.index_length_bytes,
                "updated_at": stats.updated_at,
                "source": stats.source,
            }
        except TableResolutionError as exc:
            return table_resolution_error("get_table_stats", exc, profile=profile, table=table)
        except DbLensError as exc:
            return tool_error(
                "get_table_stats", exc, profile=profile, database=database, table=table
            )

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
    def explain_select(
        sql: str,
        profile: str | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Run EXPLAIN for a single SELECT query after safety validation."""

        resolved = _resolve_query_context(sql, table_locator, profile, database)
        if isinstance(resolved, dict):
            return resolved
        profile_name, database_name = resolved
        result = query_service.inspect_query(
            sql,
            profile=profile_name,
            database=database_name,
            include_metadata=False,
        )
        return {
            "profile": profile_name,
            "database": database_name,
            "accepted": result.accepted,
            "query_type": result.query_type,
            "explain": _explain_response(result.explain_summary),
            "risk_hints": _risk_hint_response(result.risk_hints),
            "reason": _safe_reason(result.reason),
            "risk": result.risk,
        }

    @server.tool(annotations=READ_ONLY_TOOL_ANNOTATIONS)
    def inspect_query(
        sql: str,
        profile: str | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """Return database context for a single SELECT query."""

        resolved = _resolve_query_context(sql, table_locator, profile, database)
        if isinstance(resolved, dict):
            return resolved
        profile_name, database_name = resolved
        result = query_service.inspect_query(sql, profile=profile_name, database=database_name)
        return {
            "profile": profile_name,
            "database": database_name,
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


def table_resolution_error(
    tool: str,
    exc: TableResolutionError,
    **extra: Any,
) -> dict[str, Any]:
    response = tool_error(tool, exc, **extra)
    response["risk"] = exc.code
    if exc.candidates:
        response["candidates"] = exc.candidates
    return response


def _resolve_table_context(
    table_locator: TableLocatorService,
    table: str,
    profile: str | None,
    database: str | None,
) -> tuple[str, str]:
    if profile and database:
        return profile, database
    return table_locator.resolve_table_database(table, profile=profile, database=database)


def _resolve_query_context(
    sql: str,
    table_locator: TableLocatorService,
    profile: str | None,
    database: str | None,
) -> tuple[str, str] | dict[str, Any]:
    try:
        if profile and database:
            return profile, database
        safe_query = SqlGuard().validate_select(sql)
        profile_name, _profile_config = table_locator.config_loader.load().resolve_profile(profile)
        if database:
            table_locator.resolve_table_database(
                safe_query.referenced_tables[0] if safe_query.referenced_tables else "",
                profile=profile_name,
                database=database,
            )
            return profile_name, database
        if not safe_query.referenced_tables:
            return {
                "accepted": False,
                "reason": "SQL has no resolvable physical table; specify database explicitly.",
                "risk": "database_required",
                "profile": profile_name,
                "database": None,
            }
        resolved_databases = {
            table_locator.resolve_table_database(table, profile=profile_name)[1]
            for table in safe_query.referenced_tables
        }
        if len(resolved_databases) == 1:
            return profile_name, next(iter(resolved_databases))
        return {
            "accepted": False,
            "reason": "Referenced tables resolve to multiple databases; specify database explicitly.",
            "risk": "ambiguous_database",
            "profile": profile_name,
            "databases": sorted(resolved_databases),
        }
    except TableResolutionError as exc:
        return table_resolution_error("query_context", exc, profile=profile)
    except Exception as exc:
        return tool_error("query_context", exc, profile=profile)


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
