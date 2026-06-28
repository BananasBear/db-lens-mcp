"""Command-line interface for db-lens-mcp."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import typer

from db_lens_mcp import __version__
from db_lens_mcp.cli.language import Language, message as cli_message, resolve_language
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
                "2. Add, update, or delete a database profile:",
                "   db-lens config add",
                "   db-lens config update <profile>",
                "   db-lens config delete <profile>",
                "",
                "3. Verify the profile:",
                "   db-lens config list",
                "   db-lens config test <profile>",
                "",
                "4. Connect an AI client:",
                "   db-lens mcp install-codex",
                "   db-lens mcp install-claude-code",
                "   db-lens mcp install-trae",
                "",
                "5. Print config snippets instead of installing:",
                "   db-lens mcp config",
                "   db-lens mcp config --client codex",
                "   db-lens mcp config --client claude-code",
                "   db-lens mcp config --client trae",
                "",
                "6. Generate a handoff message for other agents:",
                "   db-lens mcp handoff",
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
    profile: str | None = typer.Option(None, help="Profile name."),
    host: str | None = typer.Option(None, help="Database host."),
    port: int | None = typer.Option(None, help="Database port."),
    database: str | None = typer.Option(None, help="Database name."),
    username: str | None = typer.Option(None, help="Database username."),
    password: str | None = typer.Option(None, help="Database password.", hide_input=True),
    driver: str = typer.Option("mysql", help="Database driver. First phase supports mysql."),
    language: str | None = typer.Option(None, help="CLI language: zh or en."),
    skip_test: bool = typer.Option(False, help="Save the profile without testing database access."),
) -> None:
    """Add or replace a database profile."""

    interactive = any(
        value is None for value in (profile, host, port, database, username, password)
    )
    language_value = resolve_language(language, prompt_if_missing=interactive)
    _require_supported_driver(driver, language_value)

    if profile is None:
        profile = typer.prompt(cli_message(language_value, "profile_prompt"))
    if host is None:
        host = typer.prompt(cli_message(language_value, "host_prompt"), default="127.0.0.1")
    if port is None:
        port = typer.prompt(cli_message(language_value, "port_prompt"), default=3306, type=int)
    if database is None:
        database = typer.prompt(cli_message(language_value, "database_prompt"))
    if username is None:
        username = typer.prompt(cli_message(language_value, "username_prompt"))
    if password is None:
        password = typer.prompt(
            cli_message(language_value, "password_prompt"),
            hide_input=True,
        )

    _require_value("profile", profile, language_value)
    _require_value("database", database, language_value)
    _require_value("username", username, language_value)
    _require_value("password", password, language_value)
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
    typer.echo(cli_message(language_value, "saved_profile", profile=profile, path=config_path))
    if skip_test:
        typer.echo(cli_message(language_value, "database_not_checked"))
        typer.echo(
            cli_message(
                language_value,
                "next_step",
                command="db-lens config test " + profile,
            )
        )
        return
    try:
        _test_database_connection(profile)
    except (ConfigurationError, DatabaseAccessError) as exc:
        typer.echo(cli_message(language_value, "database_failed", error=exc))
        typer.echo(
            cli_message(
                language_value,
                "profile_saved_rerun",
                command="db-lens config test " + profile,
            )
        )
        raise typer.Exit(code=1) from exc
    typer.echo(cli_message(language_value, "database_ok"))
    typer.echo(
        cli_message(
            language_value,
            "next_step",
            command="db-lens mcp install-codex",
        )
    )


@config_app.command("update")
def config_update(
    profile: str,
    driver: str | None = typer.Option(
        None,
        help="Database driver. First phase supports mysql.",
    ),
    host: str | None = typer.Option(None, help="Database host."),
    port: int | None = typer.Option(None, help="Database port."),
    database: str | None = typer.Option(None, help="Database name."),
    username: str | None = typer.Option(None, help="Database username."),
    password: str | None = typer.Option(
        None,
        help="New database password. Leave unset to keep the current password.",
        hide_input=True,
    ),
    language: str | None = typer.Option(None, help="CLI language: zh or en."),
    skip_test: bool = typer.Option(False, help="Save the profile without testing database access."),
) -> None:
    """Update an existing database profile."""

    interactive = all(
        value is None for value in (driver, host, port, database, username, password)
    )
    language_value = resolve_language(language, prompt_if_missing=interactive)
    loader = ConfigLoader()
    secret_store = SecretStore()
    try:
        config = loader.load()
        _profile_name, current_profile = config.get_profile(profile)
    except ConfigurationError as exc:
        typer.echo(cli_message(language_value, "config_update_failed", error=exc))
        raise typer.Exit(code=1) from exc
    except KeyError as exc:
        message = exc.args[0] if exc.args else str(exc)
        typer.echo(cli_message(language_value, "config_update_failed", error=message))
        raise typer.Exit(code=1) from exc

    if interactive:
        driver = typer.prompt(
            cli_message(language_value, "driver_prompt"),
            default=current_profile.driver,
        )
        host = typer.prompt(
            cli_message(language_value, "host_prompt"),
            default=current_profile.host,
        )
        port = typer.prompt(
            cli_message(language_value, "port_prompt"),
            default=current_profile.port,
            type=int,
        )
        database = typer.prompt(
            cli_message(language_value, "database_prompt"),
            default=current_profile.database,
        )
        username = typer.prompt(
            cli_message(language_value, "username_prompt"),
            default=current_profile.username,
        )
        password = typer.prompt(
            cli_message(language_value, "password_keep_prompt"),
            default="",
            hide_input=True,
            show_default=False,
        )

    driver_value = driver if driver is not None else current_profile.driver
    host_value = host if host is not None else current_profile.host
    port_value = port if port is not None else current_profile.port
    database_value = database if database is not None else current_profile.database
    username_value = username if username is not None else current_profile.username

    _require_supported_driver(driver_value, language_value)
    _require_value("host", host_value, language_value)
    _require_value("database", database_value, language_value)
    _require_value("username", username_value, language_value)

    password_value = current_profile.password
    if password is not None and password.strip():
        password_value = secret_store.encrypt(password)

    config.profiles[profile] = ProfileConfig(
        driver=driver_value,
        host=host_value,
        port=port_value,
        database=database_value,
        username=username_value,
        password=password_value,
        connect_timeout_seconds=current_profile.connect_timeout_seconds,
        read_timeout_seconds=current_profile.read_timeout_seconds,
    )
    config_path = loader.save(config)
    typer.echo(cli_message(language_value, "updated_profile", profile=profile, path=config_path))
    if skip_test:
        typer.echo(cli_message(language_value, "database_not_checked"))
        typer.echo(
            cli_message(
                language_value,
                "next_step",
                command="db-lens config test " + profile,
            )
        )
        return
    try:
        _test_database_connection(profile)
    except (ConfigurationError, DatabaseAccessError) as exc:
        typer.echo(cli_message(language_value, "database_failed", error=exc))
        typer.echo(
            cli_message(
                language_value,
                "profile_updated_rerun",
                command="db-lens config test " + profile,
            )
        )
        raise typer.Exit(code=1) from exc
    typer.echo(cli_message(language_value, "database_ok"))
    typer.echo(
        cli_message(
            language_value,
            "next_step",
            command="db-lens mcp install-codex",
        )
    )


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


@config_app.command("delete")
def config_delete(
    profile: str,
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Delete without asking for confirmation.",
    ),
    language: str | None = typer.Option(None, help="CLI language: zh or en."),
) -> None:
    """Delete an existing database profile."""

    language_value = resolve_language(language, prompt_if_missing=not yes)
    loader = ConfigLoader()
    try:
        config = loader.load()
        _profile_name, current_profile = config.get_profile(profile)
    except ConfigurationError as exc:
        typer.echo(cli_message(language_value, "config_delete_failed", error=exc))
        raise typer.Exit(code=1) from exc
    except KeyError as exc:
        message = exc.args[0] if exc.args else str(exc)
        typer.echo(cli_message(language_value, "config_delete_failed", error=message))
        raise typer.Exit(code=1) from exc

    public = current_profile.public_dict()
    typer.echo(
        cli_message(
            language_value,
            "deleted_profile_summary",
            profile=profile,
            driver=public["driver"],
            username=public["username"],
            host=public["host"],
            port=public["port"],
            database=public["database"],
        )
    )
    if not yes and not typer.confirm(
        cli_message(language_value, "delete_confirm", profile=profile),
        default=False,
    ):
        typer.echo(cli_message(language_value, "delete_cancelled"))
        return

    del config.profiles[profile]
    default_message = ""
    if config.default_profile == profile:
        remaining_profiles = sorted(config.profiles)
        config.default_profile = remaining_profiles[0] if remaining_profiles else None
        if config.default_profile:
            default_message = cli_message(
                language_value,
                "default_profile_set",
                profile=config.default_profile,
            )
        else:
            default_message = cli_message(language_value, "default_profile_cleared")

    config_path = loader.save(config)
    typer.echo(cli_message(language_value, "deleted_profile", profile=profile, path=config_path))
    if default_message:
        typer.echo(default_message)
    if config.profiles:
        typer.echo(
            cli_message(
                language_value,
                "next_step",
                command="db-lens config list",
            )
        )
    else:
        typer.echo(
            cli_message(
                language_value,
                "next_step",
                command="db-lens config add",
            )
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
    client: str = typer.Option(
        "json",
        help="Output format: json, codex, claude-code, or trae.",
    ),
    config_file: str = typer.Option(
        "",
        help="Optional DB_LENS_CONFIG_FILE value for clients that need an explicit path.",
    ),
) -> None:
    """Print a copy-paste MCP client configuration snippet."""

    command_value = command.strip() or _resolve_db_lens_command()
    client_value = client.strip().lower()
    config_file_value = config_file.strip()
    if client_value == "codex":
        typer.echo(_codex_mcp_block(server_name, command_value, config_file_value))
        return
    if client_value == "claude-code":
        typer.echo(
            json.dumps(
                {
                    "mcpServers": {
                        server_name: _claude_code_server_definition(
                            command_value,
                            config_file_value,
                        )
                    }
                },
                indent=2,
            )
        )
        return
    if client_value == "trae":
        typer.echo(
            json.dumps(
                _trae_mcp_file(server_name, command_value, config_file_value),
                indent=2,
            )
        )
        return
    if client_value != "json":
        raise typer.BadParameter("client must be json, codex, claude-code, or trae.")
    typer.echo(
        json.dumps(
            {
                "mcpServers": {
                    server_name: _base_server_config(command_value, config_file_value)
                }
            },
            indent=2,
        )
    )


@mcp_app.command("handoff")
def mcp_handoff(
    server_name: str = typer.Option("db-lens", help="MCP server name in the handoff message."),
    command: str = typer.Option("", help="Command used by the MCP client. Defaults to db-lens."),
    config_file: str = typer.Option(
        "",
        help="Optional DB_LENS_CONFIG_FILE value for clients that need an explicit path.",
    ),
) -> None:
    """Print a generic MCP installation message for other agents."""

    command_value = command.strip() or _resolve_db_lens_command()
    typer.echo(_handoff_message(server_name, command_value, config_file.strip()))


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
    config_file_value = db_lens_config_file.strip()
    config_path = Path(codex_config).expanduser() if codex_config.strip() else _codex_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    if config_path.exists():
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        shutil.copy2(config_path, backup_path)
    updated = _install_toml_block(
        existing,
        server_name,
        _codex_mcp_block(server_name, command_value, config_file_value),
    )
    config_path.write_text(updated, encoding="utf-8")
    typer.echo(f"Codex MCP config updated: {config_path}")
    if config_path.with_suffix(config_path.suffix + ".bak").exists():
        typer.echo(f"Backup: {config_path.with_suffix(config_path.suffix + '.bak')}")
    typer.echo("Restart Codex, then ask it to use db-lens.")


@mcp_app.command("install-claude-code")
def mcp_install_claude_code(
    server_name: str = typer.Option("db-lens", help="MCP server name in Claude Code."),
    command: str = typer.Option("", help="Command used by Claude Code. Defaults to db-lens."),
    scope: str = typer.Option(
        "user",
        help="Claude Code MCP scope: local, user, or project.",
    ),
    claude_command: str = typer.Option(
        "",
        help="Path to the Claude Code CLI. Defaults to `claude` on PATH.",
    ),
    db_lens_config_file: str = typer.Option(
        "",
        help="Optional DB_LENS_CONFIG_FILE value to write into the Claude Code MCP server env.",
    ),
) -> None:
    """Install db-lens into Claude Code."""

    command_value = command.strip() or _resolve_db_lens_command()
    scope_value = _validate_claude_scope(scope)
    claude_cli = _resolve_claude_command(claude_command)
    payload = json.dumps(
        _claude_code_server_definition(command_value, db_lens_config_file.strip())
    )
    result = _run_external_command(
        [
            claude_cli,
            "mcp",
            "add-json",
            "--scope",
            scope_value,
            server_name,
            payload,
        ],
        client_name="Claude Code",
    )
    _echo_command_output(result, fallback_message="Claude Code MCP config updated.")
    typer.echo("Restart Claude Code if it is already running.")


@mcp_app.command("install-trae")
def mcp_install_trae(
    server_name: str = typer.Option("db-lens", help="MCP server name in Trae."),
    command: str = typer.Option("", help="Command used by Trae. Defaults to db-lens."),
    trae_command: str = typer.Option(
        "",
        help="Path to the Trae CLI. Defaults to `trae` on PATH or the standard macOS app path.",
    ),
    db_lens_config_file: str = typer.Option(
        "",
        help="Optional DB_LENS_CONFIG_FILE value to write into the Trae MCP server env.",
    ),
) -> None:
    """Install db-lens into Trae."""

    command_value = command.strip() or _resolve_db_lens_command()
    trae_cli = _resolve_trae_command(trae_command)
    payload = json.dumps(
        _trae_server_definition(server_name, command_value, db_lens_config_file.strip())
    )
    result = _run_external_command(
        [
            trae_cli,
            "--add-mcp",
            payload,
        ],
        client_name="Trae",
    )
    _echo_command_output(result, fallback_message="Trae MCP config updated.")
    typer.echo("Restart Trae if it is already running.")


def _require_value(name: str, value: str, language: Language = "en") -> None:
    if not value.strip():
        raise typer.BadParameter(cli_message(language, "empty_value", name=name))


def _require_supported_driver(driver: str, language: Language = "en") -> None:
    if driver not in {"mysql", "mariadb"}:
        raise typer.BadParameter(cli_message(language, "unsupported_driver"))


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


def _resolve_claude_command(explicit_command: str = "") -> str:
    if explicit_command.strip():
        return explicit_command.strip()
    resolved = shutil.which("claude")
    if resolved:
        return resolved
    raise ConfigurationError(
        "Claude Code CLI was not found on PATH. Install Claude Code, or pass "
        "--claude-command /path/to/claude."
    )


def _resolve_trae_command(explicit_command: str = "") -> str:
    if explicit_command.strip():
        return explicit_command.strip()
    resolved = shutil.which("trae")
    if resolved:
        return resolved
    for candidate in _candidate_trae_commands():
        if candidate.exists():
            return str(candidate)
    raise ConfigurationError(
        "Trae CLI was not found on PATH. Install Trae, or pass "
        "--trae-command /path/to/trae."
    )


def _candidate_trae_commands() -> list[Path]:
    app_roots = [Path("/Applications"), Path.home() / "Applications"]
    app_names = ["Trae.app", "Trae CN.app", "TRAE SOLO.app"]
    return [
        app_root / app_name / "Contents" / "Resources" / "app" / "bin" / "trae"
        for app_root in app_roots
        for app_name in app_names
    ]


def _validate_claude_scope(scope: str) -> str:
    scope_value = scope.strip().lower()
    if scope_value not in {"local", "user", "project"}:
        raise typer.BadParameter("scope must be local, user, or project.")
    return scope_value


def _codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def _base_server_config(command: str, config_file: str = "") -> dict[str, object]:
    server_config: dict[str, object] = {
        "command": command,
        "args": ["mcp", "run"],
    }
    if config_file:
        server_config["env"] = {"DB_LENS_CONFIG_FILE": config_file}
    return server_config


def _claude_code_server_definition(command: str, config_file: str = "") -> dict[str, object]:
    server_config = {"type": "stdio"}
    server_config.update(_base_server_config(command, config_file))
    return server_config


def _trae_server_definition(
    server_name: str,
    command: str,
    config_file: str = "",
) -> dict[str, object]:
    server_config = {"name": server_name}
    server_config.update(_base_server_config(command, config_file))
    return server_config


def _trae_mcp_file(server_name: str, command: str, config_file: str = "") -> dict[str, object]:
    return {
        "servers": {
            server_name: _base_server_config(command, config_file),
        },
        "inputs": [],
    }


def _handoff_message(server_name: str, command: str, config_file: str = "") -> str:
    payload = {
        "mcpServers": {
            server_name: _base_server_config(command, config_file),
        }
    }
    config_json = json.dumps(payload, indent=2, ensure_ascii=False)
    return "\n".join(
        [
            "请把下面这个 MCP server 配置到你当前使用的 MCP 客户端中，并完成安装。",
            "",
            "要求：",
            f"- server 名称保持为 {server_name}",
            "- 使用下面的 command、args 和 env",
            "- 不要修改配置中的字段名",
            "- 如果你的客户端不支持自动安装，请把下面的 JSON 配置粘贴到对应的 MCP 配置位置",
            "- 安装完成后，确认你已经能看到 db-lens 提供的 MCP tools",
            "",
            "配置：",
            config_json,
        ]
    )


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


def _run_external_command(
    command: list[str],
    *,
    client_name: str,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ConfigurationError(
            f"{client_name} CLI was not found. Install {client_name}, or pass its explicit CLI path."
        ) from exc
    except subprocess.CalledProcessError as exc:
        output = (exc.stderr or exc.stdout).strip()
        if not output:
            output = str(exc)
        raise ConfigurationError(f"{client_name} MCP install failed: {output}") from exc


def _echo_command_output(
    result: subprocess.CompletedProcess[str],
    *,
    fallback_message: str,
) -> None:
    stdout = result.stdout.strip()
    if stdout:
        typer.echo(stdout)
        return
    typer.echo(fallback_message)
