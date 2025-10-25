"""
Gameboy Emulator - Configuration Settings
"""

import os


class Config:
    """Configuration class for the Gameboy emulator."""

    # Display settings
    DISPLAY_WIDTH = 160
    DISPLAY_HEIGHT = 144
    SCALE_FACTOR = 3
    WINDOW_WIDTH = DISPLAY_WIDTH * SCALE_FACTOR
    WINDOW_HEIGHT = DISPLAY_HEIGHT * SCALE_FACTOR

    # CPU settings
    CPU_CLOCK_SPEED = 4194304  # 4.19 MHz
    FRAME_RATE = 60

    # Memory settings
    ROM_BANK_SIZE = 0x4000  # 16KB
    RAM_BANK_SIZE = 0x2000  # 8KB
    VRAM_SIZE = 0x2000      # 8KB
    OAM_SIZE = 0xA0         # 160 bytes
    HRAM_SIZE = 0x7F        # 127 bytes

    # File paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ROMS_DIR = os.path.join(BASE_DIR, "roms")
    SAVES_DIR = os.path.join(BASE_DIR, "saves")

    # Emulation settings
    ENABLE_AUDIO = True
    ENABLE_DEBUG = False
    MAX_FPS = 60

    # Color palette (original Gameboy green shades)
    PALETTE = [
        (155, 188, 15),   # Light green (0)
        (139, 172, 15),   # Light green (1)
        (48, 98, 48),     # Dark green (2)
        (15, 56, 15)      # Dark green (3)
    ]

    @classmethod
    def ensure_directories(cls):
        """Ensure that necessary directories exist."""
        os.makedirs(cls.ROMS_DIR, exist_ok=True)
        os.makedirs(cls.SAVES_DIR, exist_ok=True)
