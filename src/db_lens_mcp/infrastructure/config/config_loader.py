"""Configuration loader placeholder."""

from __future__ import annotations

from pathlib import Path

from db_lens_mcp.errors import ConfigurationError
from db_lens_mcp.infrastructure.config.config_models import AppConfig


DEFAULT_CONFIG_PATH = Path.home() / ".db-lens" / "config.toml"


class ConfigLoader:
    """Load db-lens-mcp TOML configuration."""

    def load(self, path: Path | None = None) -> AppConfig:
        """Load configuration.

        Real TOML parsing is implemented with the config feature. Returning an
        explicit error keeps the skeleton honest and avoids hidden defaults.
        """

        config_path = path or DEFAULT_CONFIG_PATH
        raise ConfigurationError(f"Configuration loading is not implemented for {config_path}.")
