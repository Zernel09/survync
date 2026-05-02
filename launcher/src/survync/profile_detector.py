"""Auto-detection of local Modrinth profiles on Windows."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def get_modrinth_profiles_dir() -> Path | None:
    """Find the Modrinth app profiles directory.

    Searches common locations on Windows.  Falls back to a check on
    Linux/macOS for development convenience.
    """
    candidates: list[Path] = []

    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            candidates.append(Path(appdata) / "com.modrinth.theseus" / "profiles")
            candidates.append(Path(appdata) / "ModrinthApp" / "profiles")
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates.append(Path(local) / "com.modrinth.theseus" / "profiles")
            candidates.append(Path(local) / "ModrinthApp" / "profiles")
        home = Path.home()
        candidates.append(home / "AppData" / "Roaming" / "com.modrinth.theseus" / "profiles")
    else:
        # Linux / macOS (dev convenience)
        home = Path.home()
        candidates.append(home / ".config" / "com.modrinth.theseus" / "profiles")
        candidates.append(home / ".local" / "share" / "com.modrinth.theseus" / "profiles")

    for candidate in candidates:
        if candidate.is_dir():
            logger.info("Found Modrinth profiles directory: %s", candidate)
            return candidate

    logger.warning("Could not auto-detect Modrinth profiles directory")
    return None


def find_profile(
    profile_name: str = "survival",
    profiles_dir: Path | None = None,
) -> Path | None:
    """Locate a specific Modrinth profile by name.

    Args:
        profile_name: The profile folder name to look for.
        profiles_dir: Override for the profiles root directory.

    Returns:
        Path to the profile directory, or None if not found.
    """
    if profiles_dir is None:
        profiles_dir = get_modrinth_profiles_dir()
    if profiles_dir is None:
        return None

    profile_path = profiles_dir / profile_name
    if profile_path.is_dir():
        logger.info("Found profile '%s' at %s", profile_name, profile_path)
        return profile_path

    # Try case-insensitive search
    for child in profiles_dir.iterdir():
        if child.is_dir() and child.name.lower() == profile_name.lower():
            logger.info("Found profile '%s' (case-insensitive) at %s", profile_name, child)
            return child

    logger.warning("Profile '%s' not found in %s", profile_name, profiles_dir)
    return None


def read_profile_metadata(profile_path: Path) -> dict:
    """Read Modrinth profile metadata (profile.json or similar).

    Returns whatever metadata is available, or an empty dict.
    """
    meta_files = ["profile.json", "instance.json", "modrinth.index.json"]
    for name in meta_files:
        meta_path = profile_path / name
        if meta_path.is_file():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("Read profile metadata from %s", meta_path)
                return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to read %s: %s", meta_path, exc)

    return {}


def validate_profile(profile_path: Path, expected_loader: str | None = None) -> list[str]:
    """Validate that a profile looks correct.

    Returns a list of warnings (empty = everything looks fine).
    """
    warnings: list[str] = []

    if not profile_path.is_dir():
        warnings.append(f"Profile directory does not exist: {profile_path}")
        return warnings

    mods_dir = profile_path / "mods"
    if not mods_dir.is_dir():
        warnings.append("No 'mods/' directory found in the profile")

    metadata = read_profile_metadata(profile_path)
    if not metadata:
        warnings.append("No profile metadata file found (profile.json / modrinth.index.json)")

    if expected_loader and metadata:
        profile_loader = metadata.get("loader", metadata.get("modloader", "")).lower()
        if profile_loader and profile_loader != expected_loader.lower():
            warnings.append(
                f"Loader mismatch: profile uses '{profile_loader}', "
                f"expected '{expected_loader}'"
            )

    return warnings
