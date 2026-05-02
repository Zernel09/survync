"""Tests for the sync engine."""

import hashlib
import tempfile
from pathlib import Path

from survync.models import FileEntry, Manifest, SyncAction
from survync.sync_engine import SyncEngine


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_manifest(files: list[FileEntry]) -> Manifest:
    return Manifest(
        pack_name="test",
        pack_version="1.0.0",
        minecraft_version="1.20.4",
        loader_name="fabric",
        loader_version="0.15.0",
        files=files,
    )


def test_plan_added_file():
    """New remote file not present locally should be ADDED."""
    with tempfile.TemporaryDirectory() as d:
        profile = Path(d)
        entry = FileEntry(
            relative_path="mods/new.jar",
            file_name="new.jar",
            sha256="abc123",
            size=100,
        )
        manifest = _make_manifest([entry])
        engine = SyncEngine(profile, manifest)
        plan = engine.plan()
        assert plan["mods/new.jar"] == SyncAction.ADDED


def test_plan_unchanged_file():
    """File that matches remote hash should be UNCHANGED."""
    with tempfile.TemporaryDirectory() as d:
        profile = Path(d)
        content = b"mod content"
        h = _hash(content)

        mod_dir = profile / "mods"
        mod_dir.mkdir()
        (mod_dir / "existing.jar").write_bytes(content)

        entry = FileEntry(
            relative_path="mods/existing.jar",
            file_name="existing.jar",
            sha256=h,
            size=len(content),
        )
        manifest = _make_manifest([entry])
        engine = SyncEngine(profile, manifest)
        plan = engine.plan()
        assert plan["mods/existing.jar"] == SyncAction.UNCHANGED


def test_plan_updated_file():
    """File with hash mismatch should be UPDATED."""
    with tempfile.TemporaryDirectory() as d:
        profile = Path(d)
        mod_dir = profile / "mods"
        mod_dir.mkdir()
        (mod_dir / "changed.jar").write_bytes(b"old version")

        entry = FileEntry(
            relative_path="mods/changed.jar",
            file_name="changed.jar",
            sha256="different_hash",
            size=100,
        )
        manifest = _make_manifest([entry])
        engine = SyncEngine(profile, manifest)
        plan = engine.plan()
        assert plan["mods/changed.jar"] == SyncAction.UPDATED


def test_plan_preserved_file():
    """Files matching preserve patterns should be PRESERVED."""
    with tempfile.TemporaryDirectory() as d:
        profile = Path(d)
        entry = FileEntry(
            relative_path="saves/world1/level.dat",
            file_name="level.dat",
            sha256="abc",
            size=50,
        )
        manifest = _make_manifest([entry])
        engine = SyncEngine(profile, manifest, preserve_paths=["saves/"])
        plan = engine.plan()
        assert plan["saves/world1/level.dat"] == SyncAction.PRESERVED


def test_plan_orphan_removal():
    """Orphan files should be REMOVED when remove_orphans=True."""
    with tempfile.TemporaryDirectory() as d:
        profile = Path(d)
        mod_dir = profile / "mods"
        mod_dir.mkdir()
        (mod_dir / "orphan.jar").write_bytes(b"orphan")

        content = b"kept"
        entry = FileEntry(
            relative_path="mods/kept.jar",
            file_name="kept.jar",
            sha256=_hash(content),
            size=len(content),
        )
        manifest = _make_manifest([entry])
        (mod_dir / "kept.jar").write_bytes(content)

        engine = SyncEngine(profile, manifest, remove_orphans=True)
        plan = engine.plan()
        assert plan.get("mods/orphan.jar") == SyncAction.REMOVED
        assert plan.get("mods/kept.jar") == SyncAction.UNCHANGED


def test_plan_no_orphan_removal():
    """Orphans should NOT be detected when remove_orphans=False."""
    with tempfile.TemporaryDirectory() as d:
        profile = Path(d)
        mod_dir = profile / "mods"
        mod_dir.mkdir()
        (mod_dir / "orphan.jar").write_bytes(b"orphan")

        manifest = _make_manifest([])
        engine = SyncEngine(profile, manifest, remove_orphans=False)
        plan = engine.plan()
        assert "mods/orphan.jar" not in plan


def test_preserved_pattern_match():
    """Test various preserve pattern formats."""
    with tempfile.TemporaryDirectory() as d:
        profile = Path(d)
        engine = SyncEngine(
            profile,
            _make_manifest([]),
            preserve_paths=["saves/", "options.txt", "*.dat"],
        )

        assert engine._is_preserved("saves/world/level.dat")
        assert engine._is_preserved("options.txt")
        assert engine._is_preserved("servers.dat")
        assert not engine._is_preserved("mods/test.jar")
