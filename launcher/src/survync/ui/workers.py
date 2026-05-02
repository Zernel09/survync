"""Background worker threads for the Survync launcher UI."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from survync.config import LauncherConfig
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
            self.signals.version_checked.emit(remote, needs_update)
        except Exception as exc:
            logger.exception("Update check failed")
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


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
