"""
Picture Processing Unit (PPU) for Gameboy Emulator
Handles graphics rendering, tiles, sprites, and LCD control
"""

import logging
from typing import List, Optional, Tuple
from src.memory.mmu import Memory
from config import Config


class PPU:
    """Gameboy Picture Processing Unit."""

    def __init__(self, memory: Memory):
        """Initialize the PPU."""
        self.logger = logging.getLogger(__name__)
        self.memory = memory

        # PPU state
        self.mode = 0  # LCD mode (0=HBlank, 1=VBlank, 2=OAM, 3=Transfer)
        self.mode_clock = 0
        self.line = 0  # Current scanline (LY)

        # Frame buffer (160x144 pixels, 2-bit color per pixel)
        self.frame_buffer = [[0 for _ in range(Config.DISPLAY_WIDTH)]
                           for _ in range(Config.DISPLAY_HEIGHT)]

        # Background scroll
        self.scroll_x = 0
        self.scroll_y = 0

        # Window position
        self.window_x = 0
        self.window_y = 0

        # Palettes
        self.bg_palette = [0, 1, 2, 3]  # Background palette
        self.obj_palette0 = [0, 1, 2, 3]  # Sprite palette 0
        self.obj_palette1 = [0, 1, 2, 3]  # Sprite palette 1

        # LCD control flags
        self.lcd_enabled = False
        self.window_enabled = False
        self.obj_enabled = False
        self.bg_enabled = False

        # VRAM banks (for CGB)
        self.vram_bank = 0

        # Sprite data
        self.oam = []  # Object Attribute Memory

        # Frame completion callback
        self.frame_callback = None

        self.logger.info("PPU initialized")

    def reset(self):
        """Reset the PPU."""
        self.mode = 0
        self.mode_clock = 0
        self.line = 0
        self.frame_buffer = [[0 for _ in range(Config.DISPLAY_WIDTH)]
                           for _ in range(Config.DISPLAY_HEIGHT)]
        self.scroll_x = 0
        self.scroll_y = 0
        self.window_x = 0
        self.window_y = 0
        self._update_control_flags()
        self.logger.info("PPU reset")

    def step(self, cycles: int):
        """Update PPU for given number of cycles."""
        # Update control flags from LCDC register
        self._update_control_flags()

        if not self.lcd_enabled:
            return

        self.mode_clock += cycles

        # Handle mode transitions
        if self.mode == 0:  # HBlank
            if self.mode_clock >= 204:
                self.mode_clock = 0
                self.line += 1

                if self.line == 144:
                    # Enter VBlank
                    self.mode = 1
                    self._request_vblank_interrupt()
                    if self.frame_callback:
                        self.frame_callback(self.frame_buffer)
                        self.logger.debug(f"Frame completed: {self.frame_callback}")
                else:
                    # Enter OAM scan
                    self.mode = 2

        elif self.mode == 1:  # VBlank
            if self.mode_clock >= 456:
                self.mode_clock = 0
                self.line += 1

                if self.line > 153:
                    # End of VBlank, start new frame
                    self.line = 0
                    self.mode = 2

        elif self.mode == 2:  # OAM scan
            if self.mode_clock >= 80:
                self.mode_clock = 0
                self.mode = 3  # Transfer

        elif self.mode == 3:  # Transfer
            if self.mode_clock >= 172:
                self.mode_clock = 0
                self.mode = 0  # HBlank

                # Render current scanline
                if self.line < 144:
                    self._render_scanline(self.line)

    def _update_control_flags(self):
        """Update control flags from LCDC register."""
        lcdc = self.memory.get_io_register(0xFF40)

        self.lcd_enabled = bool(lcdc & 0x80)
        self.window_enabled = bool(lcdc & 0x20)
        self.obj_enabled = bool(lcdc & 0x02)
        self.bg_enabled = bool(lcdc & 0x01)

    def _render_scanline(self, line: int):
        """Render a single scanline."""
        if not self.bg_enabled and not self.window_enabled:
            return

        # Update scroll positions
        self.scroll_x = self.memory.get_io_register(0xFF43)
        self.scroll_y = self.memory.get_io_register(0xFF42)
        self.window_x = self.memory.get_io_register(0xFF4B) - 7
        self.window_y = self.memory.get_io_register(0xFF4A)

        # Update palettes
        self._update_palettes()

        # Render background/window
        if self.bg_enabled:
            self._render_background_line(line)

        # Render window (if enabled and on window area)
        if self.window_enabled and line >= self.window_y:
            self._render_window_line(line)

        # Render sprites
        if self.obj_enabled:
            self._render_sprites_line(line)

    def _render_background_line(self, line: int):
        """Render background for a scanline."""
        # Calculate tile coordinates
        tile_y = (line + self.scroll_y) >> 3
        tile_y_offset = (line + self.scroll_y) & 7

        for x in range(Config.DISPLAY_WIDTH):
            tile_x = (x + self.scroll_x) >> 3
            tile_x_offset = (x + self.scroll_x) & 7

            # Get tile number from background map
            bg_map_base = 0x9800 if self.memory.get_io_register(0xFF40) & 0x08 else 0x9C00
            tile_number = self.memory.read_byte(bg_map_base + (tile_y << 5) + tile_x)

            # Handle tile data area (0x8000 or 0x8800)
            tile_data_base = 0x8000 if self.memory.get_io_register(0xFF40) & 0x10 else 0x8800

            if tile_data_base == 0x8800:
                # Signed tile numbers
                tile_number = (tile_number ^ 0x80) - 128

            # Get tile data address
            tile_address = tile_data_base + (tile_number << 4) + (tile_y_offset << 1)

            # Read tile data (2 bytes for 8 pixels)
            byte1 = self.memory.read_byte(tile_address)
            byte2 = self.memory.read_byte(tile_address + 1)

            # Extract pixel color (2 bits per pixel)
            bit_pos = 7 - tile_x_offset
            color_bit1 = (byte1 >> bit_pos) & 1
            color_bit2 = (byte2 >> bit_pos) & 1
            color_index = (color_bit2 << 1) | color_bit1

            # Apply background palette
            pixel_color = self.bg_palette[color_index]
            self.frame_buffer[line][x] = pixel_color

    def _render_window_line(self, line: int):
        """Render window for a scanline."""
        if not self.window_enabled or line < self.window_y:
            return

        window_tile_y = (line - self.window_y) >> 3

        for x in range(max(0, self.window_x), Config.DISPLAY_WIDTH):
            if x < self.window_x:
                continue

            window_tile_x = (x - self.window_x) >> 3
            tile_x_offset = (x - self.window_x) & 7
            tile_y_offset = (line - self.window_y) & 7

            # Get tile number from window map
            window_map_base = 0x9800 if self.memory.get_io_register(0xFF40) & 0x40 else 0x9C00
            tile_number = self.memory.read_byte(window_map_base + (window_tile_y << 5) + window_tile_x)

            # Get tile data address
            tile_data_base = 0x8000 if self.memory.get_io_register(0xFF40) & 0x10 else 0x8800

            if tile_data_base == 0x8800:
                tile_number = (tile_number ^ 0x80) - 128

            tile_address = tile_data_base + (tile_number << 4) + (tile_y_offset << 1)

            # Read tile data
            byte1 = self.memory.read_byte(tile_address)
            byte2 = self.memory.read_byte(tile_address + 1)

            # Extract pixel color
            bit_pos = 7 - tile_x_offset
            color_bit1 = (byte1 >> bit_pos) & 1
            color_bit2 = (byte2 >> bit_pos) & 1
            color_index = (color_bit2 << 1) | color_bit1

            # Apply background palette
            pixel_color = self.bg_palette[color_index]
            self.frame_buffer[line][x] = pixel_color

    def _render_sprites_line(self, line: int):
        """Render sprites for a scanline."""
        if not self.obj_enabled:
            return

        # Get sprite height (8 or 16 pixels)
        obj_size = 16 if self.memory.get_io_register(0xFF40) & 0x04 else 8

        # Find sprites on current scanline
        sprites_on_line = []

        for i in range(40):  # 40 sprites max
            sprite_y = self.memory.read_byte(0xFE00 + (i * 4)) - 16
            sprite_x = self.memory.read_byte(0xFE00 + (i * 4) + 1) - 8

            if line >= sprite_y and line < sprite_y + obj_size:
                sprites_on_line.append(i)

                # Only render first 10 sprites per line
                if len(sprites_on_line) >= 10:
                    break

        # Sort sprites by x coordinate (for priority)
        sprites_on_line.sort(key=lambda i: self.memory.read_byte(0xFE00 + (i * 4) + 1))

        # Render sprites
        for sprite_index in sprites_on_line:
            self._render_single_sprite(line, sprite_index)

    def _render_single_sprite(self, line: int, sprite_index: int):
        """Render a single sprite."""
        base_addr = 0xFE00 + (sprite_index * 4)

        sprite_y = self.memory.read_byte(base_addr) - 16
        sprite_x = self.memory.read_byte(base_addr + 1) - 8
        tile_number = self.memory.read_byte(base_addr + 2)
        attributes = self.memory.read_byte(base_addr + 3)

        # Check if sprite is on current scanline
        obj_size = 16 if self.memory.get_io_register(0xFF40) & 0x04 else 8
        if line < sprite_y or line >= sprite_y + obj_size:
            return

        # Handle vertical flip
        tile_y = line - sprite_y
        if attributes & 0x40:  # V flip
            tile_y = obj_size - 1 - tile_y

        # Get tile address
        if obj_size == 16:
            tile_address = 0x8000 + (tile_number & 0xFE) * 16 + (tile_y & 7) * 2
            if tile_y >= 8:
                tile_address += 16
        else:
            tile_address = 0x8000 + tile_number * 16 + tile_y * 2

        # Read tile data
        byte1 = self.memory.read_byte(tile_address)
        byte2 = self.memory.read_byte(tile_address + 1)

        # Handle horizontal flip
        for x in range(8):
            tile_x = x
            if attributes & 0x20:  # H flip
                tile_x = 7 - x

            # Extract pixel color
            bit_pos = 7 - tile_x
            color_bit1 = (byte1 >> bit_pos) & 1
            color_bit2 = (byte2 >> bit_pos) & 1
            color_index = (color_bit2 << 1) | color_bit1

            if color_index == 0:  # Transparent
                continue

            # Calculate screen position
            screen_x = sprite_x + x

            # Check bounds
            if screen_x < 0 or screen_x >= Config.DISPLAY_WIDTH:
                continue

            # Apply sprite palette
            if attributes & 0x10:  # Palette 1
                pixel_color = self.obj_palette1[color_index]
            else:  # Palette 0
                pixel_color = self.obj_palette0[color_index]

            # Check sprite priority
            if attributes & 0x80:  # Background priority
                if self.frame_buffer[line][screen_x] != 0:
                    continue

            # Render pixel
            self.frame_buffer[line][screen_x] = pixel_color

    def _update_palettes(self):
        """Update color palettes from memory."""
        # Background palette
        bgp = self.memory.get_io_register(0xFF47)
        self.bg_palette = [
            (bgp >> 0) & 3,
            (bgp >> 2) & 3,
            (bgp >> 4) & 3,
            (bgp >> 6) & 3
        ]

        # Sprite palette 0
        obp0 = self.memory.get_io_register(0xFF48)
        self.obj_palette0 = [
            (obp0 >> 0) & 3,
            (obp0 >> 2) & 3,
            (obp0 >> 4) & 3,
            (obp0 >> 6) & 3
        ]

        # Sprite palette 1
        obp1 = self.memory.get_io_register(0xFF49)
        self.obj_palette1 = [
            (obp1 >> 0) & 3,
            (obp1 >> 2) & 3,
            (obp1 >> 4) & 3,
            (obp1 >> 6) & 3
        ]

    def _request_vblank_interrupt(self):
        """Request VBlank interrupt."""
        # Set VBlank interrupt flag in IF register (0xFF0F)
        if_reg = self.memory.get_io_register(0x0F)
        self.memory.set_io_register(0x0F, if_reg | 0x01)  # VBlank bit

    def get_frame_buffer(self) -> List[List[int]]:
        """Get the current frame buffer."""
        return self.frame_buffer.copy()

    def get_lcd_status(self) -> dict:
        """Get current LCD status."""
        return {
            'mode': self.mode,
            'line': self.line,
            'lcdc': self.memory.get_io_register(0xFF40),
            'stat': self.memory.get_io_register(0xFF41),
            'scroll_x': self.scroll_x,
            'scroll_y': self.scroll_y,
            'window_x': self.window_x,
            'window_y': self.window_y
        }

    def set_frame_callback(self, callback):
        """Set callback function for when frame is complete."""
        self.frame_callback = callback
