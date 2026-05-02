"""Entry point for the Survync launcher."""

from __future__ import annotations

import logging
import sys

from survync import __app_name__, __version__
from survync.config import LauncherConfig, get_app_data_dir


def setup_logging() -> None:
    """Configure logging to both console and file."""
    log_dir = get_app_data_dir()
    log_file = log_dir / "survync.log"

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ],
    )


def main() -> None:
    """Launch the Survync application."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting %s v%s", __app_name__, __version__)

    # Load or create config
    config = LauncherConfig.load()

    # Start the Qt application
    from PySide6.QtWidgets import QApplication

    from survync.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
