"""MCP tool registration."""

from __future__ import annotations

from typing import Any, Protocol

from db_lens_mcp.application.query_inspection_service import QueryInspectionService
from db_lens_mcp.domain.risk_rules import RiskRules
from db_lens_mcp.domain.sql_guard import SqlGuard
from db_lens_mcp.mcp.schemas import not_implemented_response


class ToolRegistrar(Protocol):
    """Subset of FastMCP needed for registering tools."""

    def tool(self) -> Any:
        """Return the tool decorator."""


def register_tools(server: ToolRegistrar) -> None:
    """Register the fixed first-phase MCP tool surface."""

    query_service = QueryInspectionService(sql_guard=SqlGuard(), risk_rules=RiskRules())

    def placeholder(tool: str, **extra: Any) -> dict[str, Any]:
        response = not_implemented_response(tool)
        response.update(extra)
        return response

    @server.tool()
    def list_databases(profile: str) -> dict[str, Any]:
        """Get visible databases for a configured profile."""

        return placeholder("list_databases", profile=profile)

    @server.tool()
    def list_tables(profile: str, database: str, keyword: str | None = None) -> dict[str, Any]:
        """Get tables in a database, optionally filtered by keyword."""

        return placeholder("list_tables", profile=profile, database=database, keyword=keyword)

    @server.tool()
    def describe_table(profile: str, database: str, table: str) -> dict[str, Any]:
        """Get table columns, primary key, and comments."""

        return placeholder("describe_table", profile=profile, database=database, table=table)

    @server.tool()
    def list_indexes(profile: str, database: str, table: str) -> dict[str, Any]:
        """Get table indexes."""

        return placeholder("list_indexes", profile=profile, database=database, table=table)

    @server.tool()
    def get_table_stats(profile: str, database: str, table: str) -> dict[str, Any]:
        """Get estimated table statistics from metadata."""

        return placeholder("get_table_stats", profile=profile, database=database, table=table)

    @server.tool()
    def explain_select(profile: str, database: str, sql: str) -> dict[str, Any]:
        """Run EXPLAIN for a single SELECT query after safety validation."""

        result = query_service.inspect_query(sql)
        return {
            "profile": profile,
            "database": database,
            "accepted": result.accepted,
            "query_type": result.query_type,
            "reason": result.reason,
            "risk": result.risk,
        }

    @server.tool()
    def inspect_query(profile: str, database: str, sql: str) -> dict[str, Any]:
        """Return database context for a single SELECT query."""

        result = query_service.inspect_query(sql)
        return {
            "profile": profile,
            "database": database,
            "accepted": result.accepted,
            "query_type": result.query_type,
            "referenced_tables": result.referenced_tables,
            "risk_hints": [
                {
                    "level": hint.level.value,
                    "code": hint.code,
                    "message": hint.message,
                }
                for hint in result.risk_hints
            ],
            "ai_summary": result.ai_summary,
            "reason": result.reason,
            "risk": result.risk,
        }
