"""Tests for data models."""

from survync.models import FileEntry, Manifest, RemoteVersion, SyncResult


def test_file_entry_roundtrip():
    entry = FileEntry(
        relative_path="mods/example.jar",
        file_name="example.jar",
        sha256="abc123",
        size=1024,
        source_type="direct",
        download_url="https://example.com/example.jar",
        modrinth_project_id="proj1",
        modrinth_version_id="ver1",
    )
    d = entry.to_dict()
    restored = FileEntry.from_dict(d)
    assert restored.relative_path == entry.relative_path
    assert restored.sha256 == entry.sha256
    assert restored.modrinth_project_id == "proj1"


def test_file_entry_optional_fields():
    data = {
        "relative_path": "mods/test.jar",
        "file_name": "test.jar",
        "sha256": "def456",
        "size": 512,
    }
    entry = FileEntry.from_dict(data)
    assert entry.source_type == "direct"
    assert entry.download_url == ""
    assert entry.modrinth_project_id is None
    d = entry.to_dict()
    assert "modrinth_project_id" not in d


def test_manifest_from_dict():
    data = {
        "pack_name": "survival",
        "pack_version": "1.0.0",
        "minecraft_version": "1.20.4",
        "loader_name": "fabric",
        "loader_version": "0.15.0",
        "files": [
            {
                "relative_path": "mods/a.jar",
                "file_name": "a.jar",
                "sha256": "aaa",
                "size": 100,
            }
        ],
        "preserve_paths": ["saves/"],
    }
    m = Manifest.from_dict(data)
    assert m.pack_name == "survival"
    assert len(m.files) == 1
    assert m.preserve_paths == ["saves/"]


def test_remote_version_from_dict():
    data = {
        "pack_name": "survival",
        "pack_version": "1.2.0",
        "minecraft_version": "1.20.4",
        "loader_name": "fabric",
        "loader_version": "0.15.0",
        "generated_at": "2025-01-01T00:00:00Z",
        "manifest_url": "https://example.com/manifest.json",
        "release_notes": "Bug fixes",
    }
    rv = RemoteVersion.from_dict(data)
    assert rv.pack_version == "1.2.0"
    assert rv.release_notes == "Bug fixes"


def test_sync_result_summary():
    result = SyncResult()
    assert result.summary() == "  No changes needed."
    assert not result.has_changes

    result.added = ["mods/new.jar"]
    result.updated = ["mods/changed.jar"]
    assert result.has_changes
    assert "Added: 1" in result.summary()
    assert "Updated: 1" in result.summary()


def test_sync_result_failures():
    result = SyncResult()
    assert not result.has_failures
    result.failed = [("mods/broken.jar", "network error")]
    assert result.has_failures
