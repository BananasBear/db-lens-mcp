"""Command-line interface for db-lens-mcp."""

from __future__ import annotations

import json
import shutil

import typer

from db_lens_mcp import __version__
from db_lens_mcp.errors import ConfigurationError, DatabaseAccessError
from db_lens_mcp.infrastructure.config.config_loader import ConfigLoader, resolve_config_path
from db_lens_mcp.infrastructure.config.config_models import AppConfig, ProfileConfig
from db_lens_mcp.infrastructure.mysql.connection_factory import MySqlConnectionFactory
from db_lens_mcp.infrastructure.secrets.secret_store import SecretStore
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
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Configure shared CLI behavior."""

    configure_logging(verbose)


@app.command()
def version() -> None:
    """Print package version."""

    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Run local environment checks."""

    loader = ConfigLoader()
    secret_store = SecretStore()
    config_path = resolve_config_path()
    typer.echo("db-lens-mcp doctor")
    typer.echo(f"version: {__version__}")
    typer.echo("status: project skeleton is installed")
    typer.echo(f"config_file: {config_path}")
    typer.echo(f"config_exists: {loader.exists()}")
    typer.echo(f"key_source: {secret_store.key_source()}")
    typer.echo(f"key_available: {secret_store.key_available()}")
    if loader.exists() and secret_store.key_available():
        try:
            _test_database_connection(None)
        except (ConfigurationError, DatabaseAccessError, KeyError) as exc:
            typer.echo(f"database: failed: {exc}")
        else:
            typer.echo("database: ok")
    else:
        typer.echo("database: not checked")


@config_app.command("add")
def config_add(
    profile: str = typer.Option("", prompt="Profile name"),
    host: str = typer.Option("127.0.0.1", prompt="Host"),
    port: int = typer.Option(3306, prompt="Port"),
    database: str = typer.Option("", prompt="Database"),
    username: str = typer.Option("", prompt="Username"),
    password: str = typer.Option("", prompt="Password", hide_input=True),
    driver: str = typer.Option("mysql", help="Database driver. First phase supports mysql."),
    skip_test: bool = typer.Option(False, help="Save the profile without testing database access."),
) -> None:
    """Add or replace a database profile."""

    _require_value("profile", profile)
    _require_value("database", database)
    _require_value("username", username)
    _require_value("password", password)
    if driver not in {"mysql", "mariadb"}:
        raise typer.BadParameter("Only mysql and mariadb are supported in the first phase.")
    loader = ConfigLoader()
    secret_store = SecretStore()
    if loader.exists():
        config = loader.load()
    else:
        config = AppConfig()
    encrypted_password = secret_store.encrypt(password)
    config.profiles[profile] = ProfileConfig(
        driver=driver,
        host=host,
        port=port,
        database=database,
        username=username,
        password=encrypted_password,
    )
    if not config.default_profile:
        config.default_profile = profile
    config_path = loader.save(config)
    typer.echo(f"Saved profile {profile!r} to {config_path}")
    if skip_test:
        typer.echo("database: not checked")
        typer.echo("Next: db-lens config test " + profile)
        return
    try:
        _test_database_connection(profile)
    except (ConfigurationError, DatabaseAccessError) as exc:
        typer.echo(f"database: failed: {exc}")
        typer.echo(
            "Profile was saved. Fix the connection information and rerun: "
            "db-lens config test " + profile
        )
        raise typer.Exit(code=1) from exc
    typer.echo("database: ok")
    typer.echo("Next: db-lens mcp run")


@config_app.command("list")
def config_list() -> None:
    """List configured profiles without exposing secrets."""

    loader = ConfigLoader()
    try:
        config = loader.load()
    except ConfigurationError as exc:
        typer.echo(f"config_error: {exc}")
        raise typer.Exit(code=1) from exc
    if not config.profiles:
        typer.echo("No profiles configured.")
        return
    for name in sorted(config.profiles):
        profile = config.profiles[name]
        marker = "*" if name == config.default_profile else "-"
        public = profile.public_dict()
        typer.echo(
            f"{marker} {name}: {public['driver']}://{public['username']}@"
            f"{public['host']}:{public['port']}/{public['database']}"
        )


@config_app.command("test")
def config_test(profile: str) -> None:
    """Test a configured profile."""

    try:
        profile_name = _test_database_connection(profile)
    except (ConfigurationError, DatabaseAccessError, KeyError) as exc:
        typer.echo(f"config_test: failed: {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(f"config_test: ok: {profile_name}")
    typer.echo("database: ok")


@mcp_app.command("run")
def mcp_run() -> None:
    """Run the local MCP stdio server."""

    from db_lens_mcp.mcp.server import run_stdio_server

    run_stdio_server()


@mcp_app.command("config")
def mcp_config(
    server_name: str = typer.Option("db-lens", help="MCP server name in the client config."),
    command: str = typer.Option("", help="Command used by the MCP client. Defaults to db-lens."),
    config_file: str = typer.Option(
        "",
        help="Optional DB_LENS_CONFIG_FILE value for clients that need an explicit path.",
    ),
) -> None:
    """Print a copy-paste MCP client configuration snippet."""

    command_value = command.strip() or _resolve_db_lens_command()
    server_config = {
        "command": command_value,
        "args": ["mcp", "run"],
    }
    if config_file.strip():
        server_config["env"] = {"DB_LENS_CONFIG_FILE": config_file.strip()}
    typer.echo(json.dumps({"mcpServers": {server_name: server_config}}, indent=2))


def _require_value(name: str, value: str) -> None:
    if not value.strip():
        raise typer.BadParameter(f"{name} must not be empty.")


def _test_database_connection(profile: str | None) -> str:
    """Open and close a configured database connection without running SQL."""

    loader = ConfigLoader()
    secret_store = SecretStore()
    profile_name, _profile_config = loader.load().get_profile(profile)
    connection = MySqlConnectionFactory(
        config_loader=loader,
        secret_store=secret_store,
    ).create(profile_name)
    close = getattr(connection, "close", None)
    if callable(close):
        close()
    return profile_name


def _resolve_db_lens_command() -> str:
    """Return a command string that MCP clients can execute."""

    return shutil.which("db-lens") or "db-lens"
