"""MySQL connection factory placeholder."""

from __future__ import annotations

from dataclasses import dataclass

from db_lens_mcp.errors import DatabaseAccessError


@dataclass(frozen=True)
class MySqlConnectionFactory:
    """Create MySQL connections.

    Real connection creation is intentionally deferred until configuration and
    secret loading exist.
    """

    def create(self, profile: str) -> object:
        """Create a database connection for a profile."""

        raise DatabaseAccessError(f"MySQL connection creation is not implemented for {profile!r}.")
