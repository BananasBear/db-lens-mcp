"""MySQL connection factory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from db_lens_mcp.errors import ConfigurationError
from db_lens_mcp.errors import DatabaseAccessError
from db_lens_mcp.infrastructure.config.config_loader import ConfigLoader
from db_lens_mcp.infrastructure.config.config_models import ProfileConfig
from db_lens_mcp.infrastructure.secrets.secret_store import SecretStore


@dataclass
class MySqlConnectionFactory:
    """Create MySQL/MariaDB connections from encrypted local profiles."""

    config_loader: ConfigLoader
    secret_store: SecretStore
    import_driver: Callable[[], tuple[object, object]] | None = None

    def create(self, profile: str | None = None) -> object:
        """Create a database connection for a profile."""

        try:
            profile_name, profile_config = self.get_profile_config(profile)
            password = self.secret_store.decrypt(profile_config.password)
        except ConfigurationError:
            raise

        try:
            pymysql, dict_cursor = (
                self.import_driver() if self.import_driver else _import_pymysql_driver()
            )
        except ModuleNotFoundError as exc:
            raise DatabaseAccessError(
                "PyMySQL is not installed. Install project dependencies before connecting."
            ) from exc

        try:
            return pymysql.connect(
                host=profile_config.host,
                port=profile_config.port,
                user=profile_config.username,
                password=password,
                database=profile_config.database,
                connect_timeout=profile_config.connect_timeout_seconds,
                read_timeout=profile_config.read_timeout_seconds,
                charset="utf8mb4",
                cursorclass=dict_cursor,
                autocommit=True,
            )
        except Exception as exc:
            raise DatabaseAccessError(f"Failed to connect profile {profile_name!r}.") from exc

    def get_profile_config(self, profile: str | None = None) -> tuple[str, ProfileConfig]:
        """Return a supported MySQL/MariaDB profile configuration."""

        try:
            profile_name, profile_config = self.config_loader.load().get_profile(profile)
        except KeyError as exc:
            raise ConfigurationError(str(exc)) from exc
        if profile_config.driver not in {"mysql", "mariadb"}:
            raise ConfigurationError(
                f"Profile {profile_name!r} uses unsupported driver {profile_config.driver!r}."
            )
        return profile_name, profile_config


def _import_pymysql_driver() -> tuple[object, object]:
    import pymysql
    from pymysql.cursors import DictCursor

    return pymysql, DictCursor
