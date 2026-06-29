import pytest

from db_lens_mcp.domain.sql_guard import SafeSelectQuery
from db_lens_mcp.errors import SafetyError
from db_lens_mcp.infrastructure.config.config_models import ProfileConfig
from db_lens_mcp.infrastructure.mysql.explain_runner import MySqlExplainRunner


class FakeConnectionFactory:
    def __init__(self, connection, database="app_db"):
        self.connection = connection
        self.database = database
        self.create_calls = []

    def create(self, profile, database=None):
        self.create_calls.append((profile, database))
        return self.connection

    def get_profile_config(self, profile):
        return profile, ProfileConfig(
            driver="mysql",
            databases=[self.database],
            username="readonly",
            password="enc:v1:password",
        )


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeCursor(self)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.connection.executed.append((sql, params))

    def fetchall(self):
        return self.connection.rows


def test_explain_runner_skips_placeholder_query_without_params() -> None:
    connection = FakeConnection([])
    runner = MySqlExplainRunner(connection_factory=FakeConnectionFactory(connection))
    query = SafeSelectQuery(
        sql="select * from orders where user_id = ?",
        referenced_tables=["orders"],
        has_placeholders=True,
    )

    summary = runner.explain("local-dev", "app_db", query)

    assert summary.status == "skipped_missing_params"
    assert summary.tables == ["orders"]
    assert connection.executed == []


def test_explain_runner_executes_tool_generated_explain_with_pymysql_params() -> None:
    connection = FakeConnection(
        [
            {
                "table": "orders",
                "type": "ref",
                "key": "idx_user_id",
                "rows": 20,
                "Extra": "Using where",
            }
        ]
    )
    runner = MySqlExplainRunner(connection_factory=FakeConnectionFactory(connection))
    query = SafeSelectQuery(
        sql="select * from orders where user_id = %s;",
        referenced_tables=["orders"],
        has_placeholders=True,
        params=[123],
    )

    summary = runner.explain("local-dev", "app_db", query)

    assert connection.executed == [
        ("EXPLAIN select * from orders where user_id = %s", (123,))
    ]
    assert summary.status == "ok"
    assert summary.tables == ["orders"]
    assert summary.access_types == ["ref"]
    assert summary.used_indexes == ["idx_user_id"]
    assert summary.estimated_rows == 20
    assert summary.extra == ["Using where"]


def test_explain_runner_skips_question_mark_placeholder_even_with_params() -> None:
    connection = FakeConnection([])
    runner = MySqlExplainRunner(connection_factory=FakeConnectionFactory(connection))
    query = SafeSelectQuery(
        sql="select * from orders where user_id = ?",
        referenced_tables=["orders"],
        has_placeholders=True,
        params=[123],
    )

    summary = runner.explain("local-dev", "app_db", query)

    assert summary.status == "skipped_unsupported_placeholder_style"
    assert connection.executed == []


def test_explain_runner_rejects_database_mismatch() -> None:
    connection = FakeConnection([])
    runner = MySqlExplainRunner(connection_factory=FakeConnectionFactory(connection, database="app_db"))
    query = SafeSelectQuery(sql="select * from orders", referenced_tables=["orders"])

    with pytest.raises(SafetyError, match="must be configured"):
        runner.explain("local-dev", "other_db", query)
