from db_lens_mcp.application.query_inspection_service import QueryInspectionService
from db_lens_mcp.domain.models import ColumnInfo, ExplainSummary, IndexInfo, TableSchema, TableStats
from db_lens_mcp.domain.risk_rules import RiskRules
from db_lens_mcp.domain.sql_guard import SafeSelectQuery, SqlGuard


def test_query_inspection_reports_missing_sqlglot_dependency() -> None:
    service = QueryInspectionService(sql_guard=SqlGuard(), risk_rules=RiskRules())

    result = service.inspect_query("select * from orders")

    assert result.accepted is False
    assert result.risk == "blocked_invalid_sql"
    assert result.reason == "sqlglot is not installed. Install project dependencies."


class FakeGuard:
    def validate_select(self, sql, params=None):
        return SafeSelectQuery(sql=sql, referenced_tables=["orders"], params=params or [])


class MultiTableFakeGuard:
    def validate_select(self, sql, params=None):
        return SafeSelectQuery(
            sql=sql,
            referenced_tables=["orders", "order_items"],
            params=params or [],
        )


class FakeExplainRunner:
    def __init__(self) -> None:
        self.called = False

    def explain(self, profile, database, query):
        self.called = True
        assert profile == "local-dev"
        assert database == "app_db"
        return ExplainSummary(
            status="ok",
            tables=query.referenced_tables,
            access_types=["ref"],
            used_indexes=["idx_user_id"],
            estimated_rows=20,
            extra=[],
        )


class FakeMetadataService:
    def describe_table(self, profile, database, table):
        assert profile == "local-dev"
        assert database == "app_db"
        assert table == "orders"
        return TableSchema(
            database=database,
            table=table,
            columns=[
                ColumnInfo(
                    name="id",
                    type="bigint",
                    nullable=False,
                    default=None,
                    primary_key=True,
                    comment="主键",
                )
            ],
            primary_key=["id"],
            comment="订单表",
        )

    def list_indexes(self, profile, database, table):
        return [
            IndexInfo(
                name="PRIMARY",
                unique=True,
                type="BTREE",
                columns=["id"],
                cardinality=10,
            )
        ]

    def get_table_stats(self, profile, database, table):
        return TableStats(
            database=database,
            table=table,
            row_count_estimate=10,
            data_length_bytes=1024,
            index_length_bytes=512,
            updated_at=None,
            source="information_schema",
        )


class PartiallyFailingMetadataService(FakeMetadataService):
    def describe_table(self, profile, database, table):
        if table == "order_items":
            raise RuntimeError("metadata failed password=secret")
        return super().describe_table(profile, database, table)


def test_query_inspection_runs_explain_when_runner_is_available() -> None:
    service = QueryInspectionService(
        sql_guard=FakeGuard(),
        risk_rules=RiskRules(),
        explain_runner=FakeExplainRunner(),
    )

    result = service.inspect_query(
        "select * from orders where user_id = %s",
        profile="local-dev",
        database="app_db",
        params=[123],
    )

    assert result.accepted is True
    assert result.query_type == "SELECT"
    assert result.referenced_tables == ["orders"]
    assert result.explain_summary.status == "ok"
    assert result.explain_summary.used_indexes == ["idx_user_id"]


def test_query_inspection_collects_metadata_for_referenced_tables() -> None:
    service = QueryInspectionService(
        sql_guard=FakeGuard(),
        risk_rules=RiskRules(),
        explain_runner=FakeExplainRunner(),
        metadata_service=FakeMetadataService(),
    )

    result = service.inspect_query(
        "select * from orders where user_id = %s",
        profile="local-dev",
        database="app_db",
        params=[123],
    )

    assert result.accepted is True
    assert result.tables[0].table == "orders"
    assert result.tables[0].columns[0].name == "id"
    assert result.indexes["orders"][0].name == "PRIMARY"
    assert result.stats[0].row_count_estimate == 10
    assert "Table schema" in result.ai_summary


def test_query_inspection_keeps_explain_when_metadata_partially_fails() -> None:
    explain_runner = FakeExplainRunner()
    service = QueryInspectionService(
        sql_guard=MultiTableFakeGuard(),
        risk_rules=RiskRules(),
        explain_runner=explain_runner,
        metadata_service=PartiallyFailingMetadataService(),
    )

    result = service.inspect_query(
        "select * from orders join order_items on order_items.order_id = orders.id",
        profile="local-dev",
        database="app_db",
    )

    assert result.accepted is True
    assert explain_runner.called is True
    assert result.explain_summary.status == "ok"
    assert [table.table for table in result.tables] == ["orders"]
    assert result.metadata_errors == [
        {"table": "order_items", "reason": "metadata failed password=secret"}
    ]
    assert "Partial table metadata" in result.ai_summary
