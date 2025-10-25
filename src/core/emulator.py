"""
Gameboy Emulator Core
Coordinates all components: CPU, Memory, PPU, APU, Input, Interrupts
"""

import logging
import time
from typing import Optional
from src.memory.mmu import Memory
from src.cpu.cpu import CPU
from src.gpu.ppu import PPU
from src.apu.apu import APU
from src.input.joypad import InputManager
from config import Config
import os

class InterruptHandler:
    """Handles Gameboy interrupts."""

    def __init__(self, memory: Memory):
        """Initialize interrupt handler."""
        self.memory = memory
        self.logger = logging.getLogger(__name__)

        # Interrupt types
        self.interrupts = {
            'VBLANK': 0x40,
            'STAT': 0x48,
            'TIMER': 0x50,
            'SERIAL': 0x58,
            'JOYPAD': 0x60
        }

        # Interrupt flags
        self.pending_interrupts = 0

    def request_interrupt(self, interrupt_type: str):
        """Request an interrupt."""
        if interrupt_type in self.interrupts:
            bit = (self.interrupts[interrupt_type] - 0x40) // 8
            self.memory.io[0x0F] |= (1 << bit)
            self.logger.debug(f"Interrupt requested: {interrupt_type}")

    def clear_interrupt(self, interrupt_type: str):
        """Clear an interrupt flag."""
        if interrupt_type in self.interrupts:
            bit = (self.interrupts[interrupt_type] - 0x40) // 8
            self.memory.io[0x0F] &= ~(1 << bit)

    def get_enabled_interrupts(self) -> int:
        """Get enabled interrupts from IE register."""
        return self.memory.io[0xFF]

    def get_interrupt_flags(self) -> int:
        """Get interrupt flags from IF register."""
        return self.memory.io[0x0F]

    def handle_interrupts(self, cpu: CPU) -> bool:
        """Handle pending interrupts if IME is enabled."""
        if not cpu.ime:
            return False

        ie = self.get_enabled_interrupts()
        iflags = self.get_interrupt_flags()

        # Check for interrupts (priority order)
        for name, addr in self.interrupts.items():
            bit = (addr - 0x40) // 8
            if (ie & (1 << bit)) and (iflags & (1 << bit)):
                # Execute interrupt
                self._execute_interrupt(cpu, addr)
                return True

        return False

    def _execute_interrupt(self, cpu: CPU, address: int):
        """Execute an interrupt routine."""
        # Disable interrupts
        cpu.ime = False

        # Clear the interrupt flag
        bit = (address - 0x40) // 8
        self.memory.io[0x0F] &= ~(1 << bit)

        # Push current PC to stack
        cpu.registers.sp -= 2
        self.memory.write_word(cpu.registers.sp, cpu.registers.pc)

        # Jump to interrupt handler
        cpu.registers.pc = address

        self.logger.debug(f"Interrupt executed: 0x{address:04X}")


class Timer:
    """Gameboy internal timer."""

    def __init__(self, memory: Memory, interrupt_handler: InterruptHandler):
        """Initialize timer."""
        self.memory = memory
        self.interrupt_handler = interrupt_handler
        self.logger = logging.getLogger(__name__)

        # Timer counters
        self.div_counter = 0
        self.tima_counter = 0

        # Timer enabled
        self.enabled = False

    def step(self, cycles: int):
        """Update timer for given cycles."""
        # DIV register (always increments)
        self.div_counter += cycles
        if self.div_counter >= 256:  # 16384 Hz / 64
            self.div_counter -= 256
            self.memory.io[0x04] = (self.memory.io[0x04] + 1) & 0xFF

        # TIMA register (if timer enabled)
        if self._is_timer_enabled():
            self.tima_counter += cycles
            clock_select = self.memory.io[0x07] & 0x03

            # Timer frequencies based on TAC bits 0-1
            frequencies = [1024, 16, 64, 256]  # Hz
            threshold = 4194304 // frequencies[clock_select]

            if self.tima_counter >= threshold:
                self.tima_counter -= threshold
                self._increment_tima()

    def _is_timer_enabled(self) -> bool:
        """Check if timer is enabled."""
        return bool(self.memory.io[0x07] & 0x04)

    def _increment_tima(self):
        """Increment TIMA and handle overflow."""
        tima = self.memory.io[0x05]
        if tima == 0xFF:
            # Overflow - set to TMA and request interrupt
            self.memory.io[0x05] = self.memory.io[0x06]  # TMA
            self.interrupt_handler.request_interrupt('TIMER')
        else:
            self.memory.io[0x05] = tima + 1


