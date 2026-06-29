"""Resolve tables to configured databases without making AI clients guess."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db_lens_mcp.application.database_inspection_service import DatabaseInspectionService
from db_lens_mcp.errors import ConfigurationError
from db_lens_mcp.infrastructure.config.config_loader import ConfigLoader, resolve_config_path
from db_lens_mcp.infrastructure.config.config_models import ProfileConfig

DEFAULT_TABLE_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


class TableResolutionError(Exception):
    """Raised when a table cannot be mapped to one configured database."""

    def __init__(self, code: str, message: str, candidates: list[dict[str, str]] | None = None):
        super().__init__(message)
        self.code = code
        self.candidates = candidates or []


@dataclass(frozen=True)
class TableMappingCache:
    """Small JSON cache for profile/database/table mappings."""

    path: Path

    @classmethod
    def for_config(cls, config_path: Path | None = None) -> "TableMappingCache":
        path = resolve_config_path(config_path).parent / "table-cache.json"
        return cls(path=path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"profiles": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"profiles": {}}

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@dataclass
class TableLocatorService:
    """Find configured databases by table name or keyword."""

    config_loader: ConfigLoader
    database_service: DatabaseInspectionService
    cache: TableMappingCache
    ttl_seconds: int = DEFAULT_TABLE_CACHE_TTL_SECONDS

    def list_profiles(self) -> list[dict[str, Any]]:
        config = self.config_loader.load()
        return [
            {
                "name": name,
                "driver": profile.driver,
                "host": profile.host,
                "port": profile.port,
                "databases": list(profile.databases),
                "username": profile.username,
            }
            for name, profile in sorted(config.profiles.items())
        ]

    def refresh_profile(self, profile: str) -> dict[str, Any]:
        profile_name, profile_config = self._resolve_profile(profile)
        profile_cache = {
            "refreshed_at": _utc_now_iso(),
            "ttl_seconds": self.ttl_seconds,
            "databases": {},
            "table_index": {},
        }
        for database in profile_config.databases:
            tables = self.database_service.list_tables(profile_name, database)
            table_names = [table["name"] for table in tables]
            profile_cache["databases"][database] = table_names
            for table_name in table_names:
                profile_cache["table_index"].setdefault(table_name.lower(), []).append(
                    {
                        "database": database,
                        "table": table_name,
                    }
                )
        data = self.cache.load()
        data.setdefault("profiles", {})[profile_name] = profile_cache
        self.cache.save(data)
        return {
            "profile": profile_name,
            "refreshed_at": profile_cache["refreshed_at"],
            "ttl_seconds": self.ttl_seconds,
            "databases": [
                {"name": database, "table_count": len(tables)}
                for database, tables in profile_cache["databases"].items()
            ],
        }

    def find_tables(self, table: str, profile: str | None = None) -> dict[str, Any]:
        profile_name, profile_config = self._resolve_profile(profile)
        profile_cache = self._profile_cache(profile_name)
        if profile_cache is None:
            self.refresh_profile(profile_name)
            profile_cache = self._profile_cache(profile_name)
        keyword = table.strip().lower()
        matches: list[dict[str, str]] = []
        for database in profile_config.databases:
            for table_name in profile_cache.get("databases", {}).get(database, []):
                if keyword in table_name.lower():
                    matches.append({"profile": profile_name, "database": database, "table": table_name})
        return {"profile": profile_name, "matches": matches}

    def resolve_table_database(
        self,
        table: str,
        profile: str | None = None,
        database: str | None = None,
    ) -> tuple[str, str]:
        profile_name, profile_config = self._resolve_profile(profile)
        if database:
            self._require_configured_database(profile_name, profile_config, database)
            return profile_name, database

        candidates = self._table_candidates(profile_name, table)
        if not candidates and self._cache_is_expired(profile_name):
            self.refresh_profile(profile_name)
            candidates = self._table_candidates(profile_name, table)
        if len(candidates) == 1:
            return profile_name, candidates[0]["database"]
        if not candidates:
            raise TableResolutionError(
                "table_not_found",
                f"Table {table!r} was not found in configured databases for profile {profile_name!r}.",
            )
        raise TableResolutionError(
            "ambiguous_table",
            f"Table {table!r} exists in multiple configured databases for profile {profile_name!r}.",
            candidates=candidates,
        )

    def _resolve_profile(self, profile: str | None) -> tuple[str, ProfileConfig]:
        try:
            return self.config_loader.load().resolve_profile(profile)
        except KeyError as exc:
            raise ConfigurationError(str(exc)) from exc

    def _require_configured_database(
        self,
        profile_name: str,
        profile_config: ProfileConfig,
        database: str,
    ) -> None:
        if database not in profile_config.databases:
            raise ConfigurationError(
                f"Database {database!r} is not configured for profile {profile_name!r}."
            )

    def _profile_cache(self, profile: str) -> dict[str, Any] | None:
        return self.cache.load().get("profiles", {}).get(profile)

    def _table_candidates(self, profile: str, table: str) -> list[dict[str, str]]:
        profile_cache = self._profile_cache(profile)
        if profile_cache is None:
            return []
        return list(profile_cache.get("table_index", {}).get(table.lower(), []))

    def _cache_is_expired(self, profile: str) -> bool:
        profile_cache = self._profile_cache(profile)
        if profile_cache is None:
            return True
        refreshed_at = profile_cache.get("refreshed_at")
        if not refreshed_at:
            return True
        try:
            refreshed = datetime.fromisoformat(str(refreshed_at).replace("Z", "+00:00"))
        except ValueError:
            return True
        if refreshed.tzinfo is None:
            refreshed = refreshed.replace(tzinfo=timezone.utc)
        ttl_seconds = int(profile_cache.get("ttl_seconds") or self.ttl_seconds)
        age_seconds = (datetime.now(timezone.utc) - refreshed).total_seconds()
        return age_seconds >= ttl_seconds


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
