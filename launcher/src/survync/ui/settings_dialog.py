"""Settings dialog for Survync launcher."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from survync.config import DEFAULT_PRESERVE_PATHS, LauncherConfig


class SettingsDialog(QDialog):
    """Settings dialog for configuring the launcher."""

    def __init__(self, config: LauncherConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Survync Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Server group
        server_group = QGroupBox("Remote Server")
        server_layout = QFormLayout(server_group)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://<user>.github.io/<repo>/")
        server_layout.addRow("Base URL:", self.url_edit)

        layout.addWidget(server_group)

        # Profile group
        profile_group = QGroupBox("Modrinth Profile")
        profile_layout = QFormLayout(profile_group)

        self.profile_name_edit = QLineEdit()
        profile_layout.addRow("Profile Name:", self.profile_name_edit)

        path_row = QHBoxLayout()
        self.profile_path_edit = QLineEdit()
        self.profile_path_edit.setPlaceholderText("Auto-detected or choose manually")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_profile)
        path_row.addWidget(self.profile_path_edit)
        path_row.addWidget(browse_btn)
        profile_layout.addRow("Profile Path:", path_row)

        layout.addWidget(profile_group)

        # Modrinth API group
        modrinth_group = QGroupBox("Modrinth API (Optional)")
        modrinth_layout = QFormLayout(modrinth_group)

        self.slug_edit = QLineEdit()
        self.slug_edit.setPlaceholderText("Leave empty unless you have a published modpack")
        modrinth_layout.addRow("Project Slug:", self.slug_edit)

        self.project_id_edit = QLineEdit()
        self.project_id_edit.setPlaceholderText("Leave empty unless you have a project ID")
        modrinth_layout.addRow("Project ID:", self.project_id_edit)

        layout.addWidget(modrinth_group)

        # Sync group
        sync_group = QGroupBox("Sync Settings")
        sync_layout = QVBoxLayout(sync_group)

        self.remove_orphans_cb = QCheckBox(
            "Remove orphaned files (files not in the remote manifest)"
        )
        sync_layout.addWidget(self.remove_orphans_cb)

        self.check_on_start_cb = QCheckBox("Check for updates on launch")
        sync_layout.addWidget(self.check_on_start_cb)

        preserve_label = QLabel("Preserved paths (one per line):")
        sync_layout.addWidget(preserve_label)

        self.preserve_edit = QTextEdit()
        self.preserve_edit.setMaximumHeight(120)
        sync_layout.addWidget(self.preserve_edit)

        reset_preserve_btn = QPushButton("Reset to Defaults")
        reset_preserve_btn.clicked.connect(self._reset_preserve_paths)
        sync_layout.addWidget(reset_preserve_btn)

        layout.addWidget(sync_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _load_values(self) -> None:
        self.url_edit.setText(self.config.remote_base_url)
        self.profile_name_edit.setText(self.config.profile_name)
        self.profile_path_edit.setText(self.config.profile_path)
        self.slug_edit.setText(self.config.modrinth_project_slug or "")
        self.project_id_edit.setText(self.config.modrinth_project_id or "")
        self.remove_orphans_cb.setChecked(self.config.remove_orphans)
        self.check_on_start_cb.setChecked(self.config.check_updates_on_start)
        self.preserve_edit.setPlainText("\n".join(self.config.preserve_paths))

    def _browse_profile(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Modrinth Profile Folder"
        )
        if folder:
            self.profile_path_edit.setText(folder)

    def _reset_preserve_paths(self) -> None:
        self.preserve_edit.setPlainText("\n".join(DEFAULT_PRESERVE_PATHS))

    def _save(self) -> None:
        self.config.remote_base_url = self.url_edit.text().strip()
        self.config.profile_name = self.profile_name_edit.text().strip() or "survival"
        self.config.profile_path = self.profile_path_edit.text().strip()
        self.config.modrinth_project_slug = self.slug_edit.text().strip() or None
        self.config.modrinth_project_id = self.project_id_edit.text().strip() or None
        self.config.remove_orphans = self.remove_orphans_cb.isChecked()
        self.config.check_updates_on_start = self.check_on_start_cb.isChecked()

        preserve_text = self.preserve_edit.toPlainText().strip()
        if preserve_text:
            self.config.preserve_paths = [
                line.strip() for line in preserve_text.splitlines() if line.strip()
            ]
        else:
            self.config.preserve_paths = list(DEFAULT_PRESERVE_PATHS)

        self.config.save()
        self.accept()
