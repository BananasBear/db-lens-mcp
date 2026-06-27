"""Application service for table metadata use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from db_lens_mcp.domain.models import IndexInfo, TableSchema, TableStats


class MetadataReader(Protocol):
    """Read-only metadata port implemented by MySQL infrastructure."""

    def list_databases(self, profile: str) -> list[str]:
        """Return visible database names for a profile."""

    def list_tables(self, profile: str, database: str, keyword: str | None = None) -> list[dict]:
        """Return visible tables for a database."""

    def describe_table(self, profile: str, database: str, table: str) -> TableSchema:
        """Return table schema metadata."""

    def list_indexes(self, profile: str, database: str, table: str) -> list[IndexInfo]:
        """Return table index metadata."""

    def get_table_stats(self, profile: str, database: str, table: str) -> TableStats:
        """Return table statistics from metadata sources."""


@dataclass(frozen=True)
class DatabaseInspectionService:
    """Coordinate read-only database metadata operations."""

    metadata_reader: MetadataReader

    def describe_table(self, profile: str, database: str, table: str) -> TableSchema:
        """Return schema metadata for a table."""

        return self.metadata_reader.describe_table(profile, database, table)

    def list_indexes(self, profile: str, database: str, table: str) -> list[IndexInfo]:
        """Return index metadata for a table."""

        return self.metadata_reader.list_indexes(profile, database, table)
