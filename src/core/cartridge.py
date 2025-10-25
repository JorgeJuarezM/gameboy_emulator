"""
Cartridge handling for Gameboy Emulator
Supports different MBC types and cartridge features
"""

import logging
import os
from typing import Optional, Dict, Any


class Cartridge:
    """Gameboy cartridge representation."""

    def __init__(self, rom_data: bytes):
        """Initialize cartridge with ROM data."""
        self.logger = logging.getLogger(__name__)
        self.rom_data = rom_data
        self.header = self._parse_header()

        # MBC state
        self.mbc_type = self.header.get('mbc_type', 'ROM_ONLY')
        self.rom_banks = self.header.get('rom_banks', 2)
        self.ram_banks = self.header.get('ram_banks', 0)
        self.ram_size = self.header.get('ram_size', 0)

        # Cartridge features
        self.has_battery = self.header.get('battery', False)
        self.has_timer = self.header.get('timer', False)
        self.has_rumble = self.header.get('rumble', False)

        self.logger.info(f"Cartridge initialized: {self.header.get('title', 'Unknown')}")

    def _parse_header(self) -> Dict[str, Any]:
        """Parse the cartridge header (0x100-0x14F)."""
        if len(self.rom_data) < 0x150:
            return {}

        header = {}

        # Title (0x134-0x143)
        title_bytes = self.rom_data[0x134:0x144]
        header['title'] = ''.join(chr(b) for b in title_bytes if b != 0).strip()

        # CGB flag (0x143)
        header['cgb_flag'] = self.rom_data[0x143]

        # New licensee code (0x144-0x145)
        header['new_licensee'] = self.rom_data[0x144:0x146]

        # SGB flag (0x146)
        header['sgb_flag'] = self.rom_data[0x146]

        # Cartridge type (0x147)
        cart_type = self.rom_data[0x147]
        header['cartridge_type'] = cart_type

        # MBC type mapping
        mbc_types = {
            0x00: 'ROM_ONLY',
            0x01: 'MBC1',
            0x02: 'MBC1+RAM',
            0x03: 'MBC1+RAM+BATTERY',
            0x05: 'MBC2',
            0x06: 'MBC2+BATTERY',
            0x0F: 'MBC3+TIMER+BATTERY',
            0x10: 'MBC3+TIMER+RAM+BATTERY',
            0x11: 'MBC3',
            0x12: 'MBC3+RAM',
            0x13: 'MBC3+RAM+BATTERY',
            0x19: 'MBC5',
            0x1A: 'MBC5+RAM',
            0x1B: 'MBC5+RAM+BATTERY',
            0x1C: 'MBC5+RUMBLE',
            0x1D: 'MBC5+RUMBLE+RAM',
            0x1E: 'MBC5+RUMBLE+RAM+BATTERY'
        }
        header['mbc_type'] = mbc_types.get(cart_type, 'UNKNOWN')

        # ROM size (0x148)
        rom_size_code = self.rom_data[0x148]
        rom_sizes = {
            0x00: 2, 0x01: 4, 0x02: 8, 0x03: 16, 0x04: 32,
            0x05: 64, 0x06: 128, 0x07: 256, 0x08: 512
        }
        header['rom_banks'] = rom_sizes.get(rom_size_code, 2)

        # RAM size (0x149)
        ram_size_code = self.rom_data[0x149]
        ram_sizes = {
            0x00: 0, 0x01: 1, 0x02: 1, 0x03: 4, 0x04: 16, 0x05: 8
        }
        header['ram_banks'] = ram_sizes.get(ram_size_code, 0)
        header['ram_size'] = header['ram_banks'] * 0x2000  # 8KB per bank

        # Destination code (0x14A)
        header['destination'] = 'Japanese' if self.rom_data[0x14A] == 0x00 else 'Non-Japanese'

        # Old licensee code (0x14B)
        header['old_licensee'] = self.rom_data[0x14B]

        # Mask ROM version (0x14C)
        header['version'] = self.rom_data[0x14C]

        # Header checksum (0x14D)
        header['header_checksum'] = self.rom_data[0x14D]

        # Global checksum (0x14E-0x14F)
        header['global_checksum'] = self.rom_data[0x14E:0x150]

        # Feature flags
        header['battery'] = cart_type in [0x03, 0x06, 0x0F, 0x10, 0x13, 0x1B, 0x1E]
        header['timer'] = cart_type in [0x0F, 0x10]
        header['rumble'] = cart_type in [0x1C, 0x1D, 0x1E]

        return header

    def validate_checksum(self) -> bool:
        """Validate the cartridge header checksum."""
        if len(self.rom_data) < 0x150:
            return False

        # Calculate header checksum
        checksum = 0
        for i in range(0x134, 0x14D):
            checksum = (checksum - self.rom_data[i] - 1) & 0xFF

        return checksum == self.header.get('header_checksum', 0)

    def get_rom_bank(self, bank_number: int) -> bytes:
        """Get a specific ROM bank."""
        if bank_number >= self.rom_banks:
            return b''

        start = bank_number * 0x4000
        end = start + 0x4000

        if end > len(self.rom_data):
            end = len(self.rom_data)

        return self.rom_data[start:end]

    def get_info(self) -> Dict[str, Any]:
        """Get cartridge information."""
        return {
            'title': self.header.get('title', 'Unknown'),
            'mbc_type': self.mbc_type,
            'rom_banks': self.rom_banks,
            'ram_banks': self.ram_banks,
            'ram_size': self.ram_size,
            'has_battery': self.has_battery,
            'has_timer': self.has_timer,
            'has_rumble': self.has_rumble,
            'cgb_supported': self.header.get('cgb_flag', 0) in [0x80, 0xC0],
            'sgb_supported': self.header.get('sgb_flag', 0) == 0x03,
            'version': self.header.get('version', 0),
            'valid_checksum': self.validate_checksum()
        }


class CartridgeManager:
    """Manages cartridge loading and validation."""

    def __init__(self):
        """Initialize cartridge manager."""
        self.logger = logging.getLogger(__name__)
        self.current_cartridge = None

    def load_cartridge(self, rom_path: str) -> Optional[Cartridge]:
        """Load a cartridge from file."""
        try:
            if not os.path.exists(rom_path):
                self.logger.error(f"ROM file not found: {rom_path}")
                return None

            with open(rom_path, 'rb') as f:
                rom_data = f.read()

            if len(rom_data) < 0x150:
                self.logger.error("ROM too small to contain valid header")
                return None

            self.current_cartridge = Cartridge(rom_data)
            info = self.current_cartridge.get_info()

            if not info['valid_checksum']:
                self.logger.warning("Cartridge header checksum is invalid")

            self.logger.info(f"Cartridge loaded: {info['title']}")
            return self.current_cartridge

        except Exception as e:
            self.logger.error(f"Failed to load cartridge: {e}")
            return None

    def get_current_cartridge(self) -> Optional[Cartridge]:
        """Get the currently loaded cartridge."""
        return self.current_cartridge

    def eject_cartridge(self):
        """Eject the current cartridge."""
        self.current_cartridge = None
        self.logger.info("Cartridge ejected")
