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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler('emulator.log')  # Also log to file
        ]
    )

    # Set specific loggers to DEBUG level
    logging.getLogger('src.core.emulator').setLevel(logging.DEBUG)
    logging.getLogger('src.gpu.ppu').setLevel(logging.DEBUG)
    logging.getLogger('src.ui.main_window').setLevel(logging.DEBUG)
    logging.getLogger('src.cpu.cpu').setLevel(logging.DEBUG)

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
