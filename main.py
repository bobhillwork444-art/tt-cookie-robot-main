#!/usr/bin/env python3
"""
Cookie Robot - Octo Browser Automation Tool
Main entry point for the application
"""

import logging
import os
import sys
from datetime import datetime  # noqa: F401  (kept if used elsewhere)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Import GUI at module import time so packagers (e.g., PyInstaller) reliably include it.
from gui.main_window import MainWindow


# Setup basic logging (console only by default)
# File logging is controlled by GUI setting "autosave_logs"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    logger.info("Starting Cookie Robot")

    # Change to script directory for relative paths
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Cookie Robot")
    app.setOrganizationName("CookieRobot")

    window = MainWindow()
    window.show()

    logger.info("Application started successfully")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
