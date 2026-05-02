#!/usr/bin/env python3
"""Generate version.json and manifest.json from a local Modrinth profile.

Usage:
    python generate_manifest.py --profile-dir /path/to/modrinth/profiles/survival
    python generate_manifest.py --profile-dir /path/to/profile --output-dir ../site
    python generate_manifest.py --profile-dir /path/to/profile --dry-run

This script scans the local Modrinth profile directory, computes hashes for
all managed files, and generates the static JSON files that Survync serves
via GitHub Pages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Directories to include in the manifest
DEFAULT_INCLUDE_DIRS = [
    "mods",
    "config",
    "shaderpacks",
    "resourcepacks",
    "kubejs",
    "defaultconfigs",
    "scripts",
    "global_packs",
]

# Paths to exclude (never include these in the manifest)
DEFAULT_EXCLUDE_PATTERNS = [
    "saves/",
    "screenshots/",
    "logs/",
    "crash-reports/",
    "options.txt",
    "optionsof.txt",
    "servers.dat",
    "realms_persistence.json",
    "usercache.json",
    ".fabric/",
    ".mixin.out/",
    "__pycache__/",
    "*.log",
    "*.tmp",
    ".DS_Store",
    "Thumbs.db",
]

BUFFER_SIZE = 65536


def sha256_file(filepath: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def should_exclude(rel_path: str, exclude_patterns: list[str]) -> bool:
    """Check if a relative path matches any exclusion pattern."""
    import fnmatch

    for pattern in exclude_patterns:
        if pattern.endswith("/") and rel_path.startswith(pattern):
            return True
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
            return True
    return False


def scan_profile(
    profile_dir: Path,
    include_dirs: list[str],
    exclude_patterns: list[str],
    base_download_url: str,
) -> list[dict]:
    """Scan the profile directory and build a file list."""
    files: list[dict] = []

    for dir_name in include_dirs:
        scan_dir = profile_dir / dir_name
        if not scan_dir.is_dir():
            continue

        for filepath in sorted(scan_dir.rglob("*")):
            if not filepath.is_file():
                continue

            rel_path = str(filepath.relative_to(profile_dir)).replace("\\", "/")

            if should_exclude(rel_path, exclude_patterns):
                continue

            file_hash = sha256_file(filepath)
            file_size = filepath.stat().st_size

            entry = {
                "relative_path": rel_path,
                "file_name": filepath.name,
                "sha256": file_hash,
                "size": file_size,
                "source_type": "direct",
                "download_url": f"{base_download_url.rstrip('/')}/files/{rel_path}",
            }
            files.append(entry)

    # Also scan for top-level files that should be synced
    for item in sorted(profile_dir.iterdir()):
        if not item.is_file():
            continue
        rel_path = item.name
        if should_exclude(rel_path, exclude_patterns):
            continue
        # Only include specific top-level files
        if rel_path in ("modrinth.index.json", "profile.json"):
            continue
        # Skip unless it's a recognized config-type file
        if item.suffix in (".json", ".toml", ".yml", ".yaml", ".cfg", ".properties"):
            file_hash = sha256_file(item)
            entry = {
                "relative_path": rel_path,
                "file_name": item.name,
                "sha256": file_hash,
                "size": item.stat().st_size,
                "source_type": "direct",
                "download_url": f"{base_download_url.rstrip('/')}/files/{rel_path}",
            }
            files.append(entry)

    return files


def read_profile_metadata(profile_dir: Path) -> dict[str, Any]:
    """Try to read metadata from the profile or Modrinth database."""
    # 1. Try local files first (profile.json, modrinth.index.json)
    for name in ("profile.json", "modrinth.index.json"):
        meta_path = profile_dir / name
        if meta_path.is_file():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue

    # 2. Try Modrinth App database
    profile_id = profile_dir.name
    db_path = None
    if sys.platform == "win32":
        db_path = Path(os.environ.get("APPDATA", "")) / "ModrinthApp" / "app.db"
    elif sys.platform == "darwin":
        db_path = Path.home() / "Library" / "Application Support" / "ModrinthApp" / "app.db"
    else:
        # Linux
        db_path = Path.home() / ".config" / "ModrinthApp" / "app.db"

    if db_path and db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            # Modrinth stores the profile folder in the path column. Some
            # installs preserve a different casing than the actual folder, so
            # match case-insensitively.
            cur.execute(
                """
                SELECT name, game_version, mod_loader, mod_loader_version
                FROM profiles
                WHERE lower(path) = lower(?)
                """,
                (profile_id,),
            )
            row = cur.fetchone()
            conn.close()

            if row:
                return {
                    "name": row[0],
                    "game_version": row[1],
                    "loader": row[2],
                    "loader_version": row[3],
                }
        except Exception as e:
            print(f"Warning: Could not read Modrinth database: {e}")

    return {}


def generate(
    profile_dir: Path,
    output_dir: Path,
    pack_name: str = "survival",
    pack_version: str = "1.0.0",
    minecraft_version: str = "1.20.4",
    loader_name: str = "fabric",
    loader_version: str = "0.15.0",
    base_download_url: str = "",
    include_dirs: Optional[list[str]] = None,
    exclude_patterns: Optional[list[str]] = None,
    dry_run: bool = False,
) -> tuple[dict, dict]:
    """Generate version.json and manifest.json.

    Returns:
        Tuple of (version_data, manifest_data).
    """
    if include_dirs is None:
        include_dirs = list(DEFAULT_INCLUDE_DIRS)
    if exclude_patterns is None:
        exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS)

    now = datetime.now(timezone.utc).isoformat()
    manifest_url = (
        f"{base_download_url.rstrip('/')}/manifest.json" if base_download_url else ""
    )

    print(f"Scanning profile: {profile_dir}")
    print(f"Include dirs: {include_dirs}")
    print(f"Pack: {pack_name} v{pack_version}")
    print(f"Minecraft: {minecraft_version}, Loader: {loader_name} {loader_version}")

    files = scan_profile(profile_dir, include_dirs, exclude_patterns, base_download_url)
    print(f"Found {len(files)} files to include in manifest")

    version_data = {
        "pack_name": pack_name,
        "pack_version": pack_version,
        "minecraft_version": minecraft_version,
        "loader_name": loader_name,
        "loader_version": loader_version,
        "generated_at": now,
        "manifest_url": manifest_url,
        "minimum_launcher_version": "0.1.0",
        "release_notes": "",
    }

    manifest_data = {
        "pack_name": pack_name,
        "pack_version": pack_version,
        "minecraft_version": minecraft_version,
        "loader_name": loader_name,
        "loader_version": loader_version,
        "files": files,
        "preserve_paths": [
            "saves/",
            "screenshots/",
            "logs/",
            "crash-reports/",
            "options.txt",
            "optionsof.txt",
            "servers.dat",
        ],
    }

    if dry_run:
        print("\n--- DRY RUN ---")
        print("\nversion.json:")
        print(json.dumps(version_data, indent=2))
        print(f"\nmanifest.json: ({len(files)} files)")
        for f in files:
            print(f"  {f['relative_path']} ({f['size']} bytes) [{f['sha256'][:12]}...]")
        return version_data, manifest_data

    output_dir.mkdir(parents=True, exist_ok=True)

    version_path = output_dir / "version.json"
    with open(version_path, "w", encoding="utf-8") as f:
        json.dump(version_data, f, indent=2)
    print(f"\nWrote: {version_path}")

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"Wrote: {manifest_path}")

    return version_data, manifest_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Survync manifest from a local Modrinth profile."
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        required=True,
        help="Path to the local Modrinth profile directory (e.g., .../profiles/survival)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "site",
        help="Output directory for generated JSON files (default: ../site)",
    )
    parser.add_argument(
        "--pack-name",
        default="survival",
        help="Pack display name (default: survival)",
    )
    parser.add_argument(
        "--pack-version",
        default="1.0.0",
        help="Pack version string (default: 1.0.0)",
    )
    parser.add_argument(
        "--minecraft-version",
        default=None,
        help="Minecraft version (overrides profile metadata)",
    )
    parser.add_argument(
        "--loader-name",
        default=None,
        help="Mod loader name (overrides profile metadata)",
    )
    parser.add_argument(
        "--loader-version",
        default=None,
        help="Mod loader version (overrides profile metadata)",
    )
    parser.add_argument(
        "--base-download-url",
        default="",
        help="Base URL for file downloads (e.g., https://user.github.io/survync/)",
    )
    parser.add_argument(
        "--include-dirs",
        nargs="+",
        default=None,
        help="Directories to include (default: mods config shaderpacks ...)",
    )
    parser.add_argument(
        "--exclude-patterns",
        nargs="+",
        default=None,
        help="Additional exclude patterns",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )

    args = parser.parse_args()

    if not args.profile_dir.is_dir():
        print(f"Error: Profile directory does not exist: {args.profile_dir}", file=sys.stderr)
        sys.exit(1)

    exclude = list(DEFAULT_EXCLUDE_PATTERNS)
    if args.exclude_patterns:
        exclude.extend(args.exclude_patterns)

    # Set final values based on precedence: CLI Arg > Metadata > Defaults
    metadata = read_profile_metadata(args.profile_dir)

    p_name = args.pack_name
    mc_version = args.minecraft_version
    l_name = args.loader_name
    l_version = args.loader_version

    # Merge with metadata if not provided via CLI
    if p_name == "survival" and "name" in metadata:
        p_name = metadata["name"]
    if mc_version is None:
        mc_version = metadata.get("game_version", "1.20.4")
    if l_name is None:
        l_name = metadata.get("loader", "fabric")
    if l_version is None:
        l_version = metadata.get("loader_version", "0.15.0")

    generate(
        profile_dir=args.profile_dir,
        output_dir=args.output_dir,
        pack_name=p_name,
        pack_version=args.pack_version,
        minecraft_version=mc_version,
        loader_name=l_name,
        loader_version=l_version,
        base_download_url=args.base_download_url,
        include_dirs=args.include_dirs,
        exclude_patterns=exclude,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
