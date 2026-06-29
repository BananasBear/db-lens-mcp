from db_lens_mcp.domain.models import ColumnInfo, ExplainSummary, IndexInfo, TableSchema, TableStats
from db_lens_mcp.errors import ConfigurationError
from db_lens_mcp.mcp.tools import register_tools


class FakeMcpServer:
    def __init__(self) -> None:
        self.tools = []
        self.tool_functions = {}
        self.tool_options = {}

    def tool(self, **options):
        def decorator(func):
            self.tools.append(func.__name__)
            self.tool_functions[func.__name__] = func
            self.tool_options[func.__name__] = options
            return func

        return decorator


class FakeDatabaseService:
    def list_databases(self, profile):
        return ["app_db"]

    def list_tables(self, profile, database, keyword=None):
        return [{"name": "orders", "comment": "订单表", "table_type": "BASE TABLE"}]

    def describe_table(self, profile, database, table):
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


class FakeQueryService:
    def __init__(self) -> None:
        self.include_metadata_values = []

    def inspect_query(self, sql, profile=None, database=None, params=None, include_metadata=True):
        self.include_metadata_values.append(include_metadata)

        class Result:
            accepted = True
            query_type = "SELECT"
            referenced_tables = ["orders"]
            tables = [
                TableSchema(
                    database="app_db",
                    table="orders",
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
            ]
            indexes = {
                "orders": [
                    IndexInfo(
                        name="PRIMARY",
                        unique=True,
                        type="BTREE",
                        columns=["id"],
                        cardinality=10,
                    )
                ]
            }
            stats = [
                TableStats(
                    database="app_db",
                    table="orders",
                    row_count_estimate=10,
                    data_length_bytes=1024,
                    index_length_bytes=512,
                    updated_at=None,
                    source="information_schema",
                )
            ]
            metadata_errors = []
            risk_hints = []
            ai_summary = "ok"
            reason = None
            risk = None
            explain_summary = ExplainSummary(
                status="ok",
                tables=["orders"],
                access_types=["ref"],
                used_indexes=["idx_user_id"],
                estimated_rows=20,
                extra=[],
            )

        return Result()


class FakeTableLocator:
    def list_profiles(self):
        return [
            {
                "name": "local-dev",
                "driver": "mysql",
                "host": "127.0.0.1",
                "port": 3306,
                "databases": ["app_db"],
                "username": "readonly",
            }
        ]

    def refresh_profile(self, profile):
        return {"profile": profile, "databases": [{"name": "app_db", "table_count": 1}]}

    def find_tables(self, table, profile=None):
        return {"profile": profile or "local-dev", "matches": [{"database": "app_db", "table": "orders"}]}

    def resolve_table_database(self, table, profile=None, database=None):
        return profile or "local-dev", database or "app_db"


class SkippedExplainQueryService:
    def __init__(self, status):
        self.status = status

    def inspect_query(self, sql, profile=None, database=None, params=None, include_metadata=True):
        class Result:
            accepted = True
            query_type = "SELECT"
            referenced_tables = ["orders"]
            tables = []
            indexes = {}
            stats = []
            metadata_errors = []
            risk_hints = []
            ai_summary = "ok"
            reason = None
            risk = None

        Result.explain_summary = ExplainSummary(status=self.status)
        return Result()


class SensitiveReasonQueryService:
    def inspect_query(self, sql, profile=None, database=None, params=None, include_metadata=True):
        class Result:
            accepted = False
            query_type = None
            referenced_tables = []
            tables = []
            indexes = {}
            stats = []
            metadata_errors = []
            risk_hints = []
            ai_summary = None
            explain_summary = None
            reason = "failed password=secret mysql://user:secret@db.local/app master_key=abc"
            risk = "explain_failed"

        return Result()


class MetadataErrorQueryService:
    def inspect_query(self, sql, profile=None, database=None, params=None, include_metadata=True):
        class Result:
            accepted = True
            query_type = "SELECT"
            referenced_tables = ["orders"]
            tables = []
            indexes = {}
            stats = []
            metadata_errors = [
                {
                    "table": "orders",
                    "reason": "metadata failed password=secret mysql://user:secret@db.local/app",
                }
            ]
            risk_hints = []
            ai_summary = "metadata missing"
            explain_summary = ExplainSummary(
                status="ok",
                tables=["orders"],
                access_types=["ref"],
                used_indexes=["idx_user_id"],
                estimated_rows=20,
                extra=[],
            )
            reason = None
            risk = None

        return Result()


def test_register_tools_adds_first_phase_tool_surface() -> None:
    server = FakeMcpServer()

    register_tools(server)

    assert server.tools == [
        "list_profiles",
        "refresh_table_cache",
        "find_tables",
        "list_databases",
        "list_tables",
        "describe_table",
        "list_indexes",
        "get_table_stats",
        "explain_select",
        "inspect_query",
    ]


def test_read_only_tools_have_mcp_annotations() -> None:
    server = FakeMcpServer()

    register_tools(server)

    read_only_tools = set(server.tools) - {"refresh_table_cache"}
    for tool_name in read_only_tools:
        annotations = server.tool_options[tool_name]["annotations"]
        assert annotations["readOnlyHint"] is True
        assert annotations["destructiveHint"] is False
        assert annotations["idempotentHint"] is True
        assert annotations["openWorldHint"] is True
    assert server.tool_options["refresh_table_cache"] == {}


def test_metadata_tools_return_service_results() -> None:
    server = FakeMcpServer()
    register_tools(server, database_service=FakeDatabaseService(), table_locator=FakeTableLocator())

    assert server.tool_functions["list_databases"]("local-dev") == {
        "profile": "local-dev",
        "databases": [{"name": "app_db"}],
    }
    assert (
        server.tool_functions["list_tables"]("local-dev", "app_db")["tables"][0]["name"]
        == "orders"
    )
    assert server.tool_functions["find_tables"]("ord", "local-dev")["matches"][0]["database"] == "app_db"


def test_explain_select_returns_explain_summary() -> None:
    server = FakeMcpServer()
    query_service = FakeQueryService()
    register_tools(
        server,
        database_service=FakeDatabaseService(),
        query_service=query_service,
        table_locator=FakeTableLocator(),
    )

    response = server.tool_functions["explain_select"](
        "select * from orders where user_id = %s",
        "local-dev",
        "app_db",
    )

    assert response["accepted"] is True
    assert query_service.include_metadata_values == [False]
    assert response["explain"]["summary"]["status"] == "ok"
    assert response["explain"]["summary"]["used_indexes"] == ["idx_user_id"]
    assert (
        server.tool_functions["describe_table"]("orders", "local-dev", "app_db")["columns"][0][
            "name"
        ]
        == "id"
    )
    assert (
        server.tool_functions["list_indexes"]("orders", "local-dev", "app_db")["indexes"][0][
            "columns"
        ]
        == ["id"]
    )
    assert (
        server.tool_functions["get_table_stats"]("orders", "local-dev", "app_db")[
            "row_count_estimate"
        ]
        == 10
    )


def test_inspect_query_returns_table_context() -> None:
    server = FakeMcpServer()
    query_service = FakeQueryService()
    register_tools(
        server,
        database_service=FakeDatabaseService(),
        query_service=query_service,
        table_locator=FakeTableLocator(),
    )

    response = server.tool_functions["inspect_query"](
        "select * from orders where user_id = %s",
        "local-dev",
        "app_db",
    )

    context = response["table_context"][0]
    assert query_service.include_metadata_values == [True]
    assert context["table"] == "orders"
    assert context["columns"][0]["name"] == "id"
    assert context["indexes"][0]["name"] == "PRIMARY"
    assert context["stats"]["row_count_estimate"] == 10


def test_inspect_query_metadata_errors_are_safe() -> None:
    server = FakeMcpServer()
    register_tools(
        server,
        database_service=FakeDatabaseService(),
        query_service=MetadataErrorQueryService(),
        table_locator=FakeTableLocator(),
    )

    response = server.tool_functions["inspect_query"](
        "select * from orders",
        "local-dev",
        "app_db",
    )

    assert response["accepted"] is True
    assert response["explain"]["summary"]["status"] == "ok"
    assert response["metadata_errors"][0]["table"] == "orders"
    assert "secret" not in response["metadata_errors"][0]["reason"]
    assert "password=<redacted>" in response["metadata_errors"][0]["reason"]
    assert "mysql://<redacted>:<redacted>@db.local/app" in response["metadata_errors"][0]["reason"]


def test_explain_select_returns_skipped_explain_status() -> None:
    server = FakeMcpServer()
    register_tools(
        server,
        database_service=FakeDatabaseService(),
        query_service=SkippedExplainQueryService("skipped_missing_params"),
        table_locator=FakeTableLocator(),
    )

    response = server.tool_functions["explain_select"](
        "select * from orders where user_id = %s",
        "local-dev",
        "app_db",
    )

    assert response["accepted"] is True
    assert response["explain"]["summary"]["status"] == "skipped_missing_params"


def test_inspect_query_returns_skipped_explain_status() -> None:
    server = FakeMcpServer()
    register_tools(
        server,
        database_service=FakeDatabaseService(),
        query_service=SkippedExplainQueryService("skipped_unsupported_placeholder_style"),
        table_locator=FakeTableLocator(),
    )

    response = server.tool_functions["inspect_query"](
        "select * from orders where user_id = ?",
        "local-dev",
        "app_db",
    )

    assert response["accepted"] is True
    assert response["explain"]["summary"]["status"] == "skipped_unsupported_placeholder_style"


def test_query_tool_reasons_are_safe() -> None:
    server = FakeMcpServer()
    register_tools(
        server,
        database_service=FakeDatabaseService(),
        query_service=SensitiveReasonQueryService(),
        table_locator=FakeTableLocator(),
    )

    for tool_name in ["explain_select", "inspect_query"]:
        response = server.tool_functions[tool_name](
            "select * from orders",
            "local-dev",
            "app_db",
        )

        assert response["accepted"] is False
        assert response["risk"] == "explain_failed"
        assert "secret" not in response["reason"]
        assert "master_key=<redacted>" in response["reason"]
        assert "mysql://<redacted>:<redacted>@db.local/app" in response["reason"]


def test_metadata_tool_errors_are_safe() -> None:
    class FailingDatabaseService(FakeDatabaseService):
        def list_databases(self, profile):
            raise ConfigurationError(
                "failed password=secret mysql://user:secret@db.local/app master_key=abc"
            )

        def describe_table(self, profile, database, table):
            raise ConfigurationError("pwd=secret")

        def list_indexes(self, profile, database, table):
            raise ConfigurationError("passwd=secret")

        def get_table_stats(self, profile, database, table):
            raise ConfigurationError("password=secret")

    server = FakeMcpServer()
    register_tools(server, database_service=FailingDatabaseService(), table_locator=FakeTableLocator())

    response = server.tool_functions["list_databases"]("local-dev")

    assert response["accepted"] is False
    assert response["risk"] == "list_databases_failed"
    assert "secret" not in response["reason"]
    assert "master_key=<redacted>" in response["reason"]
    assert "mysql://<redacted>:<redacted>@db.local/app" in response["reason"]

    for tool_name in ["describe_table", "list_indexes", "get_table_stats"]:
        tool_response = server.tool_functions[tool_name]("orders", "local-dev", "app_db")
        assert tool_response["accepted"] is False
        assert "secret" not in tool_response["reason"]
