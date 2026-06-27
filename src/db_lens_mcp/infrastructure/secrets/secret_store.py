"""Secret store placeholder."""

from __future__ import annotations

from db_lens_mcp.errors import ConfigurationError


class SecretStore:
    """Encrypt and decrypt local database passwords."""

    def encrypt(self, value: str) -> str:
        raise ConfigurationError("Secret encryption is not implemented yet.")

    def decrypt(self, value: str) -> str:
        raise ConfigurationError("Secret decryption is not implemented yet.")
