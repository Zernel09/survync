"""Configuration management for Survync launcher."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Default preserved paths that should never be synced
DEFAULT_PRESERVE_PATHS = [
    "saves/",
    "screenshots/",
    "logs/",
    "crash-reports/",
    "options.txt",
    "optionsof.txt",
    "servers.dat",
    "realms_persistence.json",
    "usercache.json",
]

# Directories to scan for synced files
DEFAULT_SYNC_DIRS = [
    "mods/",
    "config/",
    "shaderpacks/",
    "resourcepacks/",
    "kubejs/",
    "defaultconfigs/",
    "scripts/",
    "global_packs/",
]

APP_NAME = "Survync"


def get_app_data_dir() -> Path:
    """Get the application data directory (platform-aware)."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_app_data_dir() / "config.json"


@dataclass
class LauncherConfig:
    """Launcher configuration stored locally."""

    # Remote server settings
    remote_base_url: str = ""

    # Profile settings
    profile_name: str = "survival"
    profile_path: str = ""

    # Optional Modrinth integration
    modrinth_project_slug: str | None = None
    modrinth_project_id: str | None = None

    # Sync settings
    preserve_paths: list[str] = field(default_factory=lambda: list(DEFAULT_PRESERVE_PATHS))
    remove_orphans: bool = False
    sync_dirs: list[str] = field(default_factory=lambda: list(DEFAULT_SYNC_DIRS))

    # UI settings
    check_updates_on_start: bool = True
    show_advanced_log: bool = False

    # Internal state
    last_known_version: str = ""
    last_sync_time: str = ""

    @classmethod
    def load(cls, path: Path | None = None) -> LauncherConfig:
        """Load config from disk, or return defaults."""
        config_path = path or get_config_path()
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("Loaded config from %s", config_path)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("Failed to parse config, using defaults: %s", exc)
        return cls()

    def save(self, path: Path | None = None) -> None:
        """Persist config to disk."""
        config_path = path or get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
        logger.info("Saved config to %s", config_path)

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: list[str] = []
        if not self.remote_base_url:
            errors.append("remote_base_url is not set")
        if not self.profile_path:
            errors.append("profile_path is not set (Modrinth profile not detected)")
        elif not Path(self.profile_path).is_dir():
            errors.append(f"profile_path does not exist: {self.profile_path}")
        return errors

    @property
    def version_url(self) -> str:
        """URL to version.json."""
        base = self.remote_base_url.rstrip("/")
        return f"{base}/version.json"

    @property
    def manifest_url(self) -> str:
        """URL to manifest.json."""
        base = self.remote_base_url.rstrip("/")
        return f"{base}/manifest.json"
