"""Auto-detection of local Modrinth profiles on Windows."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
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

    Tries the following in order:
        1. Exact folder name match.
        2. Case-insensitive exact match.
        3. Any folder whose name starts with profile_name (e.g. 'survival 1.0.0').
        4. Hard-coded fallbacks: 'NeoForge 1.21.1'.

    Returns:
        Path to the profile directory, or None if nothing matched
        (callers should then prompt the user to choose manually).
    """
    if profiles_dir is None:
        profiles_dir = get_modrinth_profiles_dir()
    if profiles_dir is None:
        return None

    # exact match
    profile_path = profiles_dir / profile_name
    if profile_path.is_dir():
        logger.info("Found profile '%s' at %s", profile_name, profile_path)
        return profile_path

    lower_name = profile_name.lower()
    prefix_match: Path | None = None
    for child in profiles_dir.iterdir():
        if not child.is_dir():
            continue
        child_lower = child.name.lower()
        # case-insensitive exact
        if child_lower == lower_name:
            logger.info("Found profile '%s' (case-insensitive) at %s", profile_name, child)
            return child
        # prefix match (e.g. "survival 1.0.0")
        if prefix_match is None and child_lower.startswith(lower_name):
            prefix_match = child

    if prefix_match is not None:
        logger.info("Found profile via prefix match at %s", prefix_match)
        return prefix_match

    # hard-coded loader-name fallbacks
    for fallback in ["NeoForge 1.21.1"]:
        fb_lower = fallback.lower()
        fb_exact = profiles_dir / fallback
        if fb_exact.is_dir():
            logger.info("Found fallback profile '%s' at %s", fallback, fb_exact)
            return fb_exact
        for child in profiles_dir.iterdir():
            if child.is_dir() and child.name.lower() == fb_lower:
                logger.info("Found fallback profile '%s' at %s", fallback, child)
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

    db_path: Path | None = None
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            db_path = Path(appdata) / "ModrinthApp" / "app.db"
    else:
        db_path = Path.home() / ".config" / "ModrinthApp" / "app.db"

    if db_path and db_path.is_file():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute(
                """
                SELECT name, game_version, mod_loader, mod_loader_version
                FROM profiles
                WHERE lower(path) = lower(?)
                """,
                (profile_path.name,),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                logger.info("Read profile metadata from Modrinth database")
                return {
                    "name": row[0],
                    "game_version": row[1],
                    "loader": row[2],
                    "loader_version": row[3],
                }
        except sqlite3.Error as exc:
            logger.warning("Failed to read Modrinth database metadata: %s", exc)

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
