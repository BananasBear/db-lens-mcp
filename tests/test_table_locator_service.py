from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from db_lens_mcp.application.table_locator_service import (
    TableLocatorService,
    TableMappingCache,
    TableResolutionError,
)
from db_lens_mcp.infrastructure.config.config_models import AppConfig, ProfileConfig


class FakeConfigLoader:
    def __init__(self, config):
        self.config = config

    def load(self):
        return self.config


class FakeDatabaseService:
    def __init__(self, tables_by_database):
        self.tables_by_database = tables_by_database
        self.list_tables_calls = []

    def list_tables(self, profile, database, keyword=None):
        self.list_tables_calls.append((profile, database, keyword))
        return [
            {"name": table, "comment": "", "table_type": "BASE TABLE"}
            for table in self.tables_by_database[database]
        ]


def test_refresh_profile_caches_table_mapping(tmp_path: Path) -> None:
    service = _service(tmp_path, {"app_db": ["orders"], "audit_db": ["events"]})

    result = service.refresh_profile("local-dev")

    assert result["databases"] == [
        {"name": "app_db", "table_count": 1},
        {"name": "audit_db", "table_count": 1},
    ]
    assert service.resolve_table_database("orders", profile="local-dev") == (
        "local-dev",
        "app_db",
    )


def test_find_tables_uses_cached_database_map(tmp_path: Path) -> None:
    service = _service(tmp_path, {"app_db": ["orders", "order_items"]})
    service.refresh_profile("local-dev")

    result = service.find_tables("order", profile="local-dev")

    assert result["matches"] == [
        {"profile": "local-dev", "database": "app_db", "table": "orders"},
        {"profile": "local-dev", "database": "app_db", "table": "order_items"},
    ]


def test_resolve_table_database_reports_ambiguous_table(tmp_path: Path) -> None:
    service = _service(tmp_path, {"app_db": ["orders"], "archive_db": ["orders"]})
    service.refresh_profile("local-dev")

    with pytest.raises(TableResolutionError) as exc_info:
        service.resolve_table_database("orders", profile="local-dev")

    assert exc_info.value.code == "ambiguous_table"
    assert exc_info.value.candidates == [
        {"database": "app_db", "table": "orders"},
        {"database": "archive_db", "table": "orders"},
    ]


def test_missing_table_does_not_refresh_when_cache_is_not_expired(tmp_path: Path) -> None:
    database_service = FakeDatabaseService({"app_db": ["orders"]})
    service = _service(tmp_path, {"app_db": ["orders"]}, database_service=database_service)
    service.refresh_profile("local-dev")
    database_service.list_tables_calls = []

    with pytest.raises(TableResolutionError) as exc_info:
        service.resolve_table_database("missing", profile="local-dev")

    assert exc_info.value.code == "table_not_found"
    assert database_service.list_tables_calls == []


def test_missing_table_refreshes_when_cache_is_expired(tmp_path: Path) -> None:
    database_service = FakeDatabaseService({"app_db": ["orders"]})
    service = _service(tmp_path, {"app_db": ["orders"]}, database_service=database_service)
    service.refresh_profile("local-dev")
    cache_data = service.cache.load()
    expired_at = datetime.now(timezone.utc) - timedelta(days=8)
    cache_data["profiles"]["local-dev"]["refreshed_at"] = (
        expired_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    service.cache.save(cache_data)
    database_service.list_tables_calls = []

    with pytest.raises(TableResolutionError) as exc_info:
        service.resolve_table_database("missing", profile="local-dev")

    assert exc_info.value.code == "table_not_found"
    assert database_service.list_tables_calls == [("local-dev", "app_db", None)]


def _service(tmp_path: Path, tables_by_database, database_service=None):
    config = AppConfig(
        profiles={
            "local-dev": ProfileConfig(
                databases=list(tables_by_database),
                username="readonly",
                password="enc:v1:secret",
            )
        }
    )
    return TableLocatorService(
        config_loader=FakeConfigLoader(config),
        database_service=database_service or FakeDatabaseService(tables_by_database),
        cache=TableMappingCache(tmp_path / "table-cache.json"),
    )
