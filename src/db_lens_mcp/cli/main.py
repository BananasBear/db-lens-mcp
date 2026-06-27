"""Command-line interface for db-lens-mcp."""

from __future__ import annotations

import typer

from db_lens_mcp import __version__
from db_lens_mcp.logging import configure_logging

app = typer.Typer(
    name="db-lens",
    help="Database context MCP server for backend AI development.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Manage local database connection profiles.")
mcp_app = typer.Typer(help="Run MCP server entry points.")

app.add_typer(config_app, name="config")
app.add_typer(mcp_app, name="mcp")


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging.")) -> None:
    """Configure shared CLI behavior."""

    configure_logging(verbose)


@app.command()
def version() -> None:
    """Print package version."""

    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Run local environment checks."""

    typer.echo("db-lens-mcp doctor")
    typer.echo(f"version: {__version__}")
    typer.echo("status: project skeleton is installed")
    typer.echo("config: not implemented yet")
    typer.echo("database: not checked")


@config_app.command("add")
def config_add() -> None:
    """Add a database profile.

    The interactive implementation lands in the configuration phase.
    """

    typer.echo("config add is not implemented yet.")


@config_app.command("list")
def config_list() -> None:
    """List configured profiles without exposing secrets."""

    typer.echo("config list is not implemented yet.")


@config_app.command("test")
def config_test(profile: str) -> None:
    """Test a configured profile."""

    typer.echo(f"config test is not implemented yet for profile {profile!r}.")


@mcp_app.command("run")
def mcp_run() -> None:
    """Run the local MCP stdio server."""

    from db_lens_mcp.mcp.server import run_stdio_server

    run_stdio_server()
