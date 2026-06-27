"""Project-level exceptions.

The first phase only defines stable exception types so later modules can share
clear failure semantics without coupling to Typer, MCP, or database drivers.
"""


class DbLensError(Exception):
    """Base exception for expected db-lens-mcp failures."""


class ConfigurationError(DbLensError):
    """Raised when local configuration is missing, invalid, or undecryptable."""


class SafetyError(DbLensError):
    """Raised when SQL or tool input violates the safety boundary."""


class DatabaseAccessError(DbLensError):
    """Raised when a database operation fails after passing local validation."""
