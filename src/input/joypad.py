"""
Input system for Gameboy Emulator
Handles joypad input and button mapping
"""

import logging
from typing import Dict, Set, Optional
from src.memory.mmu import Memory


class Joypad:
    """Gameboy joypad input handler."""

    def __init__(self, memory: Memory):
        """Initialize joypad."""
        self.logger = logging.getLogger(__name__)
        self.memory = memory

        # Button states
        self.buttons_pressed: Set[str] = set()
        self.directions_pressed: Set[str] = set()

        # Button mappings (keyboard keys to Gameboy buttons)
        self.key_mappings = {
            # Directions
            'up': {'up'},
            'down': {'down'},
            'left': {'left'},
            'right': {'right'},

            # Buttons
            'z': {'a'},
            'x': {'b'},
            'return': {'start'},
            'shift': {'select'}
        }

        # Reverse mapping (Gameboy buttons to keyboard keys)
        self.reverse_mappings = {}
        self._build_reverse_mappings()

        # Input modes (directions or buttons)
        self.select_directions = False
        self.select_buttons = False

        self.logger.info("Joypad initialized")

    def _build_reverse_mappings(self):
        """Build reverse key mappings."""
        for key, buttons in self.key_mappings.items():
            for button in buttons:
                if button not in self.reverse_mappings:
                    self.reverse_mappings[button] = set()
                self.reverse_mappings[button].add(key)

    def key_press(self, key: str):
        """Handle key press."""
        key = key.lower()

        if key in self.key_mappings:
            buttons = self.key_mappings[key]

            # Add to appropriate set
            for button in buttons:
                if button in ['up', 'down', 'left', 'right']:
                    self.directions_pressed.add(button)
                else:
                    self.buttons_pressed.add(button)

            self._update_joypad_register()

    def key_release(self, key: str):
        """Handle key release."""
        key = key.lower()

        if key in self.key_mappings:
            buttons = self.key_mappings[key]

            # Remove from appropriate set
            for button in buttons:
                if button in ['up', 'down', 'left', 'right']:
                    self.directions_pressed.discard(button)
                else:
                    self.buttons_pressed.discard(button)

            self._update_joypad_register()

    def _update_joypad_register(self):
        """Update the P1 joypad register."""
        p1 = 0xFF  # Default: all buttons released

        # Check if directions are selected
        if self.select_directions:
            if 'down' in self.directions_pressed:
                p1 &= ~0x08
            if 'up' in self.directions_pressed:
                p1 &= ~0x04
            if 'left' in self.directions_pressed:
                p1 &= ~0x02
            if 'right' in self.directions_pressed:
                p1 &= ~0x01

        # Check if buttons are selected
        if self.select_buttons:
            if 'start' in self.buttons_pressed:
                p1 &= ~0x08
            if 'select' in self.buttons_pressed:
                p1 &= ~0x04
            if 'b' in self.buttons_pressed:
                p1 &= ~0x02
            if 'a' in self.buttons_pressed:
                p1 &= ~0x01

        # Write to P1 register (but don't overwrite selection bits)
        current_p1 = self.memory.get_io_register(0xFF00)
        selection_bits = current_p1 & 0x30  # Preserve bits 4-5 (selection)
        self.memory.set_io_register(0xFF00, selection_bits | (p1 & 0x0F))

    def handle_register_write(self, value: int):
        """Handle write to P1 register (selection bits)."""
        # Update selection mode
        self.select_directions = not bool(value & 0x10)  # P14
        self.select_buttons = not bool(value & 0x20)     # P15

        # Update register with current state
        self._update_joypad_register()

    def handle_register_read(self) -> int:
        """Handle read from P1 register."""
        current_p1 = self.memory.get_io_register(0xFF00)
        self._update_joypad_register()
        return self.memory.get_io_register(0xFF00)

    def is_button_pressed(self, button: str) -> bool:
        """Check if a specific button is pressed."""
        if button in ['up', 'down', 'left', 'right']:
            return button in self.directions_pressed
        else:
            return button in self.buttons_pressed

    def get_pressed_buttons(self) -> Dict[str, Set[str]]:
        """Get currently pressed buttons."""
        return {
            'directions': self.directions_pressed.copy(),
            'buttons': self.buttons_pressed.copy()
        }

    def reset(self):
        """Reset joypad state."""
        self.buttons_pressed.clear()
        self.directions_pressed.clear()
        self._update_joypad_register()
        self.logger.info("Joypad reset")


class InputManager:
    """Manages all input devices and mappings."""

    def __init__(self, memory: Memory):
        """Initialize input manager."""
        self.logger = logging.getLogger(__name__)
        self.memory = memory

        # Input devices
        self.joypad = Joypad(memory)

        # Connected input devices
        self.devices = {
            'joypad': self.joypad
        }

        self.logger.info("Input manager initialized")

    def key_press(self, key: str):
        """Handle key press from UI."""
        self.joypad.key_press(key)

    def key_release(self, key: str):
        """Handle key release from UI."""
        self.joypad.key_release(key)

    def handle_io_write(self, address: int, value: int):
        """Handle I/O register write."""
        if address == 0xFF00:  # P1 - Joypad
            self.joypad.handle_register_write(value)

    def handle_io_read(self, address: int) -> int:
        """Handle I/O register read."""
        if address == 0xFF00:  # P1 - Joypad
            return self.joypad.handle_register_read()
        return 0xFF

    def get_input_state(self) -> dict:
        """Get current input state."""
        return {
            'joypad': self.joypad.get_pressed_buttons()
        }

    def reset(self):
        """Reset all input devices."""
        self.joypad.reset()
        self.logger.info("Input manager reset")
