"""Risk hint rules."""

from __future__ import annotations

from db_lens_mcp.domain.models import ExplainSummary, RiskHint, RiskLevel


class RiskRules:
    """Generate simple, fact-based risk hints from normalized EXPLAIN output."""

    def from_explain_summary(self, summary: ExplainSummary) -> list[RiskHint]:
        """Return first-phase risk hints.

        The skeleton keeps this intentionally minimal. Concrete EXPLAIN parsing
        and risk rules are implemented after MySQL EXPLAIN support exists.
        """

        if summary.estimated_rows is None:
            return [
                RiskHint(
                    level=RiskLevel.INFO,
                    code="unknown_table_stats",
                    message="执行计划缺少扫描行数估算，暂时无法判断扫描规模。",
                )
            ]
        return []
