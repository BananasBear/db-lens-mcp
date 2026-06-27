"""Core domain models.

These objects describe the database context exposed to AI clients. They avoid
driver-specific fields unless the field is already part of the public domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    """Risk severity for AI-facing query hints."""

    INFO = "info"
    WARNING = "warning"


@dataclass(frozen=True)
class ConnectionProfile:
    """A named database connection profile."""

    name: str
    driver: str
    host: str
    port: int
    database: str
    username: str
    password: str
    connect_timeout_seconds: int = 5
    read_timeout_seconds: int = 10


@dataclass(frozen=True)
class ColumnInfo:
    """Column metadata used by AI clients to understand table shape."""

    name: str
    type: str
    nullable: bool
    default: Any | None
    primary_key: bool
    comment: str | None = None


@dataclass(frozen=True)
class TableSchema:
    """Schema summary for a database table."""

    database: str
    table: str
    columns: list[ColumnInfo]
    primary_key: list[str] = field(default_factory=list)
    comment: str | None = None


@dataclass(frozen=True)
class IndexInfo:
    """Index metadata in AI-readable field order."""

    name: str
    unique: bool
    type: str
    columns: list[str]
    cardinality: int | None = None


@dataclass(frozen=True)
class TableStats:
    """Estimated table size information from metadata sources."""

    database: str
    table: str
    row_count_estimate: int | None
    data_length_bytes: int | None
    index_length_bytes: int | None
    updated_at: str | None
    source: str


@dataclass(frozen=True)
class ExplainSummary:
    """Normalized EXPLAIN highlights for first-phase risk rules."""

    status: str = "ok"
    tables: list[str] = field(default_factory=list)
    access_types: list[str] = field(default_factory=list)
    used_indexes: list[str] = field(default_factory=list)
    estimated_rows: int | None = None
    extra: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RiskHint:
    """AI-facing risk hint based only on confirmed metadata or EXPLAIN facts."""

    level: RiskLevel
    code: str
    message: str
