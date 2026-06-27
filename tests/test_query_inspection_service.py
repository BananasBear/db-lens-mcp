from db_lens_mcp.application.query_inspection_service import QueryInspectionService
from db_lens_mcp.domain.risk_rules import RiskRules
from db_lens_mcp.domain.sql_guard import SqlGuard


def test_query_inspection_rejects_sql_until_guard_is_implemented() -> None:
    service = QueryInspectionService(sql_guard=SqlGuard(), risk_rules=RiskRules())

    result = service.inspect_query("select * from orders")

    assert result.accepted is False
    assert result.risk == "blocked_invalid_sql"
    assert result.reason == "SQL validation is not implemented yet."
