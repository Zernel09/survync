"""Networking utilities for Survync launcher."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from survync.models import Manifest, RemoteVersion

logger = logging.getLogger(__name__)

USER_AGENT = "Survync/0.1.0 (Minecraft Modpack Launcher)"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# extensiones de texto que GitHub Pages puede alterar los line endings
# para estas no validamos tamaño — solo el hash sha256 es confiable
_TEXT_EXTENSIONS = {
    ".toml", ".properties", ".json", ".json5",
    ".yml", ".yaml", ".cfg", ".txt", ".css",
    ".ini", ".conf", ".xml", ".md", ".bak",
}


class NetworkError(Exception):
    """Raised when a network operation fails after retries."""


def _request(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """Perform an HTTP GET with retries.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Response body as bytes.

    Raises:
        NetworkError: After all retries are exhausted.
    """
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (HTTPError, URLError, OSError) as exc:
            last_error = exc
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    raise NetworkError(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {last_error}")


def fetch_version(version_url: str) -> RemoteVersion:
    """Fetch and parse version.json from the remote server."""
    logger.info("Fetching version info from %s", version_url)
    data = _request(version_url)
    parsed = json.loads(data)
    return RemoteVersion.from_dict(parsed)


def fetch_manifest(manifest_url: str) -> Manifest:
    """Fetch and parse manifest.json from the remote server."""
    logger.info("Fetching manifest from %s", manifest_url)
    data = _request(manifest_url)
    parsed = json.loads(data)
    return Manifest.from_dict(parsed)


def download_file(
    url: str,
    dest: Path,
    expected_hash: str | None = None,
    expected_size: int | None = None,
) -> Path:
    """Download a file to a temporary location, verify, then move to dest.

    Uses atomic replace: downloads to dest.tmp then renames.

    For text-based file types (toml, properties, json, etc.) the size check is
    skipped because GitHub Pages may normalise line endings (CRLF -> LF), which
    changes the byte count but leaves the content semantically identical.
    Integrity is still guaranteed by the SHA-256 hash check.

    Args:
        url: Download URL.
        dest: Final destination path.
        expected_hash: Expected SHA-256 hex digest for verification.
        expected_size: Expected file size in bytes (skipped for text files).

    Returns:
        The final destination path.

    Raises:
        NetworkError: If download fails.
        ValueError: If hash verification fails.
    """
    import hashlib

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_suffix(dest.suffix + ".tmp")

    logger.info("Downloading %s -> %s", url, dest)
    data = _request(url)

    # solo validamos tamaño para archivos binarios — los de texto pueden tener
    # line endings distintos entre el servidor y el disco local
    is_text = dest.suffix.lower() in _TEXT_EXTENSIONS
    if expected_size is not None and not is_text and len(data) != expected_size:
        raise ValueError(
            f"Size mismatch for {url}: expected {expected_size}, got {len(data)}"
        )

    if expected_hash is not None:
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(
                f"Hash mismatch for {url}: expected {expected_hash}, got {actual_hash}"
            )

    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
        tmp_path.replace(dest)
    except OSError:
        # en Windows, replace puede fallar si dest está bloqueado
        if dest.exists():
            dest.unlink()
        tmp_path.rename(dest)

    logger.info("Downloaded %s (%d bytes)", dest.name, len(data))
    return dest
