from pathlib import Path

from cryptography.fernet import Fernet
from typer.testing import CliRunner

from db_lens_mcp.cli.main import app


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self):
        self.closed = True


class FakeMySqlConnectionFactory:
    connections = []

    def __init__(self, config_loader, secret_store) -> None:
        self.config_loader = config_loader
        self.secret_store = secret_store

    def create(self, profile):
        self.config_loader.load().get_profile(profile)
        connection = FakeConnection()
        self.connections.append(connection)
        return connection


def test_config_add_list_and_test_use_encrypted_password(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": Fernet.generate_key().decode("ascii"),
    }
    FakeMySqlConnectionFactory.connections = []
    monkeypatch.setattr(
        "db_lens_mcp.cli.main.MySqlConnectionFactory",
        FakeMySqlConnectionFactory,
    )

    add_result = runner.invoke(
        app,
        [
            "config",
            "add",
            "--profile",
            "local-dev",
            "--host",
            "127.0.0.1",
            "--port",
            "3306",
            "--database",
            "app_db",
            "--username",
            "readonly",
            "--password",
            "db-password",
        ],
        env=env,
    )
    list_result = runner.invoke(app, ["config", "list"], env=env)
    test_result = runner.invoke(app, ["config", "test", "local-dev"], env=env)

    assert add_result.exit_code == 0
    assert "Saved profile 'local-dev'" in add_result.stdout
    assert config_path.exists()
    assert "db-password" not in config_path.read_text(encoding="utf-8")
    assert "database: ok" in add_result.stdout
    assert "Next: db-lens mcp install-codex" in add_result.stdout
    assert list_result.exit_code == 0
    assert "* local-dev: mysql://readonly@127.0.0.1:3306/app_db" in list_result.stdout
    assert "db-password" not in list_result.stdout
    assert test_result.exit_code == 0
    assert "config_test: ok: local-dev" in test_result.stdout
    assert "database: ok" in test_result.stdout
    assert all(connection.closed for connection in FakeMySqlConnectionFactory.connections)


def test_config_test_fails_for_missing_profile(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    env = {"DB_LENS_CONFIG_FILE": str(config_path)}

    result = runner.invoke(app, ["config", "test", "missing"], env=env)

    assert result.exit_code == 1
    assert "Configuration file does not exist" in result.stdout


def test_doctor_reports_config_and_key_status(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": Fernet.generate_key().decode("ascii"),
    }

    result = runner.invoke(app, ["doctor"], env=env)

    assert result.exit_code == 0
    assert f"config_file: {config_path}" in result.stdout
    assert "config_exists: False" in result.stdout
    assert "key_source: DB_LENS_MASTER_KEY" in result.stdout
    assert "key_available: True" in result.stdout
    assert "database: not checked" in result.stdout


def test_doctor_reports_invalid_default_profile_without_crashing(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text('default_profile = "missing"\n', encoding="utf-8")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": Fernet.generate_key().decode("ascii"),
    }

    result = runner.invoke(app, ["doctor"], env=env)

    assert result.exit_code == 0
    assert "config_exists: True" in result.stdout
    assert "database: failed:" in result.stdout
