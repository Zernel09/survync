"""Tests for configuration management."""

import tempfile
from pathlib import Path

from survync.config import DEFAULT_REMOTE_BASE_URL, LauncherConfig


def test_config_defaults():
    config = LauncherConfig()
    assert config.profile_name == "survival"
    assert config.remote_base_url == DEFAULT_REMOTE_BASE_URL
    assert config.remove_orphans is False
    assert "saves/" in config.preserve_paths


def test_config_save_and_load():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)

    config = LauncherConfig(
        remote_base_url="https://example.github.io/pack/",
        profile_name="survival",
        profile_path="/tmp/test_profile",
    )
    config.save(path)

    loaded = LauncherConfig.load(path)
    assert loaded.remote_base_url == "https://example.github.io/pack/"
    assert loaded.profile_name == "survival"
    assert loaded.profile_path == "/tmp/test_profile"


def test_config_validate_missing_url():
    config = LauncherConfig(remote_base_url="")
    errors = config.validate()
    assert any("remote_base_url" in e for e in errors)


def test_config_validate_missing_profile():
    config = LauncherConfig(remote_base_url="https://example.com")
    errors = config.validate()
    assert any("profile_path" in e for e in errors)


def test_config_validate_ok():
    with tempfile.TemporaryDirectory() as d:
        config = LauncherConfig(
            remote_base_url="https://example.com",
            profile_path=d,
        )
        errors = config.validate()
        assert not errors


def test_config_version_url():
    config = LauncherConfig(remote_base_url="https://example.github.io/pack")
    assert config.version_url == "https://example.github.io/pack/version.json"


def test_config_load_corrupt_file():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        f.write("NOT JSON")
        path = Path(f.name)

    config = LauncherConfig.load(path)
    assert config.profile_name == "survival"  # falls back to defaults
