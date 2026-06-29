from pathlib import Path

from cryptography.fernet import Fernet
from typer.testing import CliRunner

from db_lens_mcp.cli.main import app
from db_lens_mcp.infrastructure.config.config_loader import ConfigLoader
from db_lens_mcp.infrastructure.secrets.secret_store import SecretStore


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

    def create(self, profile, database=None):
        self.config_loader.load().get_profile(profile)
        connection = FakeConnection()
        self.connections.append(connection)
        return connection


class FakeTableLocatorService:
    def refresh_profile(self, profile):
        return {
            "profile": profile,
            "refreshed_at": "2026-06-29T10:00:00Z",
            "ttl_seconds": 604800,
            "databases": [
                {"name": "app_db", "table_count": 2},
                {"name": "audit_db", "table_count": 1},
            ],
        }


def test_config_add_list_and_test_use_encrypted_password(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)
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
    assert "- local-dev: mysql://readonly@127.0.0.1:3306/app_db" in list_result.stdout
    assert "db-password" not in list_result.stdout
    assert test_result.exit_code == 0
    assert "config_test: ok: local-dev" in test_result.stdout
    assert "database: ok" in test_result.stdout
    assert all(connection.closed for connection in FakeMySqlConnectionFactory.connections)


def test_config_add_interactive_prompts_for_language_and_uses_chinese_copy(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)
    FakeMySqlConnectionFactory.connections = []
    monkeypatch.setattr(
        "db_lens_mcp.cli.main.MySqlConnectionFactory",
        FakeMySqlConnectionFactory,
    )

    result = runner.invoke(
        app,
        ["config", "add"],
        input="zh\nlocal-dev\n\n\napp_db\nreadonly\ndb-password\n",
        env=env,
    )

    loader = ConfigLoader()
    secret_store = SecretStore()
    _, profile = loader.load().get_profile("local-dev")

    assert result.exit_code == 0
    assert "Choose language / 选择语言 (zh/en)" in result.stdout
    assert "请输入 profile 名称" in result.stdout
    assert "请输入 host" in result.stdout
    assert "请输入 port" in result.stdout
    assert "已保存 profile 'local-dev'" in result.stdout
    assert "database: 连接成功" in result.stdout
    assert "下一步：db-lens mcp install-codex" in result.stdout
    assert profile.host == "127.0.0.1"
    assert profile.port == 3306
    assert profile.databases == ["app_db"]
    assert profile.username == "readonly"
    assert secret_store.decrypt(profile.password) == "db-password"
    assert len(FakeMySqlConnectionFactory.connections) == 1
    assert all(connection.closed for connection in FakeMySqlConnectionFactory.connections)


def test_config_update_interactive_uses_defaults_and_keeps_password(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)
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
    update_result = runner.invoke(
        app,
        ["config", "update", "local-dev"],
        input="zh\n\n\n3307\napp_db_v2\nreadonly_v2\n\n",
        env=env,
    )

    loader = ConfigLoader()
    secret_store = SecretStore()
    _, profile = loader.load().get_profile("local-dev")

    assert add_result.exit_code == 0
    assert update_result.exit_code == 0
    assert "Choose language / 选择语言 (zh/en)" in update_result.stdout
    assert "请输入 driver" in update_result.stdout
    assert f"已在 {config_path} 中更新 profile 'local-dev'" in update_result.stdout
    assert "database: 连接成功" in update_result.stdout
    assert "下一步：db-lens mcp install-codex" in update_result.stdout
    assert profile.driver == "mysql"
    assert profile.host == "127.0.0.1"
    assert profile.port == 3307
    assert profile.databases == ["app_db_v2"]
    assert profile.username == "readonly_v2"
    assert secret_store.decrypt(profile.password) == "db-password"
    assert len(FakeMySqlConnectionFactory.connections) == 2
    assert all(connection.closed for connection in FakeMySqlConnectionFactory.connections)


def test_config_update_noninteractive_updates_selected_fields_and_can_skip_test(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)
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

    FakeMySqlConnectionFactory.connections = []
    update_result = runner.invoke(
        app,
        [
            "config",
            "update",
            "local-dev",
            "--host",
            "db.internal",
            "--language",
            "zh",
            "--skip-test",
        ],
        env=env,
    )

    loader = ConfigLoader()
    secret_store = SecretStore()
    _, profile = loader.load().get_profile("local-dev")

    assert add_result.exit_code == 0
    assert update_result.exit_code == 0
    assert f"已在 {config_path} 中更新 profile 'local-dev'" in update_result.stdout
    assert "database: 未检查" in update_result.stdout
    assert "下一步：db-lens config test local-dev" in update_result.stdout
    assert profile.host == "db.internal"
    assert profile.port == 3306
    assert profile.databases == ["app_db"]
    assert profile.username == "readonly"
    assert secret_store.decrypt(profile.password) == "db-password"
    assert FakeMySqlConnectionFactory.connections == []


