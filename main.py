#!/usr/bin/env python3
"""
Cookie Robot - Octo Browser Automation Tool
Main entry point for the application
"""
import sys
import os
import logging
from datetime import datetime
from gui import MainWindow

# Setup basic logging (console only by default)
# File logging is controlled by GUI setting "autosave_logs"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    logger.info("Starting Cookie Robot")
    
    # Change to script directory for relative paths
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Cookie Robot")
    app.setOrganizationName("CookieRobot")
    
    from gui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    
    logger.info("Application started successfully")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
