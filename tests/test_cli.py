from typer.testing import CliRunner
import json

from db_lens_mcp import __version__
from db_lens_mcp.cli.main import app


def test_version_command_prints_package_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_doctor_command_reports_skeleton_status(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["doctor"],
        env={"DB_LENS_CONFIG_FILE": str(tmp_path / "missing.toml")},
    )

    assert result.exit_code == 0
    assert "project skeleton is installed" in result.stdout
    assert "database: not checked" in result.stdout


def test_help_command_prints_common_workflow() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["help"])

    assert result.exit_code == 0
    assert "db-lens common commands" in result.stdout
    assert "db-lens config add" in result.stdout
    assert "db-lens config update <profile>" in result.stdout
    assert "db-lens config delete <profile>" in result.stdout
    assert "db-lens mcp install-codex" in result.stdout


def test_mcp_config_prints_client_json() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "mcp",
            "config",
            "--server-name",
            "db-lens-local",
            "--command",
            "/usr/local/bin/db-lens",
            "--config-file",
            "/tmp/db-lens.toml",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    server = payload["mcpServers"]["db-lens-local"]
    assert server == {
        "command": "/usr/local/bin/db-lens",
        "args": ["mcp", "run"],
        "env": {"DB_LENS_CONFIG_FILE": "/tmp/db-lens.toml"},
    }


def test_mcp_config_prints_codex_toml() -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "mcp",
            "config",
            "--client",
            "codex",
            "--command",
            "/usr/local/bin/db-lens",
            "--config-file",
            "/tmp/db-lens.toml",
        ],
    )

    assert result.exit_code == 0
    assert '[mcp_servers.db-lens]' in result.stdout
    assert 'command = "/usr/local/bin/db-lens"' in result.stdout
    assert 'args = ["mcp", "run"]' in result.stdout
    assert '[mcp_servers.db-lens.env]' in result.stdout
    assert 'DB_LENS_CONFIG_FILE = "/tmp/db-lens.toml"' in result.stdout


def test_mcp_config_does_not_print_secrets() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["mcp", "config"])

    assert result.exit_code == 0
    lowered = result.stdout.lower()
    assert "password" not in lowered
    assert "master_key" not in lowered
    assert "mysql://" not in lowered


def test_mcp_install_codex_uses_invoked_absolute_command_when_path_is_missing(
    tmp_path, monkeypatch
) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    db_lens_bin = tmp_path / "db-lens"
    db_lens_bin.write_text("#!/bin/sh\n", encoding="utf-8")
    db_lens_bin.chmod(0o755)
    monkeypatch.setattr("db_lens_mcp.cli.main.shutil.which", lambda name: None)
    monkeypatch.setattr("db_lens_mcp.cli.main.sys.argv", [str(db_lens_bin)])

    result = runner.invoke(
        app,
        [
            "mcp",
            "install-codex",
            "--codex-config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0
    assert f'command = "{db_lens_bin}"' in config_path.read_text(encoding="utf-8")


def test_mcp_install_codex_writes_config_and_backup(tmp_path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text('model = "gpt-5.5"\n', encoding="utf-8")

    first = runner.invoke(
        app,
        [
            "mcp",
            "install-codex",
            "--codex-config",
            str(config_path),
            "--command",
            "/usr/local/bin/db-lens",
            "--db-lens-config-file",
            "/tmp/db-lens.toml",
        ],
    )
    second = runner.invoke(
        app,
        [
            "mcp",
            "install-codex",
            "--codex-config",
            str(config_path),
            "--command",
            "/opt/db-lens",
        ],
    )

    content = config_path.read_text(encoding="utf-8")
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "Codex MCP config updated" in first.stdout
    assert (tmp_path / "config.toml.bak").exists()
    assert 'model = "gpt-5.5"' in content
    assert content.count("[mcp_servers.db-lens]") == 1
    assert 'command = "/opt/db-lens"' in content
    assert "DB_LENS_CONFIG_FILE" not in content


def test_mcp_install_codex_replaces_quoted_existing_table(tmp_path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                'model = "gpt-5.5"',
                '[mcp_servers."db-lens"]',
                'command = "/old/db-lens"',
                'args = ["mcp", "run"]',
                '[mcp_servers."db-lens".env]',
                'DB_LENS_CONFIG_FILE = "/old/config.toml"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "mcp",
            "install-codex",
            "--codex-config",
            str(config_path),
            "--command",
            "/new/db-lens",
        ],
    )

    content = config_path.read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert "/old/db-lens" not in content
    assert "/old/config.toml" not in content
    assert content.count("[mcp_servers.db-lens]") == 1
    assert 'command = "/new/db-lens"' in content
