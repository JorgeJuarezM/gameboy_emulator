#!/usr/bin/env python3
"""
Test script for Gameboy Emulator
Tests basic functionality and components
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.emulator import GameboyEmulator
from src.memory.mmu import Memory
from src.cpu.cpu import CPU, Registers
from src.gpu.ppu import PPU
from src.apu.apu import APU
from src.input.joypad import InputManager


def test_memory():
    """Test memory system."""
    print("Testing Memory System...")
    memory = Memory()

    # Test basic read/write
    memory.write_byte(0xC000, 0x42)
    assert memory.read_byte(0xC000) == 0x42, "Basic memory read/write failed"

    # Test word operations
    memory.write_word(0xC000, 0x1234)
    assert memory.read_word(0xC000) == 0x1234, "Word memory operations failed"

    # Test I/O registers
    memory.set_io_register(0xFF40, 0x91)
    assert memory.get_io_register(0xFF40) == 0x91, "I/O register operations failed"

    print("✓ Memory system tests passed")


def test_cpu():
    """Test CPU functionality."""
    print("Testing CPU...")
    memory = Memory()
    cpu = CPU(memory)

    # Test registers
    cpu.registers.a = 0x42
    assert cpu.registers.a == 0x42, "Register A test failed"

    cpu.registers.bc = 0x1234
    assert cpu.registers.b == 0x12 and cpu.registers.c == 0x34, "BC register test failed"

    # Test flags
    cpu.registers.flag_z = True
    assert cpu.registers.flag_z == True, "Zero flag test failed"

    cpu.registers.flag_c = False
    assert cpu.registers.flag_c == False, "Carry flag test failed"

    print("✓ CPU tests passed")


def test_emulator():
    """Test basic emulator functionality."""
    print("Testing Emulator...")
    emulator = GameboyEmulator()

    # Test initialization
    assert emulator.memory is not None, "Memory not initialized"
    assert emulator.cpu is not None, "CPU not initialized"
    assert emulator.ppu is not None, "PPU not initialized"
    assert emulator.apu is not None, "APU not initialized"
    assert emulator.input_manager is not None, "Input manager not initialized"

    # Test reset
    emulator.reset()
    assert emulator.frame_count == 0, "Frame count not reset"
    assert emulator.cycle_count == 0, "Cycle count not reset"

    # Test state
    state = emulator.get_state()
    assert 'running' in state, "State missing running status"
    assert 'frame_count' in state, "State missing frame count"

    print("✓ Emulator tests passed")


def test_instructions():
    """Test basic CPU instructions."""
    print("Testing CPU Instructions...")
    memory = Memory()
    cpu = CPU(memory)

    # Load a simple program: LD A, 42
    memory.write_byte(0x0100, 0x3E)  # LD A, n
    memory.write_byte(0x0101, 0x42)  # 42

    # Set PC to start of program
    cpu.registers.pc = 0x0100

    # Execute instruction
    cycles = cpu.step()
    assert cycles > 0, "Instruction execution failed"
    assert cpu.registers.a == 0x42, f"Expected A=0x42, got A=0x{cpu.registers.a"02X"}"

    print("✓ Instruction tests passed")


def main():
    """Run all tests."""
    print("Gameboy Emulator - Test Suite")
    print("=" * 40)

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

    try:
        test_memory()
        test_cpu()
        test_emulator()
        test_instructions()

        print("\n🎉 All tests passed successfully!")
        print("\nThe Gameboy emulator is ready for use.")
        print("\nTo run the emulator:")
        print("1. python main.py")
        print("2. Load a ROM file (.gb)")
        print("3. Use the controls to play")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
