"""MySQL metadata reader.

This adapter only runs fixed information_schema queries. It must not expose a
generic SQL execution method.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from db_lens_mcp.application.database_inspection_service import MetadataReader
from db_lens_mcp.domain.models import ColumnInfo, IndexInfo, TableSchema, TableStats
from db_lens_mcp.errors import DatabaseAccessError
from db_lens_mcp.infrastructure.mysql.connection_factory import MySqlConnectionFactory


@dataclass(frozen=True)
class MySqlMetadataReader(MetadataReader):
    """Read MySQL/MariaDB metadata using whitelisted queries."""

    connection_factory: MySqlConnectionFactory

    def list_databases(self, profile: str) -> list[str]:
        sql = """
            SELECT SCHEMA_NAME AS name
            FROM information_schema.SCHEMATA
            WHERE SCHEMA_NAME NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
            ORDER BY SCHEMA_NAME
        """
        with self._connection(profile) as connection:
            rows = _fetch_all(connection, sql)
        return [row["name"] for row in rows]

    def list_tables(self, profile: str, database: str, keyword: str | None = None) -> list[dict]:
        keyword = keyword.strip() if keyword else None
        if not keyword:
            keyword = None
        sql = """
            SELECT TABLE_NAME AS name,
                   TABLE_COMMENT AS comment,
                   TABLE_TYPE AS table_type
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
              AND (%s IS NULL OR TABLE_NAME LIKE %s)
            ORDER BY TABLE_NAME
        """
        like_keyword = f"%{keyword}%" if keyword else None
        with self._connection(profile) as connection:
            return _fetch_all(connection, sql, (database, keyword, like_keyword))

    def describe_table(self, profile: str, database: str, table: str) -> TableSchema:
        columns_sql = """
            SELECT COLUMN_NAME AS name,
                   COLUMN_TYPE AS type,
                   IS_NULLABLE AS nullable,
                   COLUMN_DEFAULT AS default_value,
                   COLUMN_KEY AS column_key,
                   COLUMN_COMMENT AS comment
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        table_sql = """
            SELECT TABLE_COMMENT AS comment
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
        """
        with self._connection(profile) as connection:
            column_rows = _fetch_all(connection, columns_sql, (database, table))
            table_rows = _fetch_all(connection, table_sql, (database, table))
        columns = [
            ColumnInfo(
                name=row["name"],
                type=row["type"],
                nullable=row["nullable"] == "YES",
                default=row["default_value"],
                primary_key=row["column_key"] == "PRI",
                comment=row.get("comment") or None,
            )
            for row in column_rows
        ]
        return TableSchema(
            database=database,
            table=table,
            columns=columns,
            primary_key=[column.name for column in columns if column.primary_key],
            comment=(table_rows[0].get("comment") if table_rows else None) or None,
        )

    def list_indexes(self, profile: str, database: str, table: str) -> list[IndexInfo]:
        sql = """
            SELECT INDEX_NAME AS name,
                   NON_UNIQUE AS non_unique,
                   INDEX_TYPE AS type,
                   COLUMN_NAME AS column_name,
                   SEQ_IN_INDEX AS seq_in_index,
                   CARDINALITY AS cardinality
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        with self._connection(profile) as connection:
            rows = _fetch_all(connection, sql, (database, table))
        grouped: dict[str, dict] = {}
        for row in rows:
            index = grouped.setdefault(
                row["name"],
                {
                    "name": row["name"],
                    "unique": row["non_unique"] == 0,
                    "type": row["type"],
                    "columns": [],
                    "cardinality": row.get("cardinality"),
                },
            )
            index["columns"].append(row["column_name"])
        return [
            IndexInfo(
                name=item["name"],
                unique=item["unique"],
                type=item["type"],
                columns=item["columns"],
                cardinality=item["cardinality"],
            )
            for item in grouped.values()
        ]

    def get_table_stats(self, profile: str, database: str, table: str) -> TableStats:
        sql = """
            SELECT TABLE_ROWS AS row_count_estimate,
                   DATA_LENGTH AS data_length_bytes,
                   INDEX_LENGTH AS index_length_bytes,
                   UPDATE_TIME AS updated_at
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
        """
        with self._connection(profile) as connection:
            rows = _fetch_all(connection, sql, (database, table))
        row = rows[0] if rows else {}
        updated_at = row.get("updated_at")
        return TableStats(
            database=database,
            table=table,
            row_count_estimate=row.get("row_count_estimate"),
            data_length_bytes=row.get("data_length_bytes"),
            index_length_bytes=row.get("index_length_bytes"),
            updated_at=updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
            source="information_schema",
        )

    @contextmanager
    def _connection(self, profile: str) -> Iterator[object]:
        connection = self.connection_factory.create(profile)
        try:
            yield connection
        finally:
            close = getattr(connection, "close", None)
            if callable(close):
                close()


def _fetch_all(connection: object, sql: str, params: tuple | None = None) -> list[dict]:
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
    except Exception as exc:
        raise DatabaseAccessError("Metadata query failed.") from exc
