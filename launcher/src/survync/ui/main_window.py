"""Main window for the Survync launcher."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
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
        self.setMinimumSize(620, 640)
        self.setStyleSheet(DARK_THEME)

        self._build_ui()
        self._auto_detect_profile()

        if self.config.check_updates_on_start and self.config.remote_base_url:
            self._check_for_updates()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(14)

        title = QLabel("Survync")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Survival profile updater")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        summary = QFrame()
        summary.setObjectName("summaryPanel")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(18, 14, 18, 14)
        summary_layout.setSpacing(8)

        version_row = QHBoxLayout()
        self.local_version_label = QLabel("Local: unknown")
        self.local_version_label.setObjectName("metricLabel")
        self.remote_version_label = QLabel("Remote: unknown")
        self.remote_version_label.setObjectName("metricLabel")
        version_row.addWidget(self.local_version_label)
        version_row.addStretch()
        version_row.addWidget(self.remote_version_label)
        summary_layout.addLayout(version_row)

        self.profile_label = QLabel("Profile: not selected")
        self.profile_label.setObjectName("detailLabel")
        summary_layout.addWidget(self.profile_label)

        self.minecraft_label = QLabel("Minecraft: unknown")
        self.minecraft_label.setObjectName("detailLabel")
        summary_layout.addWidget(self.minecraft_label)

        layout.addWidget(summary)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("playButton")
        self.play_btn.clicked.connect(self._on_play)
        layout.addWidget(self.play_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

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

        log_title = QLabel("Activity")
        log_title.setObjectName("sectionLabel")
        layout.addWidget(log_title)

        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setMaximumHeight(210)
        layout.addWidget(self.log_panel)

        footer = QLabel(f"Survync v{__version__}")
        footer.setObjectName("detailLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(footer)

        self._update_version_labels()
        self._update_profile_labels()

    def _set_state(self, state: LauncherState, detail: str = "") -> None:
        self._state = state
        text = state.value
        if detail:
            text = f"{state.value} - {detail}"
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
        local_ver = self.config.last_known_version or "unknown"
        self.local_version_label.setText(f"Local: {local_ver}")

        if self._remote_version:
            self.remote_version_label.setText(
                f"Remote: {self._remote_version.pack_version}"
            )
            self.minecraft_label.setText(
                "Minecraft: "
                f"{self._remote_version.minecraft_version} / "
                f"{self._remote_version.loader_name} "
                f"{self._remote_version.loader_version}"
            )
        else:
            self.remote_version_label.setText("Remote: unknown")
            self.minecraft_label.setText("Minecraft: unknown")

    def _update_profile_labels(self) -> None:
        if self.config.profile_path:
            self.profile_label.setText(f"Profile: {self.config.profile_path}")
        else:
            self.profile_label.setText("Profile: not selected")

    def _auto_detect_profile(self) -> None:
        """Try to auto-detect the Modrinth profile on first run."""
        if self.config.profile_path:
            path = Path(self.config.profile_path)
            if path.is_dir():
                self._log(f"Using configured profile: {path}")
                self._update_profile_labels()
                return
            self._log(f"Configured profile path not found: {path}")

        profile = find_profile(self.config.profile_name)
        if profile:
            self.config.profile_path = str(profile)
            self.config.save()
            self._log(f"Auto-detected profile: {profile}")
            self._update_profile_labels()
            warnings = validate_profile(profile)
            for warning in warnings:
                self._log(f"  Warning: {warning}")
        else:
            self._log(
                f"Could not auto-detect '{self.config.profile_name}' profile. "
                "Prompting for the profile folder."
            )
            self._prompt_for_profile_path()

    def _prompt_for_profile_path(self) -> None:
        """Ask the user to select the Modrinth profile folder."""
        QMessageBox.information(
            self,
            "Select Modrinth Profile",
            "Survync could not find your Modrinth profile automatically. "
            "Please select the profile folder.",
        )
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Modrinth Profile Folder",
        )
        if not folder:
            self._log("No profile folder selected. You can choose one in Settings.")
            return

        profile = Path(folder)
        self.config.profile_path = str(profile)
        self.config.profile_name = profile.name
        self.config.save()
        self._log(f"Selected profile: {profile}")
        self._update_profile_labels()

        warnings = validate_profile(profile)
        for warning in warnings:
            self._log(f"  Warning: {warning}")

    def _check_for_updates(self) -> None:
        errors = self.config.validate()
        if "remote_base_url is not set" in errors:
            self._log("Remote URL not configured - open Settings to set it.")
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
                f"(current: {self.config.last_known_version or 'unknown'})"
            )
            if remote_version.release_notes:
                self._log(f"  Release notes: {remote_version.release_notes}")
            self._set_state(LauncherState.READY, "Update available")
        else:
            self._log("Profile is up to date.")
            self._set_state(LauncherState.READY)

    def _on_play(self) -> None:
        errors = self.config.validate()
        if errors:
            self._log("Configuration errors:")
            for error in errors:
                self._log(f"  - {error}")
            self._set_state(LauncherState.ERROR, errors[0])
            return

        if self._remote_version is None and self.config.remote_base_url:
            self._log("Checking for updates before launch...")
            self._set_state(LauncherState.CHECKING)
            worker = CheckUpdateWorker(self.config)
            worker.signals.version_checked.connect(self._on_play_after_check)
            worker.signals.error.connect(self._on_play_check_error)
            self.thread_pool.start(worker)
            return

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
            self._log("Update needed - syncing before launch...")
            self._start_sync(launch_after=True)
        else:
            self._log("Up to date - launching.")
            self._launch()

    def _on_play_check_error(self, error: str) -> None:
        self._log(f"Update check failed: {error}")
        self._log("Launching with current files...")
        self._launch()

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
            for path, error in result.failed:
                self._log(f"  FAILED: {path} - {error}")
            self._set_state(LauncherState.ERROR, "Sync completed with errors")
            return

        if self._remote_version:
            self.config.last_known_version = self._remote_version.pack_version
            self.config.last_sync_time = datetime.now(timezone.utc).isoformat()
            self.config.save()
            self._update_version_labels()

        self._set_state(LauncherState.READY)

        if getattr(self, "_launch_after_sync", False):
            self._launch()

    def _repair(self) -> None:
        errors = self.config.validate()
        if errors:
            self._log("Configuration errors:")
            for error in errors:
                self._log(f"  - {error}")
            self._set_state(LauncherState.ERROR, errors[0])
            return

        self._set_state(LauncherState.REPAIRING)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self._log("Starting repair - re-validating all files...")

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
                LauncherState.ERROR, "Auto-launch failed - open Modrinth manually"
            )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, parent=self)
        if dialog.exec():
            self._log("Settings saved.")
            self._update_version_labels()
            self._update_profile_labels()

    def _on_error(self, error: str) -> None:
        self.progress_bar.setVisible(False)
        self._log(f"Error: {error}")
        self._set_state(LauncherState.ERROR, error[:80])
