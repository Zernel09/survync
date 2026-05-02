"""Data models for Survync launcher."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class SourceType(enum.Enum):
    """How a file is sourced for download."""

    DIRECT = "direct"
    MODRINTH = "modrinth"
    CURSEFORGE = "curseforge"
    LOCAL = "local"


class SyncAction(enum.Enum):
    """Action taken for a file during sync."""

    ADDED = "added"
    UPDATED = "updated"
    REMOVED = "removed"
    SKIPPED = "skipped"
    PRESERVED = "preserved"
    UNCHANGED = "unchanged"


class LauncherState(enum.Enum):
    """Current state of the launcher."""

    READY = "Ready"
    CHECKING = "Checking for updates..."
    UPDATING = "Updating"
    LAUNCHING = "Launching..."
    REPAIRING = "Repairing..."
    ERROR = "Error"


@dataclass
class FileEntry:
    """A single file in the manifest."""

    relative_path: str
    file_name: str
    sha256: str
    size: int
    source_type: str = "direct"
    download_url: str = ""
    modrinth_project_id: str | None = None
    modrinth_version_id: str | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "relative_path": self.relative_path,
            "file_name": self.file_name,
            "sha256": self.sha256,
            "size": self.size,
            "source_type": self.source_type,
            "download_url": self.download_url,
        }
        if self.modrinth_project_id:
            d["modrinth_project_id"] = self.modrinth_project_id
        if self.modrinth_version_id:
            d["modrinth_version_id"] = self.modrinth_version_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> FileEntry:
        return cls(
            relative_path=data["relative_path"],
            file_name=data["file_name"],
            sha256=data["sha256"],
            size=data["size"],
            source_type=data.get("source_type", "direct"),
            download_url=data.get("download_url", ""),
            modrinth_project_id=data.get("modrinth_project_id"),
            modrinth_version_id=data.get("modrinth_version_id"),
        )


@dataclass
class RemoteVersion:
    """Remote version metadata from version.json."""

    pack_name: str
    pack_version: str
    minecraft_version: str
    loader_name: str
    loader_version: str
    generated_at: str
    manifest_url: str
    minimum_launcher_version: str | None = None
    release_notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> RemoteVersion:
        return cls(
            pack_name=data["pack_name"],
            pack_version=data["pack_version"],
            minecraft_version=data["minecraft_version"],
            loader_name=data["loader_name"],
            loader_version=data["loader_version"],
            generated_at=data["generated_at"],
            manifest_url=data["manifest_url"],
            minimum_launcher_version=data.get("minimum_launcher_version"),
            release_notes=data.get("release_notes"),
        )


@dataclass
class Manifest:
    """Full manifest with file list and metadata."""

    pack_name: str
    pack_version: str
    minecraft_version: str
    loader_name: str
    loader_version: str
    files: list[FileEntry] = field(default_factory=list)
    preserve_paths: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Manifest:
        files = [FileEntry.from_dict(f) for f in data.get("files", [])]
        return cls(
            pack_name=data["pack_name"],
            pack_version=data["pack_version"],
            minecraft_version=data["minecraft_version"],
            loader_name=data["loader_name"],
            loader_version=data["loader_version"],
            files=files,
            preserve_paths=data.get("preserve_paths", []),
        )

    def to_dict(self) -> dict:
        return {
            "pack_name": self.pack_name,
            "pack_version": self.pack_version,
            "minecraft_version": self.minecraft_version,
            "loader_name": self.loader_name,
            "loader_version": self.loader_version,
            "files": [f.to_dict() for f in self.files],
            "preserve_paths": self.preserve_paths,
        }


@dataclass
class SyncResult:
    """Summary of a sync operation."""

    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    preserved: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    total_downloaded_bytes: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.updated or self.removed)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed)

    def summary(self) -> str:
        lines = []
        if self.added:
            lines.append(f"  Added: {len(self.added)} files")
        if self.updated:
            lines.append(f"  Updated: {len(self.updated)} files")
        if self.removed:
            lines.append(f"  Removed: {len(self.removed)} files")
        if self.preserved:
            lines.append(f"  Preserved: {len(self.preserved)} files")
        if self.skipped:
            lines.append(f"  Skipped: {len(self.skipped)} files")
        if self.failed:
            lines.append(f"  Failed: {len(self.failed)} files")
        if not lines:
            return "  No changes needed."
        return "\n".join(lines)
