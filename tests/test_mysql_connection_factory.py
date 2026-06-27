import sys
import types

import pytest

from db_lens_mcp.errors import ConfigurationError, DatabaseAccessError
from db_lens_mcp.infrastructure.config.config_models import AppConfig, ProfileConfig
from db_lens_mcp.infrastructure.mysql.connection_factory import MySqlConnectionFactory


class FakeConfigLoader:
    def __init__(self, config):
        self.config = config

    def load(self):
        return self.config


class FakeSecretStore:
    def decrypt(self, value):
        assert value == "enc:v1:password"
        return "plain-password"


def test_connection_factory_builds_pymysql_connection(monkeypatch) -> None:
    calls = []
    pymysql_module = types.ModuleType("pymysql")
    cursors_module = types.ModuleType("pymysql.cursors")
    cursors_module.DictCursor = object

    def connect(**kwargs):
        calls.append(kwargs)
        return "connection"

    pymysql_module.connect = connect
    monkeypatch.setitem(sys.modules, "pymysql", pymysql_module)
    monkeypatch.setitem(sys.modules, "pymysql.cursors", cursors_module)
    config = AppConfig(
        default_profile="local-dev",
        profiles={
            "local-dev": ProfileConfig(
                driver="mysql",
                host="db.local",
                port=3307,
                database="app_db",
                username="readonly",
                password="enc:v1:password",
                connect_timeout_seconds=3,
                read_timeout_seconds=8,
            )
        },
    )
    factory = MySqlConnectionFactory(
        config_loader=FakeConfigLoader(config),
        secret_store=FakeSecretStore(),
        import_driver=lambda: (pymysql_module, object),
    )

    connection = factory.create("local-dev")

    assert connection == "connection"
    assert calls == [
        {
            "host": "db.local",
            "port": 3307,
            "user": "readonly",
            "password": "plain-password",
            "database": "app_db",
            "connect_timeout": 3,
            "read_timeout": 8,
            "charset": "utf8mb4",
            "cursorclass": object,
            "autocommit": True,
        }
    ]


def test_connection_factory_rejects_unsupported_driver() -> None:
    config = AppConfig(
        default_profile="local-dev",
        profiles={
            "local-dev": ProfileConfig(
                driver="postgres",
                database="app_db",
                username="readonly",
                password="enc:v1:password",
            )
        },
    )
    factory = MySqlConnectionFactory(
        config_loader=FakeConfigLoader(config),
        secret_store=FakeSecretStore(),
    )

    with pytest.raises(ConfigurationError, match="unsupported driver"):
        factory.create("local-dev")


def test_connection_factory_failure_message_does_not_expose_password(monkeypatch) -> None:
    pymysql_module = types.ModuleType("pymysql")
    cursors_module = types.ModuleType("pymysql.cursors")
    cursors_module.DictCursor = object

    def connect(**kwargs):
        raise RuntimeError(f"driver failure with password={kwargs['password']}")

    pymysql_module.connect = connect
    monkeypatch.setitem(sys.modules, "pymysql", pymysql_module)
    monkeypatch.setitem(sys.modules, "pymysql.cursors", cursors_module)
    config = AppConfig(
        default_profile="local-dev",
        profiles={
            "local-dev": ProfileConfig(
                driver="mysql",
                database="app_db",
                username="readonly",
                password="enc:v1:password",
            )
        },
    )
    factory = MySqlConnectionFactory(
        config_loader=FakeConfigLoader(config),
        secret_store=FakeSecretStore(),
        import_driver=lambda: (pymysql_module, object),
    )

    with pytest.raises(DatabaseAccessError) as exc_info:
        factory.create("local-dev")

    assert "plain-password" not in str(exc_info.value)
    assert "password" not in str(exc_info.value).lower()


def test_connection_factory_reports_missing_pymysql(monkeypatch) -> None:
    config = AppConfig(
        default_profile="local-dev",
        profiles={
            "local-dev": ProfileConfig(
                driver="mysql",
                database="app_db",
                username="readonly",
                password="enc:v1:password",
            )
        },
    )
    factory = MySqlConnectionFactory(
        config_loader=FakeConfigLoader(config),
        secret_store=FakeSecretStore(),
        import_driver=missing_driver,
    )

    with pytest.raises(DatabaseAccessError, match="PyMySQL is not installed"):
        factory.create("local-dev")


def missing_driver():
    raise ModuleNotFoundError("No module named 'pymysql'")
