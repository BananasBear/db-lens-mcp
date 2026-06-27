from pathlib import Path

import pytest

from db_lens_mcp.errors import ConfigurationError
from db_lens_mcp.infrastructure.secrets.secret_store import ENCRYPTED_PREFIX, SecretStore


def test_secret_store_encrypts_and_decrypts_with_local_key(tmp_path: Path) -> None:
    key_path = tmp_path / "master.key"
    store = SecretStore(key_path=key_path)

    encrypted = store.encrypt("db-password")
    decrypted = store.decrypt(encrypted)

    assert encrypted.startswith(ENCRYPTED_PREFIX)
    assert encrypted != "db-password"
    assert decrypted == "db-password"
    assert key_path.exists()


def test_secret_store_rejects_plaintext_value(tmp_path: Path) -> None:
    store = SecretStore(key_path=tmp_path / "master.key")

    with pytest.raises(ConfigurationError, match="not encrypted"):
        store.decrypt("plain-password")


def test_key_available_does_not_create_key_file(tmp_path: Path) -> None:
    key_path = tmp_path / "master.key"
    store = SecretStore(key_path=key_path)

    assert store.key_available() is False
    assert not key_path.exists()
