"""MySQL EXPLAIN runner placeholder."""

from __future__ import annotations

from db_lens_mcp.domain.models import ExplainSummary
from db_lens_mcp.domain.sql_guard import SafeSelectQuery
from db_lens_mcp.errors import DatabaseAccessError


class MySqlExplainRunner:
    """Run EXPLAIN only for SQL already accepted by SqlGuard."""

    def explain(self, profile: str, database: str, query: SafeSelectQuery) -> ExplainSummary:
        raise DatabaseAccessError(f"EXPLAIN is not implemented for {profile}:{database}.")
