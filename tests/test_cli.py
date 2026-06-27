from typer.testing import CliRunner

from db_lens_mcp import __version__
from db_lens_mcp.cli.main import app


def test_version_command_prints_package_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_doctor_command_reports_skeleton_status() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "project skeleton is installed" in result.stdout
    assert "database: not checked" in result.stdout
