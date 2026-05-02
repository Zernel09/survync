"""Background worker threads for the Survync launcher UI."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from survync.config import LauncherConfig
from survync.models import RemoteVersion, SyncAction
from survync.network import fetch_manifest, fetch_version
from survync.sync_engine import SyncEngine

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """Signals emitted by background workers."""

    finished = Signal()
    error = Signal(str)
    progress = Signal(int, int, str)  # current, total, filename

    # Check-specific
    version_checked = Signal(object, object)  # RemoteVersion, needs_update: bool

    # Sync-specific
    sync_complete = Signal(object)  # SyncResult

    # Repair-specific
    repair_complete = Signal(object)  # SyncResult


class CheckUpdateWorker(QRunnable):
    """Check the remote server for updates."""

    def __init__(self, config: LauncherConfig) -> None:
        super().__init__()
        self.config = config
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            remote = fetch_version(self.config.version_url)
            needs_update = remote.pack_version != self.config.last_known_version
            if needs_update and not self.config.last_known_version:
                needs_update = not self._profile_matches_remote(remote)
            self.signals.version_checked.emit(remote, needs_update)
        except Exception as exc:
            logger.exception("Update check failed")
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()

    def _profile_matches_remote(self, remote: RemoteVersion) -> bool:
        """Infer first-run local version by hashing files against the manifest."""
        profile_path = Path(self.config.profile_path)
        if not profile_path.is_dir():
            return False

        manifest_url = remote.manifest_url or self.config.manifest_url
        manifest = fetch_manifest(manifest_url)
        engine = SyncEngine(
            profile_path=profile_path,
            manifest=manifest,
            preserve_paths=self.config.preserve_paths,
            remove_orphans=self.config.remove_orphans,
        )
        plan = engine.plan()
        actionable = {SyncAction.ADDED, SyncAction.UPDATED, SyncAction.REMOVED}
        if any(action in actionable for action in plan.values()):
            return False

        self.config.last_known_version = remote.pack_version
        self.config.last_sync_time = datetime.now(timezone.utc).isoformat()
        self.config.save()
        logger.info(
            "Local profile matches remote manifest; recorded version %s",
            self.config.last_known_version,
        )
        return True


class SyncWorker(QRunnable):
    """Download and sync files from the remote manifest."""

    def __init__(
        self,
        config: LauncherConfig,
        manifest_url: str | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.manifest_url = manifest_url or config.manifest_url
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            manifest = fetch_manifest(self.manifest_url)
            engine = SyncEngine(
                profile_path=Path(self.config.profile_path),
                manifest=manifest,
                preserve_paths=self.config.preserve_paths,
                remove_orphans=self.config.remove_orphans,
                progress_callback=self._on_progress,
            )
            result = engine.execute()
            self.signals.sync_complete.emit(result)
        except Exception as exc:
            logger.exception("Sync failed")
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()

    def _on_progress(self, current: int, total: int, filename: str) -> None:
        self.signals.progress.emit(current, total, filename)


class RepairWorker(QRunnable):
    """Re-validate and repair all files."""

    def __init__(self, config: LauncherConfig) -> None:
        super().__init__()
        self.config = config
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            manifest = fetch_manifest(self.config.manifest_url)
            engine = SyncEngine(
                profile_path=Path(self.config.profile_path),
                manifest=manifest,
                preserve_paths=self.config.preserve_paths,
                remove_orphans=False,
                progress_callback=self._on_progress,
            )
            result = engine.repair()
            self.signals.repair_complete.emit(result)
        except Exception as exc:
            logger.exception("Repair failed")
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()

    def _on_progress(self, current: int, total: int, filename: str) -> None:
        self.signals.progress.emit(current, total, filename)
