"""
Memory Management Unit (MMU) for Gameboy Emulator
Handles all memory operations including ROM, RAM, VRAM, I/O registers, etc.
"""

import logging
from typing import Optional, List
from config import Config


class Memory:
    """Memory Management Unit for Gameboy."""

    def __init__(self):
        """Initialize the memory system."""
        self.logger = logging.getLogger(__name__)

        # Memory banks - expanded ROM support for larger cartridges
        self.rom = [0] * (2 * 1024 * 1024)  # 2MB ROM (supports up to MBC5)
        self.wram = [0] * (8 * 1024)  # 8KB Work RAM
        self.vram = [0] * (8 * 1024)  # 8KB Video RAM
        self.oam = [0] * 160         # 160 bytes Object Attribute Memory
        self.hram = [0] * 127        # 127 bytes High RAM
        # I/O registers (0xFF00-0xFF7F) + IE register (0xFFFF)
        self.io = [0] * 128          # I/O registers (0xFF00-0xFF7F)
        self.ie_register = 0x00      # Interrupt Enable register (0xFFFF)

        # Boot ROM (256 bytes)
        self.boot_rom = None
        self.boot_rom_enabled = True

        # Cartridge RAM (for games that need it)
        self.cart_ram = []
        self.cart_ram_enabled = False

        # Memory Bank Controller (MBC) state
        self.mbc_type = None
        self.rom_bank = 1
        self.ram_bank = 0
        self.ram_enabled = False

        # Initialize I/O registers with default values
        self._init_io_registers()

    def _init_io_registers(self):
        """Initialize I/O registers with default values."""
        # Joypad (P1)
        self.io[0x00] = 0xFF

        # Serial transfer (SB, SC)
        self.io[0x01] = 0x00  # SB
        self.io[0x02] = 0x7E  # SC

        # Timer (DIV, TIMA, TMA, TAC)
        self.io[0x04] = 0x00  # DIV
        self.io[0x05] = 0x00  # TIMA
        self.io[0x06] = 0x00  # TMA
        self.io[0x07] = 0xF8  # TAC

        # Interrupt flags and enable
        self.io[0x0F] = 0xE1  # IF
        # IE register is handled separately as self.ie_register

        # Audio registers
        self.io[0x10] = 0x80  # NR10
        self.io[0x11] = 0xBF  # NR11
        self.io[0x12] = 0xF3  # NR12
        self.io[0x13] = 0xFF  # NR13
        self.io[0x14] = 0xBF  # NR14
        # ... more audio registers

        # LCD Control and Status
        self.io[0x40] = 0x91  # LCDC
        self.io[0x41] = 0x00  # STAT
        self.io[0x42] = 0x00  # SCY
        self.io[0x43] = 0x00  # SCX
        self.io[0x44] = 0x00  # LY
        self.io[0x45] = 0x00  # LYC

        # Palettes
        self.io[0x47] = 0xFC  # BGP
        self.io[0x48] = 0xFF  # OBP0
        self.io[0x49] = 0xFF  # OBP1

        # Window positions
        self.io[0x4A] = 0x00  # WY
        self.io[0x4B] = 0x00  # WX

    def load_boot_rom(self, boot_rom_data: bytes):
        """Load the boot ROM."""
        if len(boot_rom_data) != 256:
            raise ValueError("Boot ROM must be exactly 256 bytes")

        self.boot_rom = list(boot_rom_data)
        self.boot_rom_enabled = True
        self.logger.info("Boot ROM loaded")

    def load_rom(self, rom_data: bytes):
        """Load a game ROM."""
        self.logger.info(f"Loading ROM with {len(rom_data)} bytes")
        if len(rom_data) < 0x8000:  # At least 32KB
            raise ValueError("ROM too small")

        # Copy entire ROM (up to 2MB)
        rom_size = min(len(rom_data), 2 * 1024 * 1024)
        self.logger.info(f"Copying {rom_size} bytes to ROM array of size {len(self.rom)}")

        try:
            for i in range(rom_size):
                self.rom[i] = rom_data[i]
            self.logger.info(f"Successfully copied ROM data")
        except Exception as e:
            self.logger.error(f"Error copying ROM data at index {i}: {e}")
            raise

        # Check cartridge header for MBC type
        self._detect_mbc_type(rom_data)

        self.logger.info(f"ROM loaded: {len(rom_data)} bytes")

    def _detect_mbc_type(self, rom_data: bytes):
        """Detect the Memory Bank Controller type from cartridge header."""
        if len(rom_data) < 0x147:
            return

        mbc_code = rom_data[0x147]

        if mbc_code == 0x00:
            self.mbc_type = "ROM_ONLY"
        elif mbc_code in [0x01, 0x02, 0x03]:
            self.mbc_type = "MBC1"
        elif mbc_code in [0x05, 0x06]:
            self.mbc_type = "MBC2"
        elif mbc_code in [0x0F, 0x10, 0x11, 0x12, 0x13]:
            self.mbc_type = "MBC3"
        elif mbc_code in [0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E]:
            self.mbc_type = "MBC5"
        else:
            self.mbc_type = "UNKNOWN"

        self.logger.info(f"Detected MBC type: {self.mbc_type}")

    def read_byte(self, address: int) -> int:
        """Read a byte from memory."""
        if address < 0x100 and self.boot_rom_enabled and self.boot_rom:
            # Boot ROM area
            return self.boot_rom[address]
        elif address < 0x4000:
            # ROM bank 0
            return self.rom[address]
        elif address < 0x8000:
            # ROM bank 1-NN (switchable)
            return self._read_rom_bank(address)
        elif address < 0xA000:
            # VRAM
            return self.vram[address - 0x8000]
        elif address < 0xC000:
            # Cartridge RAM (if available)
            return self._read_cart_ram(address)
        elif address < 0xE000:
            # Work RAM bank 0
            return self.wram[address - 0xC000]
        elif address < 0xFE00:
            # Echo RAM (mirror of C000-DDFF)
            return self.wram[address - 0xE000]
        elif address < 0xFEA0:
            # OAM
            return self.oam[address - 0xFE00]
        elif address < 0xFF00:
            # Unused area
            return 0xFF
        elif address < 0xFF80:
            # I/O registers
            return self.io[address - 0xFF00]
        elif address < 0xFFFF:
            # High RAM
            return self.hram[address - 0xFF80]
        elif address == 0xFFFF:
            # Interrupt Enable register
            return self.ie_register
        else:
            self.logger.warning(f"Reading from invalid address: 0x{address:04X}")
            return 0xFF

    def write_byte(self, address: int, value: int):
        """Write a byte to memory."""
        value &= 0xFF  # Ensure 8-bit

        if address < 0x2000:
            # RAM enable/disable for MBC1/MBC3
            self._handle_ram_enable(address, value)
        elif address < 0x4000:
            # ROM bank number (lower 5 bits)
            self._handle_rom_bank_change(address, value)
        elif address < 0x6000:
            # RAM bank number or upper ROM bank bits (MBC1)
            self._handle_ram_bank_change(address, value)
        elif address < 0x8000:
            # MBC1 mode select
            self._handle_mode_select(address, value)
        elif address < 0xA000:
            # VRAM
            self.vram[address - 0x8000] = value
        elif address < 0xC000:
            # Cartridge RAM
            self._write_cart_ram(address, value)
        elif address < 0xE000:
            # Work RAM bank 0
            self.wram[address - 0xC000] = value
        elif address < 0xFE00:
            # Echo RAM (mirror)
            self.wram[address - 0xE000] = value
        elif address < 0xFEA0:
            # OAM
            self.oam[address - 0xFE00] = value
        elif address < 0xFF00:
            # Unused area - ignore writes
            pass
        elif address < 0xFF80:
            # I/O registers
            self._write_io_register(address, value)
        elif address < 0xFFFF:
            # High RAM
            self.hram[address - 0xFF80] = value
        elif address == 0xFFFF:
            # Interrupt Enable register
            self.ie_register = value
        else:
            self.logger.warning(f"Writing to invalid address: 0x{address:04X} = 0x{value:02X}")

    def _read_rom_bank(self, address: int) -> int:
        """Read from switchable ROM bank."""
        if self.mbc_type == "ROM_ONLY":
            return self.rom[address] if address < len(self.rom) else 0xFF

        bank_offset = (self.rom_bank - 1) * 0x4000
        rom_address = bank_offset + (address - 0x4000)
        return self.rom[rom_address] if rom_address < len(self.rom) else 0xFF

    def _read_cart_ram(self, address: int) -> int:
        """Read from cartridge RAM."""
        if not self.cart_ram_enabled or not self.cart_ram:
            return 0xFF

        ram_address = (address - 0xA000) + (self.ram_bank * 0x2000)
        return self.cart_ram[ram_address] if ram_address < len(self.cart_ram) else 0xFF

    def _write_cart_ram(self, address: int, value: int):
        """Write to cartridge RAM."""
        if not self.cart_ram_enabled or not self.cart_ram:
            return

        ram_address = (address - 0xA000) + (self.ram_bank * 0x2000)
        if ram_address < len(self.cart_ram):
            self.cart_ram[ram_address] = value

    def _handle_ram_enable(self, address: int, value: int):
        """Handle RAM enable/disable for MBC."""
        if self.mbc_type in ["MBC1", "MBC3"]:
            self.ram_enabled = (value & 0x0F) == 0x0A
            if self.ram_enabled and not self.cart_ram:
                # Initialize cartridge RAM if needed
                ram_size = 0x2000  # Default 8KB
                self.cart_ram = [0] * ram_size

    def _handle_rom_bank_change(self, address: int, value: int):
        """Handle ROM bank switching."""
        if self.mbc_type in ["MBC1", "MBC2", "MBC3", "MBC5"]:
            bank = value & 0x1F
            if bank == 0:
                bank = 1
            self.rom_bank = bank

    def _handle_ram_bank_change(self, address: int, value: int):
        """Handle RAM bank switching."""
        if self.mbc_type == "MBC1":
            self.ram_bank = value & 0x03
        elif self.mbc_type == "MBC3":
            self.ram_bank = value & 0x03

    def _handle_mode_select(self, address: int, value: int):
        """Handle MBC1 mode selection."""
        if self.mbc_type == "MBC1":
            # Mode selection (simplified)
            pass

    def _write_io_register(self, address: int, value: int):
        """Write to I/O register with special handling."""
        io_offset = address - 0xFF00

        # Handle special registers that need immediate action
        if address == 0xFF50:
            # Boot ROM disable
            if value & 1:
                self.boot_rom_enabled = False
                self.logger.info("Boot ROM disabled")
        elif address == 0xFF00:
            # Joypad register - handled by input system
            pass
        elif address == 0xFF04:
            # DIV - always write 0
            self.io[io_offset] = 0
        elif address == 0xFF44:
            # LY - LCD Y coordinate - read only
            pass
        else:
            # Normal I/O register write
            self.io[io_offset] = value

    def read_word(self, address: int) -> int:
        """Read a 16-bit word from memory (little-endian)."""
        low = self.read_byte(address)
        high = self.read_byte(address + 1)
        return (high << 8) | low

    def write_word(self, address: int, value: int):
        """Write a 16-bit word to memory (little-endian)."""
        self.write_byte(address, value & 0xFF)
        self.write_byte(address + 1, (value >> 8) & 0xFF)

    def get_io_register(self, address: int) -> int:
        """Get I/O register value."""
        if 0xFF00 <= address <= 0xFF7F:
            value = self.io[address - 0xFF00]
            # Log important registers
            if address in [0xFF40, 0xFF44, 0xFF00, 0xFF0F]:
                self.logger.debug(f"Reading I/O register 0x{address:04X} = 0x{value:02X}")
            return value
        return 0

    def set_io_register(self, address: int, value: int):
        """Set I/O register value."""
        if 0xFF00 <= address <= 0xFF7F:
            self.io[address - 0xFF00] = value & 0xFF

    def reset(self):
        """Reset the memory system."""
        self.rom = [0] * (2 * 1024 * 1024)  # 2MB ROM (supports up to MBC5)
        self.wram = [0] * (8 * 1024)
        self.vram = [0] * (8 * 1024)
        self.oam = [0] * 160
        self.hram = [0] * 127
        self.io = [0] * 128          # I/O registers (0xFF00-0xFF7F)
        self.ie_register = 0x00      # Interrupt Enable register (0xFFFF)

        self.boot_rom = None
        self.boot_rom_enabled = True
        self.cart_ram = []
        self.cart_ram_enabled = False

        self.mbc_type = None
        self.rom_bank = 1
        self.ram_bank = 0
        self.ram_enabled = False

        self._init_io_registers()
        self.logger.info("Memory system reset")
