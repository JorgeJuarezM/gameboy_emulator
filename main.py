#!/usr/bin/env python3
"""
Gameboy Emulator - Main Entry Point
"""

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.emulator import GameboyEmulator


def main():
    """Main entry point of the Gameboy emulator."""
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create Qt application
    app = QApplication(sys.argv)

    # Create main window
    window = MainWindow()

    # Show the window
    window.show()

    # Start the Qt event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
