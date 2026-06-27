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


def test_mcp_config_does_not_print_secrets() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["mcp", "config"])

    assert result.exit_code == 0
    lowered = result.stdout.lower()
    assert "password" not in lowered
    assert "master_key" not in lowered
    assert "mysql://" not in lowered
