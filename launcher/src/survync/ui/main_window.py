"""Main window for the Survync launcher."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from survync import __version__
from survync.config import LauncherConfig
from survync.launcher import launch_profile
from survync.models import LauncherState, RemoteVersion, SyncResult
from survync.profile_detector import find_profile, validate_profile
from survync.ui.settings_dialog import SettingsDialog
from survync.ui.styles import DARK_THEME
from survync.ui.workers import CheckUpdateWorker, RepairWorker, SyncWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Primary launcher window."""

    def __init__(self, config: LauncherConfig) -> None:
        super().__init__()
        self.config = config
        self.thread_pool = QThreadPool()
        self._remote_version: RemoteVersion | None = None
        self._state = LauncherState.READY

        self.setWindowTitle(f"Survync v{__version__}")
        self.setMinimumSize(520, 560)
        self.setStyleSheet(DARK_THEME)

        self._build_ui()
        self._auto_detect_profile()

        if self.config.check_updates_on_start and self.config.remote_base_url:
            self._check_for_updates()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Title
        title = QLabel("Survync")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Version info row
        version_row = QHBoxLayout()
        self.local_version_label = QLabel("Local: —")
        self.local_version_label.setObjectName("versionLabel")
        self.remote_version_label = QLabel("Remote: —")
        self.remote_version_label.setObjectName("versionLabel")
        version_row.addWidget(self.local_version_label)
        version_row.addStretch()
        version_row.addWidget(self.remote_version_label)
        layout.addLayout(version_row)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Play button
        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("playButton")
        self.play_btn.clicked.connect(self._on_play)
        layout.addWidget(self.play_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Action buttons row
        btn_row = QHBoxLayout()
        self.check_btn = QPushButton("Check Updates")
        self.check_btn.clicked.connect(self._check_for_updates)
        btn_row.addWidget(self.check_btn)

        self.repair_btn = QPushButton("Repair")
        self.repair_btn.clicked.connect(self._repair)
        btn_row.addWidget(self.repair_btn)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self._open_settings)
        btn_row.addWidget(self.settings_btn)

        layout.addLayout(btn_row)

        # Log panel
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setMaximumHeight(180)
        layout.addWidget(self.log_panel)

        # Footer
        footer = QLabel(f"Survync v{__version__}")
        footer.setObjectName("versionLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(footer)

        self._update_version_labels()

    def _set_state(self, state: LauncherState, detail: str = "") -> None:
        self._state = state
        text = state.value
        if detail:
            text = f"{state.value} — {detail}"
        self.status_label.setText(text)

        busy = state not in (LauncherState.READY, LauncherState.ERROR)
        self.play_btn.setEnabled(not busy)
        self.check_btn.setEnabled(not busy)
        self.repair_btn.setEnabled(not busy)

    def _log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.log_panel.append(f"[{ts}] {message}")
        logger.info(message)

    def _update_version_labels(self) -> None:
        local_ver = self.config.last_known_version or "—"
        self.local_version_label.setText(f"Local: {local_ver}")

        if self._remote_version:
            self.remote_version_label.setText(
                f"Remote: {self._remote_version.pack_version}"
            )
        else:
            self.remote_version_label.setText("Remote: —")

    def _auto_detect_profile(self) -> None:
        """Try to auto-detect the Modrinth profile on first run."""
        if self.config.profile_path:
            path = Path(self.config.profile_path)
            if path.is_dir():
                self._log(f"Using configured profile: {path}")
                return
            else:
                self._log(f"Configured profile path not found: {path}")

        profile = find_profile(self.config.profile_name)
        if profile:
            self.config.profile_path = str(profile)
            self.config.save()
            self._log(f"Auto-detected profile: {profile}")
            warnings = validate_profile(profile)
            for w in warnings:
                self._log(f"  Warning: {w}")
        else:
            self._log(
                f"Could not auto-detect '{self.config.profile_name}' profile. "
                "Please set the profile path in Settings."
            )

    # ── Check for updates ──────────────────────────────────────────

    def _check_for_updates(self) -> None:
        errors = self.config.validate()
        if "remote_base_url is not set" in errors:
            self._log("Remote URL not configured — open Settings to set it.")
            self._set_state(LauncherState.ERROR, "Remote URL not configured")
            return

        self._set_state(LauncherState.CHECKING)
        self._log("Checking for updates...")

        worker = CheckUpdateWorker(self.config)
        worker.signals.version_checked.connect(self._on_version_checked)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    def _on_version_checked(
        self, remote_version: RemoteVersion, needs_update: bool
    ) -> None:
        self._remote_version = remote_version
        self._update_version_labels()

        if needs_update:
            self._log(
                f"Update available: {remote_version.pack_version} "
                f"(current: {self.config.last_known_version or 'none'})"
            )
            if remote_version.release_notes:
                self._log(f"  Release notes: {remote_version.release_notes}")
            self._set_state(LauncherState.READY, "Update available!")
        else:
            self._log("You are up to date.")
            self._set_state(LauncherState.READY)

    # ── Play ───────────────────────────────────────────────────────

    def _on_play(self) -> None:
        errors = self.config.validate()
        if errors:
            self._log("Configuration errors:")
            for e in errors:
                self._log(f"  - {e}")
            self._set_state(LauncherState.ERROR, errors[0])
            return

        # If we haven't checked yet, check first
        if self._remote_version is None and self.config.remote_base_url:
            self._log("Checking for updates before launch...")
            self._set_state(LauncherState.CHECKING)
            worker = CheckUpdateWorker(self.config)
            worker.signals.version_checked.connect(self._on_play_after_check)
            worker.signals.error.connect(self._on_play_check_error)
            self.thread_pool.start(worker)
            return

        # If update is needed, sync first
        if (
            self._remote_version
            and self._remote_version.pack_version != self.config.last_known_version
        ):
            self._start_sync()
            return

        self._launch()

    def _on_play_after_check(
        self, remote_version: RemoteVersion, needs_update: bool
    ) -> None:
        self._remote_version = remote_version
        self._update_version_labels()

        if needs_update:
            self._log("Update needed — syncing before launch...")
            self._start_sync(launch_after=True)
        else:
            self._log("Up to date — launching.")
            self._launch()

    def _on_play_check_error(self, error: str) -> None:
        self._log(f"Update check failed: {error}")
        self._log("Launching with current files...")
        self._launch()

    # ── Sync ───────────────────────────────────────────────────────

    def _start_sync(self, launch_after: bool = True) -> None:
        self._launch_after_sync = launch_after
        self._set_state(LauncherState.UPDATING)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        manifest_url = (
            self._remote_version.manifest_url
            if self._remote_version
            else self.config.manifest_url
        )
        worker = SyncWorker(self.config, manifest_url=manifest_url)
        worker.signals.progress.connect(self._on_sync_progress)
        worker.signals.sync_complete.connect(self._on_sync_complete)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    def _on_sync_progress(self, current: int, total: int, filename: str) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self._set_state(LauncherState.UPDATING, f"{current}/{total}")
        self._log(f"  [{current}/{total}] {filename}")

    def _on_sync_complete(self, result: SyncResult) -> None:
        self.progress_bar.setVisible(False)
        self._log("Sync complete:")
        self._log(result.summary())

        if result.has_failures:
            self._log("Some files failed to sync. Check the log for details.")
            for path, err in result.failed:
                self._log(f"  FAILED: {path} — {err}")
            self._set_state(LauncherState.ERROR, "Sync completed with errors")
            return

        # Update last known version
        if self._remote_version:
            self.config.last_known_version = self._remote_version.pack_version
            self.config.last_sync_time = datetime.now(timezone.utc).isoformat()
            self.config.save()
            self._update_version_labels()

        self._set_state(LauncherState.READY)

        if getattr(self, "_launch_after_sync", False):
            self._launch()

    # ── Repair ─────────────────────────────────────────────────────

    def _repair(self) -> None:
        errors = self.config.validate()
        if errors:
            self._log("Configuration errors:")
            for e in errors:
                self._log(f"  - {e}")
            self._set_state(LauncherState.ERROR, errors[0])
            return

        self._set_state(LauncherState.REPAIRING)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self._log("Starting repair — re-validating all files...")

        worker = RepairWorker(self.config)
        worker.signals.progress.connect(self._on_sync_progress)
        worker.signals.repair_complete.connect(self._on_repair_complete)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    def _on_repair_complete(self, result: SyncResult) -> None:
        self.progress_bar.setVisible(False)
        self._log("Repair complete:")
        self._log(result.summary())

        if result.has_failures:
            self._set_state(LauncherState.ERROR, "Repair completed with errors")
        else:
            self._set_state(LauncherState.READY)

    # ── Launch ─────────────────────────────────────────────────────

    def _launch(self) -> None:
        self._set_state(LauncherState.LAUNCHING)
        self._log(f"Launching profile '{self.config.profile_name}'...")

        success = launch_profile(self.config.profile_name)
        if success:
            self._log("Launch initiated. You can close Survync.")
            self._set_state(LauncherState.READY)
        else:
            self._log(
                "Could not auto-launch. Please open the Modrinth App and "
                f"start the '{self.config.profile_name}' profile manually."
            )
            self._set_state(
                LauncherState.ERROR, "Auto-launch failed — open Modrinth manually"
            )

    # ── Settings ───────────────────────────────────────────────────

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, parent=self)
        if dialog.exec():
            self._log("Settings saved.")
            self._update_version_labels()

    # ── Error handling ─────────────────────────────────────────────

    def _on_error(self, error: str) -> None:
        self.progress_bar.setVisible(False)
        self._log(f"Error: {error}")
        self._set_state(LauncherState.ERROR, error[:80])
