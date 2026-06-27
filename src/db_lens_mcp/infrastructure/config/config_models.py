"""Configuration models."""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProfileConfig(BaseModel):
    """Connection profile stored in local config."""

    driver: str = "mysql"
    host: str = "127.0.0.1"
    port: int = Field(default=3306, ge=1, le=65535)
    database: str
    username: str
    password: str
    connect_timeout_seconds: int = Field(default=5, ge=1)
    read_timeout_seconds: int = Field(default=10, ge=1)

    def public_dict(self) -> dict:
        """Return profile fields that are safe to show in CLI output."""

        return {
            "driver": self.driver,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "read_timeout_seconds": self.read_timeout_seconds,
        }


class AppConfig(BaseModel):
    """Top-level TOML config shape."""

    default_profile: Optional[str] = None
    profiles: Dict[str, ProfileConfig] = Field(default_factory=dict)

    def get_profile(self, name: Optional[str] = None) -> tuple[str, ProfileConfig]:
        """Return the named profile or the configured default profile."""

        profile_name = name or self.default_profile
        if not profile_name:
            raise KeyError("No profile specified and no default_profile configured.")
        if profile_name not in self.profiles:
            raise KeyError(f"Profile {profile_name!r} does not exist.")
        return profile_name, self.profiles[profile_name]
