"""Local secret store for encrypted configuration values."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from db_lens_mcp.errors import ConfigurationError


DEFAULT_KEY_PATH = Path.home() / ".db-lens" / "master.key"
MASTER_KEY_ENV = "DB_LENS_MASTER_KEY"
ENCRYPTED_PREFIX = "enc:v1:"


class SecretStore:
    """Encrypt and decrypt local database passwords."""

    def __init__(self, key_path: Path | None = None) -> None:
        self.key_path = key_path or DEFAULT_KEY_PATH

    def encrypt(self, value: str) -> str:
        """Encrypt a secret value for storage in config.toml."""

        token = self._fernet(create=True).encrypt(value.encode("utf-8")).decode("ascii")
        return f"{ENCRYPTED_PREFIX}{token}"

    def decrypt(self, value: str) -> str:
        """Decrypt a config value.

        Plain values are rejected so the tool never silently accepts accidental
        cleartext passwords from config files.
        """

        if not value.startswith(ENCRYPTED_PREFIX):
            raise ConfigurationError("Secret value is not encrypted with enc:v1 prefix.")
        token = value[len(ENCRYPTED_PREFIX) :].encode("ascii")
        try:
            return self._fernet(create=False).decrypt(token).decode("utf-8")
        except InvalidToken as exc:
            raise ConfigurationError("Secret decryption failed. Check DB_LENS_MASTER_KEY.") from exc

    def key_available(self) -> bool:
        """Return whether a usable key source currently exists."""

        try:
            self._load_key(create=False)
            return True
        except ConfigurationError:
            return False

    def key_source(self) -> str:
        """Return a non-sensitive description of the key source."""

        if os.getenv(MASTER_KEY_ENV):
            return MASTER_KEY_ENV
        return str(self.key_path)

    def _fernet(self, create: bool) -> Fernet:
        try:
            return Fernet(self._load_key(create=create))
        except ValueError as exc:
            raise ConfigurationError("Master key is invalid. Check DB_LENS_MASTER_KEY.") from exc

    def _load_key(self, create: bool) -> bytes:
        env_key = os.getenv(MASTER_KEY_ENV)
        if env_key:
            return env_key.encode("ascii")
        if self.key_path.exists():
            return self.key_path.read_text(encoding="utf-8").strip().encode("ascii")
        if not create:
            raise ConfigurationError(f"Master key file does not exist: {self.key_path}")
        return self._create_key_file()

    def _create_key_file(self) -> bytes:
        key = Fernet.generate_key()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_text(key.decode("ascii") + "\n", encoding="utf-8")
        try:
            self.key_path.chmod(0o600)
        except PermissionError:
            pass
        return key
