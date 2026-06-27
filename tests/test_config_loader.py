from pathlib import Path

from db_lens_mcp.infrastructure.config.config_loader import ConfigLoader
from db_lens_mcp.infrastructure.config.config_models import AppConfig, ProfileConfig


def test_config_loader_saves_and_loads_fixed_toml_shape(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    loader = ConfigLoader()
    config = AppConfig(
        default_profile="local-dev",
        profiles={
            "local-dev": ProfileConfig(
                driver="mysql",
                host="127.0.0.1",
                port=3306,
                database="app_db",
                username="readonly",
                password="enc:v1:secret",
            )
        },
    )

    saved_path = loader.save(config, config_path)
    loaded = loader.load(saved_path)

    assert saved_path == config_path
    assert loaded.default_profile == "local-dev"
    assert loaded.profiles["local-dev"].database == "app_db"
    assert loaded.profiles["local-dev"].password == "enc:v1:secret"


def test_profile_public_dict_does_not_include_password() -> None:
    profile = ProfileConfig(
        database="app_db",
        username="readonly",
        password="enc:v1:secret",
    )

    public = profile.public_dict()

    assert public["database"] == "app_db"
    assert "password" not in public
