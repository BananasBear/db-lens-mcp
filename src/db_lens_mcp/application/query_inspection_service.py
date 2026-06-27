"""Application service for SELECT query inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from db_lens_mcp.domain.models import ExplainSummary, IndexInfo, RiskHint, TableSchema, TableStats
from db_lens_mcp.domain.risk_rules import RiskRules
from db_lens_mcp.domain.sql_guard import SafeSelectQuery, SqlGuard


class ExplainRunner(Protocol):
    """Run EXPLAIN for a query that already passed SqlGuard."""

    def explain(self, profile: str, database: str, query: SafeSelectQuery) -> ExplainSummary:
        """Return normalized EXPLAIN summary."""


class MetadataService(Protocol):
    """Read table context needed to explain a SELECT to AI clients."""

    def describe_table(self, profile: str, database: str, table: str) -> TableSchema:
        """Return table schema metadata."""

    def list_indexes(self, profile: str, database: str, table: str) -> list[IndexInfo]:
        """Return table index metadata."""

    def get_table_stats(self, profile: str, database: str, table: str) -> TableStats:
        """Return estimated table statistics."""


@dataclass(frozen=True)
class QueryInspectionResult:
    """Combined context returned by the first-phase `inspect_query` tool."""

    accepted: bool
    query_type: str | None = None
    referenced_tables: list[str] = field(default_factory=list)
    tables: list[TableSchema] = field(default_factory=list)
    indexes: dict[str, list[IndexInfo]] = field(default_factory=dict)
    stats: list[TableStats] = field(default_factory=list)
    metadata_errors: list[dict[str, str]] = field(default_factory=list)
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
    explain_runner: ExplainRunner | None = None
    metadata_service: MetadataService | None = None

    def inspect_query(
        self,
        sql: str,
        profile: str | None = None,
        database: str | None = None,
        params: list | None = None,
        include_metadata: bool = True,
    ) -> QueryInspectionResult:
        """Inspect a query.

        The service keeps the safety order explicit: validate SQL first, then
        read metadata and run tool-generated EXPLAIN only for a safe SELECT.
        """

        try:
            safe_query = self.sql_guard.validate_select(sql, params=params)
        except Exception as exc:
            return QueryInspectionResult(
                accepted=False,
                reason=str(exc),
                risk="blocked_invalid_sql",
            )

        tables: list[TableSchema] = []
        indexes: dict[str, list[IndexInfo]] = {}
        stats: list[TableStats] = []
        metadata_errors: list[dict[str, str]] = []
        if include_metadata and self.metadata_service and profile and database:
            for table_name in safe_query.referenced_tables:
                try:
                    tables.append(
                        self.metadata_service.describe_table(profile, database, table_name)
                    )
                    indexes[table_name] = self.metadata_service.list_indexes(
                        profile, database, table_name
                    )
                    stats.append(
                        self.metadata_service.get_table_stats(profile, database, table_name)
                    )
                except Exception as exc:
                    metadata_errors.append(
                        {
                            "table": table_name,
                            "reason": str(exc),
                        }
                    )

        explain_summary = None
        risk_hints: list[RiskHint] = []
        if self.explain_runner and profile and database:
            try:
                explain_summary = self.explain_runner.explain(profile, database, safe_query)
                risk_hints = self.risk_rules.from_explain_summary(explain_summary)
            except Exception as exc:
                return QueryInspectionResult(
                    accepted=False,
                    reason=str(exc),
                    risk="explain_failed",
                )

        return QueryInspectionResult(
            accepted=True,
            query_type="SELECT",
            referenced_tables=safe_query.referenced_tables,
            tables=tables,
            indexes=indexes,
            stats=stats,
            metadata_errors=metadata_errors,
            explain_summary=explain_summary,
            risk_hints=risk_hints,
            ai_summary=_build_ai_summary(
                safe_query.referenced_tables,
                bool(tables),
                bool(metadata_errors),
            ),
        )


def _build_ai_summary(
    referenced_tables: list[str],
    has_metadata: bool,
    has_metadata_errors: bool,
) -> str:
    if not referenced_tables:
        return "SQL passed safety validation. No physical table was detected."
    if has_metadata_errors and has_metadata:
        return "SQL passed safety validation. Partial table metadata was collected; some table context is missing."
    if has_metadata_errors:
        return "SQL passed safety validation. Table metadata could not be collected."
    if has_metadata:
        return "SQL passed safety validation. Table schema, indexes, stats, and EXPLAIN were collected where available."
    return "SQL passed safety validation. Table metadata was not collected."
