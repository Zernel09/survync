"""Optional Modrinth API integration.

This module provides helpers for querying the Modrinth REST API.
All functions are optional and only used when a project slug or
project ID is explicitly configured.

IMPORTANT: We never blindly search for "survival" and bind to a
random result.  The user must provide an exact slug or project ID.
"""

from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

MODRINTH_API_BASE = "https://api.modrinth.com/v2"
USER_AGENT = "Survync/0.1.0 (Minecraft Modpack Launcher)"
DEFAULT_TIMEOUT = 15


class ModrinthAPIError(Exception):
    """Raised when a Modrinth API call fails."""


def _api_get(endpoint: str) -> dict | list:
    """Perform a GET request against the Modrinth API."""
    url = f"{MODRINTH_API_BASE}{endpoint}"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read())
    except (HTTPError, URLError, OSError) as exc:
        raise ModrinthAPIError(f"Modrinth API request failed: {exc}") from exc


def get_project(slug_or_id: str) -> dict:
    """Fetch a Modrinth project by slug or project ID.

    Args:
        slug_or_id: Exact project slug (e.g. "my-modpack") or project ID.

    Returns:
        Project data dict.
    """
    return _api_get(f"/project/{slug_or_id}")  # type: ignore[return-value]


def list_versions(
    project_id: str,
    game_version: str | None = None,
    loader: str | None = None,
) -> list[dict]:
    """List versions of a Modrinth project.

    Args:
        project_id: The project ID or slug.
        game_version: Optional Minecraft version filter.
        loader: Optional loader filter (e.g. "fabric", "forge").

    Returns:
        List of version dicts.
    """
    params = []
    if game_version:
        params.append(f'game_versions=["{game_version}"]')
    if loader:
        params.append(f'loaders=["{loader}"]')

    query = "&".join(params)
    endpoint = f"/project/{project_id}/version"
    if query:
        endpoint += f"?{query}"

    return _api_get(endpoint)  # type: ignore[return-value]


def get_version(version_id: str) -> dict:
    """Fetch a specific version by ID."""
    return _api_get(f"/version/{version_id}")  # type: ignore[return-value]


def get_version_files(version_id: str) -> list[dict]:
    """Get the file list for a specific version."""
    version = get_version(version_id)
    return version.get("files", [])


def lookup_project_safe(slug_or_id: str | None) -> dict | None:
    """Safely look up a project.  Returns None on any error.

    This will NOT search by name — it requires an exact slug or ID.
    """
    if not slug_or_id:
        return None
    try:
        return get_project(slug_or_id)
    except ModrinthAPIError as exc:
        logger.info("Modrinth project lookup failed for '%s': %s", slug_or_id, exc)
        return None
