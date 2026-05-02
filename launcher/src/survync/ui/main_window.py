"""Main window for the Survync launcher."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QIcon
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
from survync.config import LauncherConfig, get_app_data_dir
from survync.models import LauncherState, RemoteVersion, SyncResult
from survync.profile_detector import find_profile, validate_profile
from survync.ui.settings_dialog import SettingsDialog
from survync.ui.styles import DARK_THEME
from survync.ui.workers import CheckUpdateWorker, RepairWorker, SyncWorker

logger = logging.getLogger(__name__)

# colores para el log en html
_LOG_COLORS = {
    "error":   "#e05c5c",
    "warn":    "#e0a84a",
    "success": "#5cba7d",
    "info":    "#cfd3cf",
}


def _icon_path() -> Path:
    """Ruta al icono empaquetado junto al ejecutable o en assets/."""
    # cuando se corre como .exe, los assets están junto al ejecutable
    import sys
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent.parent))
    candidates = [
        base / "assets" / "icon.ico",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "assets" / "icon.ico",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return Path()


class MainWindow(QMainWindow):
    """Ventana principal del launcher de Survync."""

    def __init__(self, config: LauncherConfig) -> None:
        super().__init__()
        self.config = config
        self.thread_pool = QThreadPool()
        self._remote_version: RemoteVersion | None = None
        self._state = LauncherState.READY
        self._downloaded_bytes = 0

        self.setWindowTitle(f"Survync v{__version__}")
        self.setMinimumSize(600, 480)
        self.setStyleSheet(DARK_THEME)

        icon = _icon_path()
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))

        self._build_ui()
        self._load_recent_log()
        self._auto_detect_profile()

        if self.config.check_updates_on_start and self.config.remote_base_url:
            self._check_for_updates()

    # ------------------------------------------------------------------ build

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 20, 28, 18)
        layout.setSpacing(12)

        title = QLabel("Survync")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Modpack sync tool")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # panel de info
        summary = QFrame()
        summary.setObjectName("summaryPanel")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(18, 12, 18, 12)
        summary_layout.setSpacing(6)

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

        # botón principal
        self.sync_btn = QPushButton("Sync")
        self.sync_btn.setObjectName("playButton")
        self.sync_btn.clicked.connect(self._on_sync)
        layout.addWidget(self.sync_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # botones secundarios
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
        self.log_panel.setMaximumHeight(180)
        layout.addWidget(self.log_panel)

        footer = QLabel(f"Survync v{__version__}")
        footer.setObjectName("detailLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(footer)

        self._update_version_labels()
        self._update_profile_labels()

    # ------------------------------------------------------------------ state

    def _set_state(self, state: LauncherState, detail: str = "") -> None:
        self._state = state
        text = state.value
        if detail:
            text = f"{state.value} — {detail}"
        self.status_label.setText(text)

        busy = state not in (LauncherState.READY, LauncherState.ERROR)
        self.sync_btn.setEnabled(not busy)
        self.check_btn.setEnabled(not busy)
        self.repair_btn.setEnabled(not busy)

    def _update_sync_btn(self, up_to_date: bool) -> None:
        """Cambia la apariencia del botón según si hay update disponible."""
        if up_to_date:
            self.sync_btn.setText("✓ Up to date")
            self.sync_btn.setProperty("upToDate", True)
        else:
            self.sync_btn.setText("Sync")
            self.sync_btn.setProperty("upToDate", False)
        # forzar recarga del estilo
        self.sync_btn.style().unpolish(self.sync_btn)
        self.sync_btn.style().polish(self.sync_btn)

    # ------------------------------------------------------------------ log

    def _log(self, message: str, kind: str = "info") -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        color = _LOG_COLORS.get(kind, _LOG_COLORS["info"])
        html = (
            f'<span style="color:#666;">[{ts}]</span> '
            f'<span style="color:{color};">{message}</span>'
        )
        self.log_panel.append(html)
        logger.info(message)

    def _load_recent_log(self) -> None:
        """Muestra las últimas 20 líneas del archivo de log al arrancar."""
        log_file = get_app_data_dir() / "survync.log"
        if not log_file.is_file():
            return
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            recent = lines[-20:] if len(lines) > 20 else lines
            self.log_panel.append(
                '<span style="color:#444;">— previous session —</span>'
            )
            for line in recent:
                self.log_panel.append(
                    f'<span style="color:#555;">{line}</span>'
                )
            self.log_panel.append(
                '<span style="color:#444;">— current session —</span>'
            )
        except OSError:
            pass

    # ------------------------------------------------------------------ labels

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
            # solo el nombre de la carpeta, no la ruta completa
            name = Path(self.config.profile_path).name
            self.profile_label.setText(f"Profile: {name}")
        else:
            self.profile_label.setText("Profile: not selected")

    # ------------------------------------------------------------------ profile

    def _auto_detect_profile(self) -> None:
        if self.config.profile_path:
            path = Path(self.config.profile_path)
            if path.is_dir():
                self._log(f"Using profile: {path.name}")
                self._update_profile_labels()
                return
            self._log(f"Configured profile not found: {path}", "warn")

        profile = find_profile(self.config.profile_name)
        if profile:
            self.config.profile_path = str(profile)
            self.config.save()
            self._log(f"Auto-detected profile: {profile.name}", "success")
            self._update_profile_labels()
            warnings = validate_profile(profile)
            for w in warnings:
                self._log(f"Warning: {w}", "warn")
        else:
            self._log(
                f"Could not auto-detect '{self.config.profile_name}' profile. "
                "Prompting for the profile folder.",
                "warn",
            )
            self._prompt_for_profile_path()

    def _prompt_for_profile_path(self) -> None:
        QMessageBox.information(
            self,
            "Select Modrinth Profile",
            "Survync could not find your Modrinth profile automatically. "
            "Please select the profile folder.",
        )
        folder = QFileDialog.getExistingDirectory(self, "Select Modrinth Profile Folder")
        if not folder:
            self._log("No profile folder selected. You can choose one in Settings.", "warn")
            return

        profile = Path(folder)
        self.config.profile_path = str(profile)
        self.config.profile_name = profile.name
        self.config.save()
        self._log(f"Selected profile: {profile.name}", "success")
        self._update_profile_labels()

        for w in validate_profile(profile):
            self._log(f"Warning: {w}", "warn")

    # ------------------------------------------------------------------ update check

    def _check_for_updates(self) -> None:
        errors = self.config.validate()
        if "remote_base_url is not set" in errors:
            self._log("Remote URL not configured — open Settings.", "error")
            self._set_state(LauncherState.ERROR, "Remote URL not configured")
            return

        self._set_state(LauncherState.CHECKING)
        self._log("Checking for updates...")

        worker = CheckUpdateWorker(self.config)
        worker.signals.version_checked.connect(self._on_version_checked)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    def _on_version_checked(self, remote_version: RemoteVersion, needs_update: bool) -> None:
        self._remote_version = remote_version
        self._update_version_labels()

        if needs_update:
            self._log(
                f"Update available: {remote_version.pack_version} "
                f"(current: {self.config.last_known_version or 'unknown'})",
                "warn",
            )
            if remote_version.release_notes:
                self._log(f"Notes: {remote_version.release_notes}")
            self._update_sync_btn(up_to_date=False)
            self._set_state(LauncherState.READY, "Update available")
        else:
            self._log("Already up to date.", "success")
            self._update_sync_btn(up_to_date=True)
            self._set_state(LauncherState.READY)

    # ------------------------------------------------------------------ sync

    def _on_sync(self) -> None:
        errors = self.config.validate()
        if errors:
            for e in errors:
                self._log(e, "error")
            self._set_state(LauncherState.ERROR, errors[0])
            return

        if self._remote_version is None and self.config.remote_base_url:
            self._log("Checking for updates...")
            self._set_state(LauncherState.CHECKING)
            worker = CheckUpdateWorker(self.config)
            worker.signals.version_checked.connect(self._on_check_then_sync)
            worker.signals.error.connect(self._on_error)
            self.thread_pool.start(worker)
            return

        self._start_sync()

    def _on_check_then_sync(self, remote_version: RemoteVersion, needs_update: bool) -> None:
        self._remote_version = remote_version
        self._update_version_labels()

        if needs_update:
            self._log(
                f"Update available: {remote_version.pack_version} "
                f"(current: {self.config.last_known_version or 'unknown'})",
                "warn",
            )
            self._start_sync()
        else:
            self._log("Already up to date. Nothing to sync.", "success")
            self._update_sync_btn(up_to_date=True)
            self._set_state(LauncherState.READY)

    def _start_sync(self) -> None:
        self._downloaded_bytes = 0
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
        mb = self._downloaded_bytes / (1024 * 1024)
        self._set_state(LauncherState.UPDATING, f"{current}/{total} — {mb:.1f} MB")
        self._log(f"[{current}/{total}] {filename}")

    def _on_sync_complete(self, result: SyncResult) -> None:
        self.progress_bar.setVisible(False)
        self._log("Sync complete:", "success")
        self._log(result.summary())

        if result.has_failures:
            self._log("Some files failed to sync:", "error")
            for path, error in result.failed:
                self._log(f"  FAILED: {path} — {error}", "error")
            self._update_sync_btn(up_to_date=False)
            self._set_state(LauncherState.ERROR, "Sync completed with errors")
            return

        if self._remote_version:
            self.config.last_known_version = self._remote_version.pack_version
            self.config.last_sync_time = datetime.now(timezone.utc).isoformat()
            self.config.save()
            self._update_version_labels()

        self._log("Done! You can now open Modrinth and play.", "success")
        self._update_sync_btn(up_to_date=True)
        self._set_state(LauncherState.READY)

    # ------------------------------------------------------------------ repair

    def _repair(self) -> None:
        errors = self.config.validate()
        if errors:
            for e in errors:
                self._log(e, "error")
            self._set_state(LauncherState.ERROR, errors[0])
            return

        self._set_state(LauncherState.REPAIRING)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self._log("Starting repair — re-validating all files...", "warn")

        worker = RepairWorker(self.config)
        worker.signals.progress.connect(self._on_sync_progress)
        worker.signals.repair_complete.connect(self._on_repair_complete)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    def _on_repair_complete(self, result: SyncResult) -> None:
        self.progress_bar.setVisible(False)
        self._log("Repair complete:", "success")
        self._log(result.summary())

        if result.has_failures:
            self._log("Some files failed:", "error")
            for path, error in result.failed:
                self._log(f"  FAILED: {path} — {error}", "error")
            self._set_state(LauncherState.ERROR, "Repair completed with errors")
        else:
            self._set_state(LauncherState.READY)

    # ------------------------------------------------------------------ settings / errors

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, parent=self)
        if dialog.exec():
            self._log("Settings saved.", "success")
            self._update_version_labels()
            self._update_profile_labels()

    def _on_error(self, error: str) -> None:
        self.progress_bar.setVisible(False)
        self._log(f"Error: {error}", "error")
        self._set_state(LauncherState.ERROR, error[:80])
