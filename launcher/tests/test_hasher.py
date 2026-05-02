"""Tests for hashing utilities."""

import hashlib
import tempfile
from pathlib import Path

from survync.hasher import sha256_bytes, sha256_file, verify_file


def test_sha256_file():
    content = b"hello world"
    expected = hashlib.sha256(content).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(content)
        f.flush()
        result = sha256_file(Path(f.name))

    assert result == expected


def test_sha256_bytes():
    content = b"test data"
    expected = hashlib.sha256(content).hexdigest()
    assert sha256_bytes(content) == expected


def test_verify_file_match():
    content = b"verify me"
    expected = hashlib.sha256(content).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(content)
        f.flush()
        assert verify_file(Path(f.name), expected)


def test_verify_file_mismatch():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(b"actual content")
        f.flush()
        assert not verify_file(Path(f.name), "wrong_hash")


def test_verify_file_missing():
    assert not verify_file(Path("/nonexistent/file.bin"), "any_hash")
