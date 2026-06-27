"""Command-line interface for db-lens-mcp."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

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
def help() -> None:
    """Show the common db-lens workflow."""

    typer.echo(
        "\n".join(
            [
                "db-lens common commands",
                "",
                "1. Check installation:",
                "   db-lens doctor",
                "",
                "2. Add a database profile:",
                "   db-lens config add",
                "",
                "3. Verify the profile:",
                "   db-lens config list",
                "   db-lens config test <profile>",
                "",
                "4. Connect an AI client:",
                "   db-lens mcp install-codex",
                "",
                "5. Print config instead of installing it:",
                "   db-lens mcp config",
                "   db-lens mcp config --client codex",
                "",
                "More help:",
                "   db-lens --help",
                "   db-lens config --help",
                "   db-lens mcp --help",
            ]
        )
    )


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
    typer.echo("Next: db-lens mcp install-codex")


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
    client: str = typer.Option("json", help="Output format: json or codex."),
    config_file: str = typer.Option(
        "",
        help="Optional DB_LENS_CONFIG_FILE value for clients that need an explicit path.",
    ),
) -> None:
    """Print a copy-paste MCP client configuration snippet."""

    command_value = command.strip() or _resolve_db_lens_command()
    client_value = client.strip().lower()
    if client_value == "codex":
        typer.echo(_codex_mcp_block(server_name, command_value, config_file.strip()))
        return
    if client_value != "json":
        raise typer.BadParameter("client must be json or codex.")
    server_config = {
        "command": command_value,
        "args": ["mcp", "run"],
    }
    if config_file.strip():
        server_config["env"] = {"DB_LENS_CONFIG_FILE": config_file.strip()}
    typer.echo(json.dumps({"mcpServers": {server_name: server_config}}, indent=2))


@mcp_app.command("install-codex")
def mcp_install_codex(
    server_name: str = typer.Option("db-lens", help="MCP server name in Codex."),
    command: str = typer.Option("", help="Command used by Codex. Defaults to db-lens."),
    codex_config: str = typer.Option(
        "",
        help="Codex config path. Defaults to ~/.codex/config.toml.",
    ),
    db_lens_config_file: str = typer.Option(
        "",
        help="Optional DB_LENS_CONFIG_FILE value to write into the Codex MCP server env.",
    ),
) -> None:
    """Install db-lens into Codex config.toml."""

    command_value = command.strip() or _resolve_db_lens_command()
    config_path = Path(codex_config).expanduser() if codex_config.strip() else _codex_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    if config_path.exists():
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        shutil.copy2(config_path, backup_path)
    updated = _install_toml_block(
        existing,
        server_name,
        _codex_mcp_block(server_name, command_value, db_lens_config_file.strip()),
    )
    config_path.write_text(updated, encoding="utf-8")
    typer.echo(f"Codex MCP config updated: {config_path}")
    if config_path.with_suffix(config_path.suffix + ".bak").exists():
        typer.echo(f"Backup: {config_path.with_suffix(config_path.suffix + '.bak')}")
    typer.echo("Restart Codex, then ask it to use db-lens.")


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

    resolved = shutil.which("db-lens")
    if resolved:
        return resolved
    invoked = Path(sys.argv[0]).expanduser()
    if invoked.is_absolute() and invoked.exists():
        return str(invoked)
    raise ConfigurationError(
        "db-lens executable was not found on PATH. Rerun this command using the full "
        "db-lens path printed by the installer, or pass --command /path/to/db-lens."
    )


def _codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def _codex_mcp_block(server_name: str, command: str, config_file: str = "") -> str:
    lines = [
        f"[mcp_servers.{server_name}]",
        f"command = {_toml_string(command)}",
        'args = ["mcp", "run"]',
    ]
    if config_file:
        lines.extend(
            [
                "",
                f"[mcp_servers.{server_name}.env]",
                f"DB_LENS_CONFIG_FILE = {_toml_string(config_file)}",
            ]
        )
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _install_toml_block(existing: str, server_name: str, block: str) -> str:
    table_names = {
        f"mcp_servers.{server_name}",
        f'mcp_servers."{server_name}"',
    }
    table_prefixes = {table + "." for table in table_names}
    kept_lines: list[str] = []
    skipping = False
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            table = stripped.strip("[]")
            skipping = table in table_names or any(
                table.startswith(prefix) for prefix in table_prefixes
            )
        if not skipping:
            kept_lines.append(line)
    content = "\n".join(kept_lines).rstrip()
    if content:
        return content + "\n\n" + block
    return block