class GameboyEmulator:
    """Main Gameboy emulator class."""

    def __init__(self):
        """Initialize the Gameboy emulator."""
        self.logger = logging.getLogger(__name__)

        # Core components
        self.memory = Memory()
        self.cpu = CPU(self.memory)
        self.ppu = PPU(self.memory)
        self.apu = APU(self.memory)
        self.input_manager = InputManager(self.memory)
        self.interrupt_handler = InterruptHandler(self.memory)
        self.timer = Timer(self.memory, self.interrupt_handler)

        # Emulation state
        self.running = False
        self.paused = False
        self.frame_count = 0
        self.cycle_count = 0

        # Frame timing
        self.last_frame_time = time.time()
        self.frame_duration = 1.0 / Config.FRAME_RATE

        # Frame callback for UI updates
        self.frame_callback = None

        # Connect PPU to frame callback
        self.ppu.set_frame_callback(self._on_frame_complete)

        self.logger.info("Gameboy emulator initialized")

    def load_rom(self, rom_path: str) -> bool:
        """Load a ROM file."""
        try:
            with open(rom_path, 'rb') as f:
                rom_data = f.read()

            self.memory.load_rom(rom_data)

            # Load boot ROM if available
            boot_rom_path = rom_path.replace('.gb', '_boot.gb')
            if os.path.exists(boot_rom_path):
                with open(boot_rom_path, 'rb') as f:
                    boot_data = f.read()
                self.memory.load_boot_rom(boot_data)

            # Initialize CPU state for ROM execution
            self.cpu.registers.pc = 0x0100  # Entry point after ROM header
            self.cpu.registers.sp = 0xFFFE  # Stack pointer at top of RAM
            self.cpu.ime = False            # Interrupts initially disabled

            self.logger.info(f"ROM loaded: {rom_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load ROM: {e}")
            return False

    def reset(self):
        """Reset the emulator."""
        self.memory.reset()
        self.cpu.reset()
        self.ppu.reset()
        self.apu.reset()
        self.input_manager.reset()
        self.frame_count = 0
        self.cycle_count = 0
        self.logger.info("Emulator reset")

    def run_frame(self) -> bool:
        """Run one frame (70224 cycles for original Gameboy)."""
        if not self.running:
            return False

        frame_cycles = 0
        target_cycles = 70224  # Cycles per frame

        while frame_cycles < target_cycles:
            if self.paused:
                time.sleep(0.01)  # Small delay when paused
                continue

            # Execute one instruction
            cycles = self.cpu.step()
            frame_cycles += cycles
            self.cycle_count += cycles

            # Update other components
            self.timer.step(cycles)
            self.ppu.step(cycles)
            self.apu.step(cycles)

            # Handle interrupts
            self.interrupt_handler.handle_interrupts(self.cpu)

            # Handle input
            self._handle_input()

            # Check for frame timing (VBlank interrupt)
            if frame_cycles >= target_cycles - 4560:  # Near end of frame
                self.interrupt_handler.request_interrupt('VBLANK')

        # Frame completed
        self.frame_count += 1

        # Debug logging
        if self.frame_count % 60 == 0:  # Log every second at 60 FPS
            self.logger.debug(f"Frame {self.frame_count}, PC: 0x{self.cpu.registers.pc:04X}, "
                            f"LCDC: 0x{self.memory.get_io_register(0xFF40):02X}, "
                            f"LY: {self.memory.get_io_register(0xFF44)}")

        # Frame rate limiting
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        if elapsed < self.frame_duration:
            time.sleep(self.frame_duration - elapsed)

        self.last_frame_time = current_time
        return True

    def _handle_input(self):
        """Handle input from joypad."""
        # Read P1 register to check if CPU is polling input
        p1 = self.memory.get_io_register(0xFF00)

        # If CPU is selecting directions or buttons, update register
        if not (p1 & 0x10) or not (p1 & 0x20):
            self.input_manager.handle_io_read(0xFF00)

    def _on_frame_complete(self, frame_buffer):
        """Handle frame completion from PPU."""
        if self.frame_callback:
            self.frame_callback(frame_buffer)

    def run(self, max_frames: Optional[int] = None):
        """Run the emulator for specified number of frames or indefinitely."""
        self.running = True
        frames_run = 0

        try:
            while self.running and (max_frames is None or frames_run < max_frames):
                if not self.run_frame():
                    break
                frames_run += 1

        except KeyboardInterrupt:
            self.logger.info("Emulator stopped by user")
        except Exception as e:
            self.logger.error(f"Emulator error: {e}")
        finally:
            self.running = False

    def pause(self):
        """Pause the emulator."""
        self.paused = True
        self.logger.info("Emulator paused")

    def resume(self):
        """Resume the emulator."""
        self.paused = False
        self.logger.info("Emulator resumed")

    def stop(self):
        """Stop the emulator."""
        self.running = False
        self.paused = False
        self.logger.info("Emulator stopped")

    def get_state(self) -> dict:
        """Get current emulator state."""
        return {
            'running': self.running,
            'paused': self.paused,
            'frame_count': self.frame_count,
            'cycle_count': self.cycle_count,
            'cpu_registers': str(self.cpu.registers),
            'ime': self.cpu.ime,
            'halted': self.cpu.halted
        }

    def save_state(self, filename: str):
        """Save emulator state to file."""
        import pickle
        state = {
            'memory': self.memory,
            'cpu': self.cpu,
            'ppu': self.ppu,
            'apu': self.apu,
            'frame_count': self.frame_count,
            'cycle_count': self.cycle_count
        }

        with open(filename, 'wb') as f:
            pickle.dump(state, f)

        self.logger.info(f"State saved: {filename}")

    def load_state(self, filename: str):
        """Load emulator state from file."""
        import pickle

        with open(filename, 'rb') as f:
            state = pickle.load(f)

        self.memory = state['memory']
        self.cpu = state['cpu']
        self.ppu = state['ppu']
        self.apu = state['apu']
        self.frame_count = state['frame_count']
        self.cycle_count = state['cycle_count']

        # Reconnect components
        self.ppu.memory = self.memory
        self.apu.memory = self.memory
        self.ppu.set_frame_callback(self._on_frame_complete)

        self.logger.info(f"State loaded: {filename}")

    def set_frame_callback(self, callback):
        """Set callback for frame updates."""
        self.frame_callback = callback
