from datetime import datetime

from db_lens_mcp.infrastructure.mysql.metadata_reader import MySqlMetadataReader


class FakeConnectionFactory:
    def __init__(self, connection):
        self.connection = connection
        self.profiles = []

    def create(self, profile):
        self.profiles.append(profile)
        return self.connection


class FakeConnection:
    def __init__(self, result_sets):
        self.result_sets = list(result_sets)
        self.executed = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.connection.executed.append((sql, params))
        self.rows = self.connection.result_sets.pop(0)

    def fetchall(self):
        return self.rows


def test_list_databases_uses_information_schema() -> None:
    connection = FakeConnection([[{"name": "app_db"}, {"name": "reporting"}]])
    reader = MySqlMetadataReader(connection_factory=FakeConnectionFactory(connection))

    databases = reader.list_databases("local-dev")

    assert databases == ["app_db", "reporting"]
    assert "information_schema.SCHEMATA" in connection.executed[0][0]
    assert connection.closed is True


def test_list_tables_supports_keyword_filter() -> None:
    connection = FakeConnection(
        [[{"name": "orders", "comment": "订单表", "table_type": "BASE TABLE"}]]
    )
    reader = MySqlMetadataReader(connection_factory=FakeConnectionFactory(connection))

    tables = reader.list_tables("local-dev", "app_db", keyword="order")

    assert tables == [{"name": "orders", "comment": "订单表", "table_type": "BASE TABLE"}]
    assert connection.executed[0][1] == ("app_db", "order", "%order%")
    assert "information_schema.TABLES" in connection.executed[0][0]


def test_list_tables_treats_blank_keyword_as_no_filter() -> None:
    connection = FakeConnection([[{"name": "orders", "comment": "", "table_type": "BASE TABLE"}]])
    reader = MySqlMetadataReader(connection_factory=FakeConnectionFactory(connection))

    tables = reader.list_tables("local-dev", "app_db", keyword=" ")

    assert tables == [{"name": "orders", "comment": "", "table_type": "BASE TABLE"}]
    assert connection.executed[0][1] == ("app_db", None, None)


def test_describe_table_maps_columns_and_primary_key() -> None:
    connection = FakeConnection(
        [
            [
                {
                    "name": "id",
                    "type": "bigint",
                    "nullable": "NO",
                    "default_value": None,
                    "column_key": "PRI",
                    "comment": "主键",
                },
                {
                    "name": "user_id",
                    "type": "bigint",
                    "nullable": "NO",
                    "default_value": None,
                    "column_key": "",
                    "comment": "用户",
                },
            ],
            [{"comment": "订单表"}],
        ]
    )
    reader = MySqlMetadataReader(connection_factory=FakeConnectionFactory(connection))

    schema = reader.describe_table("local-dev", "app_db", "orders")

    assert schema.database == "app_db"
    assert schema.table == "orders"
    assert schema.primary_key == ["id"]
    assert schema.columns[0].primary_key is True
    assert schema.columns[1].name == "user_id"
    assert schema.comment == "订单表"
    assert all("information_schema." in sql for sql, _ in connection.executed)


def test_list_indexes_groups_columns_in_order() -> None:
    connection = FakeConnection(
        [
            [
                {
                    "name": "idx_user_created",
                    "non_unique": 1,
                    "type": "BTREE",
                    "column_name": "user_id",
                    "seq_in_index": 1,
                    "cardinality": 100,
                },
                {
                    "name": "idx_user_created",
                    "non_unique": 1,
                    "type": "BTREE",
                    "column_name": "created_at",
                    "seq_in_index": 2,
                    "cardinality": 100,
                },
            ]
        ]
    )
    reader = MySqlMetadataReader(connection_factory=FakeConnectionFactory(connection))

    indexes = reader.list_indexes("local-dev", "app_db", "orders")

    assert len(indexes) == 1
    assert indexes[0].name == "idx_user_created"
    assert indexes[0].unique is False
    assert indexes[0].columns == ["user_id", "created_at"]
    assert "information_schema.STATISTICS" in connection.executed[0][0]


def test_get_table_stats_maps_information_schema_values() -> None:
    connection = FakeConnection(
        [
            [
                {
                    "row_count_estimate": 1200,
                    "data_length_bytes": 2048,
                    "index_length_bytes": 1024,
                    "updated_at": datetime(2026, 6, 27, 10, 0, 0),
                }
            ]
        ]
    )
    reader = MySqlMetadataReader(connection_factory=FakeConnectionFactory(connection))

    stats = reader.get_table_stats("local-dev", "app_db", "orders")

    assert stats.row_count_estimate == 1200
    assert stats.data_length_bytes == 2048
    assert stats.index_length_bytes == 1024
    assert stats.updated_at == "2026-06-27T10:00:00"
    assert stats.source == "information_schema"
    assert "information_schema.TABLES" in connection.executed[0][0]


def test_metadata_reader_wraps_driver_errors_without_sql_text() -> None:
    connection = FakeConnection([])
    reader = MySqlMetadataReader(connection_factory=FakeConnectionFactory(connection))

    try:
        reader.list_databases("local-dev")
    except Exception as exc:
        error = exc
    else:
        raise AssertionError("Expected metadata reader to fail.")

    assert error.__class__.__name__ == "DatabaseAccessError"
    assert str(error) == "Metadata query failed."
    assert "information_schema" not in str(error)
    assert connection.closed is True
