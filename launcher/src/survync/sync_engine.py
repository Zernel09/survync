"""Core sync engine — compares local vs remote and applies changes."""

from __future__ import annotations

import fnmatch
import logging
from collections.abc import Callable
from pathlib import Path

from survync.hasher import sha256_file
from survync.models import FileEntry, Manifest, SyncAction, SyncResult
from survync.network import NetworkError, download_file

logger = logging.getLogger(__name__)


class SyncEngine:
    """Compares local files against a remote manifest and syncs differences."""

    def __init__(
        self,
        profile_path: Path,
        manifest: Manifest,
        preserve_paths: list[str] | None = None,
        remove_orphans: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        """
        Args:
            profile_path: Root of the local Modrinth profile.
            manifest: The remote manifest describing the desired state.
            preserve_paths: Glob patterns for paths that should never be modified.
            remove_orphans: If True, remove local files not in the manifest
                            (respecting preserve_paths).
            progress_callback: Called with (current, total, filename) during sync.
        """
        self.profile_path = profile_path
        self.manifest = manifest
        self.preserve_paths = preserve_paths or []
        self.remove_orphans = remove_orphans
        self.progress_callback = progress_callback

    def _is_preserved(self, relative_path: str) -> bool:
        """Check if a path matches any preserve pattern."""
        for pattern in self.preserve_paths:
            # Match directory prefixes (e.g. "saves/" matches "saves/world1/level.dat")
            if pattern.endswith("/") and relative_path.startswith(pattern):
                return True
            if fnmatch.fnmatch(relative_path, pattern):
                return True
            if relative_path == pattern:
                return True
        return False

    def plan(self) -> dict[str, SyncAction]:
        """Compute the sync plan without making any changes.

        Returns:
            Dict mapping relative_path -> action to take.
        """
        plan: dict[str, SyncAction] = {}
        remote_files = {fe.relative_path: fe for fe in self.manifest.files}

        # Determine actions for remote files
        for rel_path, entry in remote_files.items():
            if self._is_preserved(rel_path):
                plan[rel_path] = SyncAction.PRESERVED
                continue

            local_file = self.profile_path / rel_path
            if not local_file.is_file():
                plan[rel_path] = SyncAction.ADDED
            else:
                try:
                    local_hash = sha256_file(local_file)
                except OSError:
                    plan[rel_path] = SyncAction.UPDATED
                    continue
                if local_hash != entry.sha256:
                    plan[rel_path] = SyncAction.UPDATED
                else:
                    plan[rel_path] = SyncAction.UNCHANGED

        # Determine orphans (local files not in remote manifest)
        if self.remove_orphans:
            managed_dirs = set()
            for fe in self.manifest.files:
                parts = Path(fe.relative_path).parts
                if len(parts) > 1:
                    managed_dirs.add(parts[0])

            for managed_dir in managed_dirs:
                dir_path = self.profile_path / managed_dir
                if not dir_path.is_dir():
                    continue
                for local_file in dir_path.rglob("*"):
                    if not local_file.is_file():
                        continue
                    rel = str(local_file.relative_to(self.profile_path)).replace("\\", "/")
                    if rel not in remote_files and rel not in plan:
                        if self._is_preserved(rel):
                            plan[rel] = SyncAction.PRESERVED
                        else:
                            plan[rel] = SyncAction.REMOVED

        return plan

    def execute(self) -> SyncResult:
        """Execute the sync: download, update, and optionally remove files.

        Returns:
            SyncResult with details of what happened.
        """
        result = SyncResult()
        plan = self.plan()
        remote_files = {fe.relative_path: fe for fe in self.manifest.files}

        actionable = {
            p: a
            for p, a in plan.items()
            if a in (SyncAction.ADDED, SyncAction.UPDATED, SyncAction.REMOVED)
        }
        total = len(actionable)
        current = 0

        for rel_path, action in plan.items():
            if action == SyncAction.UNCHANGED:
                continue
            elif action == SyncAction.PRESERVED:
                result.preserved.append(rel_path)
                continue
            elif action == SyncAction.SKIPPED:
                result.skipped.append(rel_path)
                continue

            current += 1
            if self.progress_callback:
                self.progress_callback(current, total, rel_path)

            if action == SyncAction.REMOVED:
                self._remove_file(rel_path, result)
            elif action in (SyncAction.ADDED, SyncAction.UPDATED):
                entry = remote_files.get(rel_path)
                if entry is None:
                    logger.error("No manifest entry for %s — skipping", rel_path)
                    result.failed.append((rel_path, "Missing manifest entry"))
                    continue
                self._download_file(entry, action, result)

        return result

    def _download_file(
        self, entry: FileEntry, action: SyncAction, result: SyncResult
    ) -> None:
        """Download or update a single file."""
        dest = self.profile_path / entry.relative_path
        try:
            download_file(
                url=entry.download_url,
                dest=dest,
                expected_hash=entry.sha256,
                expected_size=entry.size,
            )
            result.total_downloaded_bytes += entry.size
            if action == SyncAction.ADDED:
                result.added.append(entry.relative_path)
            else:
                result.updated.append(entry.relative_path)
        except (NetworkError, ValueError, OSError) as exc:
            logger.error("Failed to sync %s: %s", entry.relative_path, exc)
            result.failed.append((entry.relative_path, str(exc)))

    def _remove_file(self, rel_path: str, result: SyncResult) -> None:
        """Remove an orphaned file."""
        local_file = self.profile_path / rel_path
        try:
            if local_file.is_file():
                local_file.unlink()
                result.removed.append(rel_path)
                logger.info("Removed orphan: %s", rel_path)
        except OSError as exc:
            logger.error("Failed to remove %s: %s", rel_path, exc)
            result.failed.append((rel_path, str(exc)))

    def repair(self) -> SyncResult:
        """Re-validate all files and fix mismatches.

        Like execute(), but treats every file as potentially wrong.
        """
        result = SyncResult()
        remote_files = {fe.relative_path: fe for fe in self.manifest.files}
        total = len(remote_files)
        current = 0

        for rel_path, entry in remote_files.items():
            current += 1
            if self.progress_callback:
                self.progress_callback(current, total, rel_path)

            if self._is_preserved(rel_path):
                result.preserved.append(rel_path)
                continue

            local_file = self.profile_path / rel_path
            needs_download = False
            if not local_file.is_file():
                needs_download = True
            else:
                try:
                    local_hash = sha256_file(local_file)
                    if local_hash != entry.sha256:
                        needs_download = True
                except OSError:
                    needs_download = True

            if needs_download:
                self._download_file(entry, SyncAction.UPDATED, result)
            else:
                result.skipped.append(rel_path)

        return result
