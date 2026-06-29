"""Configuration models."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field, model_validator


class ProfileConfig(BaseModel):
    """Connection profile stored in local config."""

    driver: str = "mysql"
    host: str = "127.0.0.1"
    port: int = Field(default=3306, ge=1, le=65535)
    databases: List[str] = Field(min_length=1)
    username: str
    password: str
    connect_timeout_seconds: int = Field(default=5, ge=1)
    read_timeout_seconds: int = Field(default=10, ge=1)

    @model_validator(mode="before")
    @classmethod
    def migrate_single_database(cls, data: Any) -> Any:
        """Accept the deprecated single-database shape while loading old configs."""

        if isinstance(data, dict) and "databases" not in data and "database" in data:
            migrated = dict(data)
            migrated["databases"] = [migrated.pop("database")]
            return migrated
        return data

    def public_dict(self) -> dict:
        """Return profile fields that are safe to show in CLI output."""

        return {
            "driver": self.driver,
            "host": self.host,
            "port": self.port,
            "databases": list(self.databases),
            "username": self.username,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "read_timeout_seconds": self.read_timeout_seconds,
        }


class AppConfig(BaseModel):
    """Top-level TOML config shape."""

    profiles: Dict[str, ProfileConfig] = Field(default_factory=dict)

    def get_profile(self, name: str) -> tuple[str, ProfileConfig]:
        """Return the named profile."""

        if name not in self.profiles:
            raise KeyError(f"Profile {name!r} does not exist.")
        return name, self.profiles[name]

    def resolve_profile(self, name: str | None = None) -> tuple[str, ProfileConfig]:
        """Return an explicit profile, or the only configured profile if unambiguous."""

        if name:
            return self.get_profile(name)
        if len(self.profiles) == 1:
            profile_name = next(iter(self.profiles))
            return profile_name, self.profiles[profile_name]
        if not self.profiles:
            raise KeyError("No profile configured.")
        raise KeyError("Multiple profiles are configured; specify profile explicitly.")
