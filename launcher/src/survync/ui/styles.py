"""Stylesheet and theming constants for the Survync UI."""

DARK_THEME = """
QMainWindow {
    background-color: #111315;
}
QWidget {
    color: #e7e5df;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}
QFrame#summaryPanel {
    background-color: #1a1d20;
    border: 1px solid #30363a;
    border-radius: 8px;
}
QPushButton {
    background-color: #24292d;
    color: #e7e5df;
    border: 1px solid #3a4146;
    border-radius: 6px;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #2d3439;
    border-color: #607068;
}
QPushButton:pressed {
    background-color: #1f6f5b;
}
QPushButton:disabled {
    background-color: #1b1d1f;
    color: #77736c;
    border-color: #292d30;
}
QPushButton#playButton {
    background-color: #2f8f6f;
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
    padding: 15px 52px;
    border-radius: 8px;
    border: 1px solid #46b58f;
    min-width: 230px;
}
QPushButton#playButton:hover {
    background-color: #37a681;
}
QPushButton#playButton:pressed {
    background-color: #24775d;
}
QPushButton#playButton:disabled {
    background-color: #263331;
    border-color: #333937;
    color: #8b8f8a;
}
QPushButton#playButton[upToDate="true"] {
    background-color: #1e3a2f;
    border-color: #2d6b4f;
    color: #7bcca0;
}
QPushButton#playButton[upToDate="true"]:hover {
    background-color: #244534;
    border-color: #3a8060;
}
QLabel {
    color: #e7e5df;
}
QLabel#titleLabel {
    font-size: 30px;
    font-weight: 800;
    color: #f0eee7;
}
QLabel#subtitleLabel {
    font-size: 13px;
    color: #aeb6b0;
}
QLabel#statusLabel {
    font-size: 14px;
    font-weight: 600;
    color: #d9c78f;
}
QLabel#metricLabel {
    font-size: 13px;
    font-weight: 700;
    color: #f0eee7;
}
QLabel#detailLabel {
    font-size: 12px;
    color: #aeb6b0;
}
QLabel#sectionLabel {
    font-size: 12px;
    font-weight: 700;
    color: #d0c8b8;
}
QTextEdit {
    background-color: #0b0d0e;
    color: #cfd3cf;
    border: 1px solid #2b3033;
    border-radius: 6px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 8px;
}
QProgressBar {
    background-color: #202427;
    border: 1px solid #353b3f;
    border-radius: 5px;
    text-align: center;
    color: #f0eee7;
    height: 22px;
}
QProgressBar::chunk {
    background-color: #2f8f6f;
    border-radius: 4px;
}
QLineEdit {
    background-color: #191c1f;
    color: #e7e5df;
    border: 1px solid #343a3f;
    border-radius: 5px;
    padding: 7px 10px;
}
QLineEdit:focus {
    border-color: #2f8f6f;
}
QCheckBox {
    color: #e7e5df;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QGroupBox {
    border: 1px solid #343a3f;
    border-radius: 7px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
"""
