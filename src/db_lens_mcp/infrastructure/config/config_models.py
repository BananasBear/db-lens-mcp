"""Configuration models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileConfig(BaseModel):
    """Connection profile stored in local config."""

    driver: str = "mysql"
    host: str = "127.0.0.1"
    port: int = 3306
    database: str
    username: str
    password: str
    connect_timeout_seconds: int = Field(default=5, ge=1)
    read_timeout_seconds: int = Field(default=10, ge=1)


class AppConfig(BaseModel):
    """Top-level TOML config shape."""

    default_profile: str | None = None
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)
