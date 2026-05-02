"""File hashing utilities for Survync."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BUFFER_SIZE = 65536  # 64 KB read buffer


def sha256_file(filepath: Path) -> str:
    """Compute the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                h.update(chunk)
    except OSError as exc:
        logger.error("Failed to hash %s: %s", filepath, exc)
        raise
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute the SHA-256 hex digest of in-memory bytes."""
    return hashlib.sha256(data).hexdigest()


def verify_file(filepath: Path, expected_hash: str) -> bool:
    """Check whether a file matches the expected SHA-256 hash."""
    if not filepath.is_file():
        return False
    actual = sha256_file(filepath)
    match = actual == expected_hash
    if not match:
        logger.debug(
            "Hash mismatch for %s: expected %s, got %s",
            filepath,
            expected_hash,
            actual,
        )
    return match
