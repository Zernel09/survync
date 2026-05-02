"""Stylesheet and theming constants for the Survync UI."""

DARK_THEME = """
QMainWindow {
    background-color: #1a1a2e;
}
QWidget {
    color: #e0e0e0;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}
QPushButton {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #0f3460;
    border-color: #533483;
}
QPushButton:pressed {
    background-color: #533483;
}
QPushButton:disabled {
    background-color: #2a2a3e;
    color: #666;
    border-color: #333;
}
QPushButton#playButton {
    background-color: #1b998b;
    color: #fff;
    font-size: 18px;
    font-weight: 700;
    padding: 14px 40px;
    border-radius: 8px;
    border: 2px solid #17a589;
    min-width: 200px;
}
QPushButton#playButton:hover {
    background-color: #17a589;
}
QPushButton#playButton:pressed {
    background-color: #148f7a;
}
QPushButton#playButton:disabled {
    background-color: #2a3a3e;
    border-color: #333;
    color: #666;
}
QLabel {
    color: #e0e0e0;
}
QLabel#titleLabel {
    font-size: 24px;
    font-weight: 700;
    color: #1b998b;
}
QLabel#statusLabel {
    font-size: 14px;
    color: #b0b0b0;
}
QLabel#versionLabel {
    font-size: 12px;
    color: #888;
}
QTextEdit {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 6px;
}
QProgressBar {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
    height: 22px;
}
QProgressBar::chunk {
    background-color: #1b998b;
    border-radius: 3px;
}
QLineEdit {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 4px;
    padding: 6px 10px;
}
QLineEdit:focus {
    border-color: #533483;
}
QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QGroupBox {
    border: 1px solid #0f3460;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QTabWidget::pane {
    border: 1px solid #0f3460;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #16213e;
    color: #b0b0b0;
    padding: 8px 16px;
    border: 1px solid #0f3460;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1a1a2e;
    color: #e0e0e0;
}
"""
