from pathlib import Path

from db_lens_mcp.infrastructure.config.config_loader import ConfigLoader
from db_lens_mcp.infrastructure.config.config_models import AppConfig, ProfileConfig


def test_config_loader_saves_and_loads_fixed_toml_shape(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    loader = ConfigLoader()
    config = AppConfig(
        profiles={
            "local-dev": ProfileConfig(
                driver="mysql",
                host="127.0.0.1",
                port=3306,
                databases=["app_db", "audit_db"],
                username="readonly",
                password="enc:v1:secret",
            )
        },
    )

    saved_path = loader.save(config, config_path)
    loaded = loader.load(saved_path)

    assert saved_path == config_path
    assert loaded.profiles["local-dev"].databases == ["app_db", "audit_db"]
    assert loaded.profiles["local-dev"].password == "enc:v1:secret"


def test_profile_public_dict_does_not_include_password() -> None:
    profile = ProfileConfig(
        databases=["app_db"],
        username="readonly",
        password="enc:v1:secret",
    )

    public = profile.public_dict()

    assert public["databases"] == ["app_db"]
    assert "password" not in public


def test_config_loader_migrates_deprecated_database_field(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[profiles.local-dev]",
                'driver = "mysql"',
                'host = "127.0.0.1"',
                "port = 3306",
                'database = "app_db"',
                'username = "readonly"',
                'password = "enc:v1:secret"',
            ]
        ),
        encoding="utf-8",
    )

    loaded = ConfigLoader().load(config_path)

    assert loaded.profiles["local-dev"].databases == ["app_db"]