def test_config_update_fails_for_missing_profile(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)
    monkeypatch.setattr(
        "db_lens_mcp.cli.main.MySqlConnectionFactory",
        FakeMySqlConnectionFactory,
    )

    runner.invoke(
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

    result = runner.invoke(
        app,
        ["config", "update", "missing", "--host", "db.internal"],
        env=env,
    )

    assert result.exit_code == 1
    assert "config_update: failed: Profile 'missing' does not exist." in result.stdout


def test_config_delete_removes_non_default_profile(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)

    first_add = runner.invoke(
        app,
        [
            "config",
            "add",
            "--profile",
            "alpha",
            "--host",
            "127.0.0.1",
            "--port",
            "3306",
            "--database",
            "app_alpha",
            "--username",
            "readonly_alpha",
            "--password",
            "alpha-password",
            "--skip-test",
        ],
        env=env,
    )
    second_add = runner.invoke(
        app,
        [
            "config",
            "add",
            "--profile",
            "beta",
            "--host",
            "127.0.0.2",
            "--port",
            "3307",
            "--database",
            "app_beta",
            "--username",
            "readonly_beta",
            "--password",
            "beta-password",
            "--skip-test",
        ],
        env=env,
    )
    delete_result = runner.invoke(
        app,
        ["config", "delete", "beta", "--yes", "--language", "zh"],
        env=env,
    )

    loader = ConfigLoader()
    config = loader.load()

    assert first_add.exit_code == 0
    assert second_add.exit_code == 0
    assert delete_result.exit_code == 0
    assert f"已从 {config_path} 删除 profile 'beta'" in delete_result.stdout
    assert "default_profile:" not in delete_result.stdout
    assert "下一步：db-lens config list" in delete_result.stdout
    assert sorted(config.profiles) == ["alpha"]
    assert not hasattr(config, "default_profile")


def test_config_delete_does_not_reassign_default_profile(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)

    runner.invoke(
        app,
        [
            "config",
            "add",
            "--profile",
            "beta",
            "--host",
            "127.0.0.2",
            "--port",
            "3307",
            "--database",
            "app_beta",
            "--username",
            "readonly_beta",
            "--password",
            "beta-password",
            "--skip-test",
        ],
        env=env,
    )
    runner.invoke(
        app,
        [
            "config",
            "add",
            "--profile",
            "alpha",
            "--host",
            "127.0.0.1",
            "--port",
            "3306",
            "--database",
            "app_alpha",
            "--username",
            "readonly_alpha",
            "--password",
            "alpha-password",
            "--skip-test",
        ],
        env=env,
    )

    delete_result = runner.invoke(
        app,
        ["config", "delete", "beta", "--yes"],
        env=env,
    )

    loader = ConfigLoader()
    config = loader.load()

    assert delete_result.exit_code == 0
    assert "Deleted profile 'beta'" in delete_result.stdout
    assert "default_profile:" not in delete_result.stdout
    assert sorted(config.profiles) == ["alpha"]
    assert not hasattr(config, "default_profile")


def test_config_delete_last_profile_leaves_no_default_profile(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)

    runner.invoke(
        app,
        [
            "config",
            "add",
            "--profile",
            "solo",
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
            "--skip-test",
        ],
        env=env,
    )

    delete_result = runner.invoke(
        app,
        ["config", "delete", "solo", "--yes"],
        env=env,
    )

    loader = ConfigLoader()
    config = loader.load()

    assert delete_result.exit_code == 0
    assert "Deleted profile 'solo'" in delete_result.stdout
    assert "default_profile:" not in delete_result.stdout
    assert "Next: db-lens config add" in delete_result.stdout
    assert config.profiles == {}
    assert not hasattr(config, "default_profile")


def test_config_delete_cancels_when_confirmation_is_rejected(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)

    runner.invoke(
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
            "--skip-test",
        ],
        env=env,
    )

    delete_result = runner.invoke(
        app,
        ["config", "delete", "local-dev"],
        input="zh\nn\n",
        env=env,
    )

    loader = ConfigLoader()
    config = loader.load()

    assert delete_result.exit_code == 0
    assert "Choose language / 选择语言 (zh/en)" in delete_result.stdout
    assert "将删除 profile 'local-dev'" in delete_result.stdout
    assert "确认删除 profile 'local-dev' 吗？" in delete_result.stdout
    assert "已取消删除。" in delete_result.stdout
    assert sorted(config.profiles) == ["local-dev"]
    assert not hasattr(config, "default_profile")


def test_config_delete_fails_for_missing_profile(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }
    monkeypatch.setenv("DB_LENS_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DB_LENS_MASTER_KEY", key)

    runner.invoke(
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
            "--skip-test",
        ],
        env=env,
    )

    delete_result = runner.invoke(
        app,
        ["config", "delete", "missing", "--yes"],
        env=env,
    )

    assert delete_result.exit_code == 1
    assert "config_delete: failed: Profile 'missing' does not exist." in delete_result.stdout


def test_config_test_fails_for_missing_profile(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    env = {"DB_LENS_CONFIG_FILE": str(config_path)}

    result = runner.invoke(app, ["config", "test", "missing"], env=env)

    assert result.exit_code == 1
    assert "Configuration file does not exist" in result.stdout


def test_cache_refresh_prints_profile_database_counts(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        "db_lens_mcp.cli.main._create_table_locator_service",
        lambda: FakeTableLocatorService(),
    )

    result = runner.invoke(app, ["cache", "refresh", "local-dev"])

    assert result.exit_code == 0
    assert "cache_refresh: ok: local-dev" in result.stdout
    assert "refreshed_at: 2026-06-29T10:00:00Z" in result.stdout
    assert "ttl_seconds: 604800" in result.stdout
    assert "- app_db: 2 tables" in result.stdout
    assert "- audit_db: 1 tables" in result.stdout


def test_doctor_reports_config_and_key_status(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
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
    key = Fernet.generate_key().decode("ascii")
    env = {
        "DB_LENS_CONFIG_FILE": str(config_path),
        "DB_LENS_MASTER_KEY": key,
    }

    result = runner.invoke(app, ["doctor"], env=env)

    assert result.exit_code == 0
    assert "config_exists: True" in result.stdout
    assert "database: failed:" in result.stdout
