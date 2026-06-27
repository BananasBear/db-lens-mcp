"""Application service for SELECT query inspection."""

from __future__ import annotations

from dataclasses import dataclass, field

from db_lens_mcp.domain.models import ExplainSummary, RiskHint, TableSchema, TableStats
from db_lens_mcp.domain.risk_rules import RiskRules
from db_lens_mcp.domain.sql_guard import SqlGuard


@dataclass(frozen=True)
class QueryInspectionResult:
    """Combined context returned by the first-phase `inspect_query` tool."""

    accepted: bool
    query_type: str | None = None
    referenced_tables: list[str] = field(default_factory=list)
    tables: list[TableSchema] = field(default_factory=list)
    stats: list[TableStats] = field(default_factory=list)
    explain_summary: ExplainSummary | None = None
    risk_hints: list[RiskHint] = field(default_factory=list)
    ai_summary: str | None = None
    reason: str | None = None
    risk: str | None = None


@dataclass(frozen=True)
class QueryInspectionService:
    """Coordinate SQL validation, metadata lookup, EXPLAIN, and risk hints."""

    sql_guard: SqlGuard
    risk_rules: RiskRules

    def inspect_query(self, sql: str) -> QueryInspectionResult:
        """Inspect a query.

        Database lookup and EXPLAIN are added in later phases. For the skeleton,
        this method exposes the expected accepted/rejected response shape.
        """

        try:
            safe_query = self.sql_guard.validate_select(sql)
        except Exception as exc:
            return QueryInspectionResult(
                accepted=False,
                reason=str(exc),
                risk="blocked_invalid_sql",
            )

        return QueryInspectionResult(
            accepted=True,
            query_type="SELECT",
            referenced_tables=safe_query.referenced_tables,
            ai_summary="SQL passed safety validation. Database inspection is not implemented yet.",
        )
