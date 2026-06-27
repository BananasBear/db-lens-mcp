"""MySQL metadata reader placeholder."""

from __future__ import annotations

from db_lens_mcp.application.database_inspection_service import MetadataReader
from db_lens_mcp.domain.models import IndexInfo, TableSchema, TableStats
from db_lens_mcp.errors import DatabaseAccessError


class MySqlMetadataReader(MetadataReader):
    """Read MySQL/MariaDB metadata using whitelisted queries."""

    def list_databases(self, profile: str) -> list[str]:
        raise DatabaseAccessError(f"list_databases is not implemented for {profile!r}.")

    def list_tables(self, profile: str, database: str, keyword: str | None = None) -> list[dict]:
        raise DatabaseAccessError(f"list_tables is not implemented for {database!r}.")

    def describe_table(self, profile: str, database: str, table: str) -> TableSchema:
        raise DatabaseAccessError(f"describe_table is not implemented for {database}.{table}.")

    def list_indexes(self, profile: str, database: str, table: str) -> list[IndexInfo]:
        raise DatabaseAccessError(f"list_indexes is not implemented for {database}.{table}.")

    def get_table_stats(self, profile: str, database: str, table: str) -> TableStats:
        raise DatabaseAccessError(f"get_table_stats is not implemented for {database}.{table}.")
