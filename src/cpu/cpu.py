"""
CPU implementation for Gameboy Emulator
Sharp LR35902 (SM83) processor with registers and instruction decoding
"""

import logging
from typing import Optional, Dict, Any
from src.memory.mmu import Memory


class Registers:
    """CPU Registers for Gameboy."""

    def __init__(self):
        """Initialize CPU registers."""
        # 8-bit registers
        self.a = 0      # Accumulator
        self.f = 0      # Flags
        self.b = 0
        self.c = 0
        self.d = 0
        self.e = 0
        self.h = 0
        self.l = 0

        # 16-bit registers
        self.pc = 0     # Program Counter
        self.sp = 0     # Stack Pointer

        # Clock cycles
        self.cycles = 0

    @property
    def af(self) -> int:
        """Get AF register (16-bit)."""
        return (self.a << 8) | self.f

    @af.setter
    def af(self, value: int):
        """Set AF register (16-bit)."""
        self.a = (value >> 8) & 0xFF
        self.f = value & 0xFF

    @property
    def bc(self) -> int:
        """Get BC register (16-bit)."""
        return (self.b << 8) | self.c

    @bc.setter
    def bc(self, value: int):
        """Set BC register (16-bit)."""
        self.b = (value >> 8) & 0xFF
        self.c = value & 0xFF

    @property
    def de(self) -> int:
        """Get DE register (16-bit)."""
        return (self.d << 8) | self.e

    @de.setter
    def de(self, value: int):
        """Set DE register (16-bit)."""
        self.d = (value >> 8) & 0xFF
        self.e = value & 0xFF

    @property
    def hl(self) -> int:
        """Get HL register (16-bit)."""
        return (self.h << 8) | self.l

    @hl.setter
    def hl(self, value: int):
        """Set HL register (16-bit)."""
        self.h = (value >> 8) & 0xFF
        self.l = value & 0xFF

    # Flag properties
    @property
    def flag_z(self) -> bool:
        """Zero flag."""
        return bool(self.f & 0x80)

    @flag_z.setter
    def flag_z(self, value: bool):
        """Set zero flag."""
        if value:
            self.f |= 0x80
        else:
            self.f &= ~0x80

    @property
    def flag_n(self) -> bool:
        """Subtract flag."""
        return bool(self.f & 0x40)

    @flag_n.setter
    def flag_n(self, value: bool):
        """Set subtract flag."""
        if value:
            self.f |= 0x40
        else:
            self.f &= ~0x40

    @property
    def flag_h(self) -> bool:
        """Half-carry flag."""
        return bool(self.f & 0x20)

    @flag_h.setter
    def flag_h(self, value: bool):
        """Set half-carry flag."""
        if value:
            self.f |= 0x20
        else:
            self.f &= ~0x20

    @property
    def flag_c(self) -> bool:
        """Carry flag."""
        return bool(self.f & 0x10)

    @flag_c.setter
    def flag_c(self, value: bool):
        """Set carry flag."""
        if value:
            self.f |= 0x10
        else:
            self.f &= ~0x10

    def reset(self):
        """Reset all registers."""
        self.a = 0
        self.f = 0
        self.b = 0
        self.c = 0
        self.d = 0
        self.e = 0
        self.h = 0
        self.l = 0
        self.pc = 0
        self.sp = 0
        self.cycles = 0

    def __str__(self) -> str:
        """String representation of registers."""
        return (f"AF={self.af:04X} BC={self.bc:04X} DE={self.de:04X} "
                f"HL={self.hl:04X} SP={self.sp:04X} PC={self.pc04X} "
                f"Flags={self.f:02X}")


class CPU:
    """Gameboy CPU implementation."""

    def __init__(self, memory: Memory):
        """Initialize the CPU."""
        self.logger = logging.getLogger(__name__)
        self.memory = memory
        self.registers = Registers()

        # CPU state
        self.halted = False
        self.stopped = False
        self.ime = False  # Interrupt Master Enable

        # Instruction execution
        self.current_opcode = 0
        self.instruction_cycles = 0

        # Initialize opcode table
        self.opcodes = self._build_opcode_table()

        # Initialize CB prefix opcodes
        self.cb_opcodes = self._build_cb_opcode_table()

    def reset(self):
        """Reset the CPU."""
        self.registers.reset()
        self.halted = False
        self.stopped = False
        self.ime = False
        self.current_opcode = 0
        self.instruction_cycles = 0
        self.logger.info("CPU reset")

    def step(self) -> int:
        """Execute one CPU instruction."""
        if self.halted:
            return 4  # NOP cycles when halted

        # Fetch opcode
        self.current_opcode = self.memory.read_byte(self.registers.pc)

        # Execute instruction
        cycles = self._execute_instruction()

        # Update program counter
        self.registers.pc += self._get_instruction_length()
        self.registers.cycles += cycles

        return cycles

    def _execute_instruction(self) -> int:
        """Execute the current instruction."""
        opcode = self.current_opcode

        if opcode == 0xCB:
            # CB prefix instruction
            self.registers.pc += 1
            cb_opcode = self.memory.read_byte(self.registers.pc)
            return self._execute_cb_instruction(cb_opcode)
        else:
            # Regular instruction
            if opcode in self.opcodes:
                return self.opcodes[opcode]()
            else:
                self.logger.warning(f"Unknown opcode: 0x{opcode:02X}")
                return 4  # Default NOP cycles

    def _execute_cb_instruction(self, cb_opcode: int) -> int:
        """Execute CB prefix instruction."""
        if cb_opcode in self.cb_opcodes:
            return self.cb_opcodes[cb_opcode]()
        else:
            self.logger.warning(f"Unknown CB opcode: 0x{cb_opcode:02X}")
            return 8  # Default CB instruction cycles

    def _get_instruction_length(self) -> int:
        """Get the length of the current instruction."""
        opcode = self.current_opcode

        if opcode == 0xCB:
            return 2  # CB prefix + CB opcode
        elif opcode in [0xC4, 0xCC, 0xCD, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4]:  # 3-byte instructions
            return 3
        elif opcode in [0xC9, 0xD9]:  # RET
            return 1
        elif opcode in [0xC3, 0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA]:  # JP
            return 3
        elif opcode in [0x01, 0x11, 0x21, 0x31]:  # LD 16-bit
            return 3
        elif opcode in [0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36]:  # LD 8-bit
            return 2
        else:
            return 1  # Most instructions are 1 byte

    def _build_opcode_table(self) -> Dict[int, Any]:
        """Build the main opcode table."""
        opcodes = {}

        # NOP
        opcodes[0x00] = self._nop

        # LD instructions
        opcodes[0x01] = lambda: self._ld_bc_nn()
        opcodes[0x11] = lambda: self._ld_de_nn()
        opcodes[0x21] = lambda: self._ld_hl_nn()
        opcodes[0x31] = lambda: self._ld_sp_nn()

        # LD (HL), n
        opcodes[0x36] = lambda: self._ld_hl_n()

        # LD A, (HL)
        opcodes[0x7E] = lambda: self._ld_a_hl()

        # LD A, n
        opcodes[0x3E] = lambda: self._ld_a_n()

        # LD B, n
        opcodes[0x06] = lambda: self._ld_b_n()

        # LD C, n
        opcodes[0x0E] = lambda: self._ld_c_n()

        # LD D, n
        opcodes[0x16] = lambda: self._ld_d_n()

        # LD E, n
        opcodes[0x1E] = lambda: self._ld_e_n()

        # LD H, n
        opcodes[0x26] = lambda: self._ld_h_n()

        # LD L, n
        opcodes[0x2E] = lambda: self._ld_l_n()

        # INC instructions
        opcodes[0x03] = lambda: self._inc_bc()
        opcodes[0x13] = lambda: self._inc_de()
        opcodes[0x23] = lambda: self._inc_hl()
        opcodes[0x33] = lambda: self._inc_sp()

        # DEC instructions
        opcodes[0x0B] = lambda: self._dec_bc()
        opcodes[0x1B] = lambda: self._dec_de()
        opcodes[0x2B] = lambda: self._dec_hl()
        opcodes[0x3B] = lambda: self._dec_sp()

        # JP instructions
        opcodes[0xC3] = lambda: self._jp_nn()
        opcodes[0xC2] = lambda: self._jp_nz_nn()
        opcodes[0xCA] = lambda: self._jp_z_nn()
        opcodes[0xD2] = lambda: self._jp_nc_nn()
        opcodes[0xDA] = lambda: self._jp_c_nn()

        # CALL instructions
        opcodes[0xCD] = lambda: self._call_nn()

        # RET instructions
        opcodes[0xC9] = lambda: self._ret()

        # PUSH instructions
        opcodes[0xC5] = lambda: self._push_bc()
        opcodes[0xD5] = lambda: self._push_de()
        opcodes[0xE5] = lambda: self._push_hl()
        opcodes[0xF5] = lambda: self._push_af()

        # POP instructions
        opcodes[0xC1] = lambda: self._pop_bc()
        opcodes[0xD1] = lambda: self._pop_de()
        opcodes[0xE1] = lambda: self._pop_hl()
        opcodes[0xF1] = lambda: self._pop_af()

        # EI (Enable Interrupts)
        opcodes[0xFB] = lambda: self._ei()

        # DI (Disable Interrupts)
        opcodes[0xF3] = lambda: self._di()

        return opcodes

    def _build_cb_opcode_table(self) -> Dict[int, Any]:
        """Build the CB prefix opcode table."""
        cb_opcodes = {}

        # BIT instructions
        for reg in range(8):
            for bit in range(8):
                opcode = 0x40 + (reg * 8) + bit
                if reg == 0:  # B
                    cb_opcodes[opcode] = lambda b=bit: self._bit_b(b)
                elif reg == 1:  # C
                    cb_opcodes[opcode] = lambda b=bit: self._bit_c(b)
                elif reg == 2:  # D
                    cb_opcodes[opcode] = lambda b=bit: self._bit_d(b)
                elif reg == 3:  # E
                    cb_opcodes[opcode] = lambda b=bit: self._bit_e(b)
                elif reg == 4:  # H
                    cb_opcodes[opcode] = lambda b=bit: self._bit_h(b)
                elif reg == 5:  # L
                    cb_opcodes[opcode] = lambda b=bit: self._bit_l(b)
                elif reg == 6:  # (HL)
                    cb_opcodes[opcode] = lambda b=bit: self._bit_hl(b)
                elif reg == 7:  # A
                    cb_opcodes[opcode] = lambda b=bit: self._bit_a(b)

        return cb_opcodes

    # Instruction implementations
    def _nop(self) -> int:
        """NOP - No operation."""
        return 4

    def _ld_bc_nn(self) -> int:
        """LD BC, nn - Load 16-bit immediate into BC."""
        nn = self.memory.read_word(self.registers.pc + 1)
        self.registers.bc = nn
        return 12

    def _ld_de_nn(self) -> int:
        """LD DE, nn - Load 16-bit immediate into DE."""
        nn = self.memory.read_word(self.registers.pc + 1)
        self.registers.de = nn
        return 12

    def _ld_hl_nn(self) -> int:
        """LD HL, nn - Load 16-bit immediate into HL."""
        nn = self.memory.read_word(self.registers.pc + 1)
        self.registers.hl = nn
        return 12

    def _ld_sp_nn(self) -> int:
        """LD SP, nn - Load 16-bit immediate into SP."""
        nn = self.memory.read_word(self.registers.pc + 1)
        self.registers.sp = nn
        return 12

    def _ld_hl_n(self) -> int:
        """LD (HL), n - Load 8-bit immediate into (HL)."""
        n = self.memory.read_byte(self.registers.pc + 1)
        self.memory.write_byte(self.registers.hl, n)
        return 12

    def _ld_a_hl(self) -> int:
        """LD A, (HL) - Load (HL) into A."""
        self.registers.a = self.memory.read_byte(self.registers.hl)
        return 8

    def _ld_a_n(self) -> int:
        """LD A, n - Load 8-bit immediate into A."""
        n = self.memory.read_byte(self.registers.pc + 1)
        self.registers.a = n
        return 8

    def _ld_b_n(self) -> int:
        """LD B, n - Load 8-bit immediate into B."""
        n = self.memory.read_byte(self.registers.pc + 1)
        self.registers.b = n
        return 8

    def _ld_c_n(self) -> int:
        """LD C, n - Load 8-bit immediate into C."""
        n = self.memory.read_byte(self.registers.pc + 1)
        self.registers.c = n
        return 8

    def _ld_d_n(self) -> int:
        """LD D, n - Load 8-bit immediate into D."""
        n = self.memory.read_byte(self.registers.pc + 1)
        self.registers.d = n
        return 8

    def _ld_e_n(self) -> int:
        """LD E, n - Load 8-bit immediate into E."""
        n = self.memory.read_byte(self.registers.pc + 1)
        self.registers.e = n
        return 8

    def _ld_h_n(self) -> int:
        """LD H, n - Load 8-bit immediate into H."""
        n = self.memory.read_byte(self.registers.pc + 1)
        self.registers.h = n
        return 8

    def _ld_l_n(self) -> int:
        """LD L, n - Load 8-bit immediate into L."""
        n = self.memory.read_byte(self.registers.pc + 1)
        self.registers.l = n
        return 8

    def _inc_bc(self) -> int:
        """INC BC - Increment BC."""
        self.registers.bc += 1
        return 8

    def _inc_de(self) -> int:
        """INC DE - Increment DE."""
        self.registers.de += 1
        return 8

    def _inc_hl(self) -> int:
        """INC HL - Increment HL."""
        self.registers.hl += 1
        return 8

    def _inc_sp(self) -> int:
        """INC SP - Increment SP."""
        self.registers.sp += 1
        return 8

    def _dec_bc(self) -> int:
        """DEC BC - Decrement BC."""
        self.registers.bc -= 1
        return 8

    def _dec_de(self) -> int:
        """DEC DE - Decrement DE."""
        self.registers.de -= 1
        return 8

    def _dec_hl(self) -> int:
        """DEC HL - Decrement HL."""
        self.registers.hl -= 1
        return 8

    def _dec_sp(self) -> int:
        """DEC SP - Decrement SP."""
        self.registers.sp -= 1
        return 8

    def _jp_nn(self) -> int:
        """JP nn - Jump to 16-bit immediate address."""
        nn = self.memory.read_word(self.registers.pc + 1)
        self.registers.pc = nn
        return 16

    def _jp_nz_nn(self) -> int:
        """JP NZ, nn - Jump to 16-bit immediate if Z flag is 0."""
        nn = self.memory.read_word(self.registers.pc + 1)
        if not self.registers.flag_z:
            self.registers.pc = nn
            return 16
        return 12

    def _jp_z_nn(self) -> int:
        """JP Z, nn - Jump to 16-bit immediate if Z flag is 1."""
        nn = self.memory.read_word(self.registers.pc + 1)
        if self.registers.flag_z:
            self.registers.pc = nn
            return 16
        return 12

    def _jp_nc_nn(self) -> int:
        """JP NC, nn - Jump to 16-bit immediate if C flag is 0."""
        nn = self.memory.read_word(self.registers.pc + 1)
        if not self.registers.flag_c:
            self.registers.pc = nn
            return 16
        return 12

    def _jp_c_nn(self) -> int:
        """JP C, nn - Jump to 16-bit immediate if C flag is 1."""
        nn = self.memory.read_word(self.registers.pc + 1)
        if self.registers.flag_c:
            self.registers.pc = nn
            return 16
        return 12

    def _call_nn(self) -> int:
        """CALL nn - Call subroutine at 16-bit immediate address."""
        nn = self.memory.read_word(self.registers.pc + 1)
        # Push return address to stack
        self.registers.sp -= 2
        self.memory.write_word(self.registers.sp, self.registers.pc + 3)
        self.registers.pc = nn
        return 24

    def _ret(self) -> int:
        """RET - Return from subroutine."""
        ret_addr = self.memory.read_word(self.registers.sp)
        self.registers.sp += 2
        self.registers.pc = ret_addr
        return 16

    def _push_bc(self) -> int:
        """PUSH BC - Push BC to stack."""
        self.registers.sp -= 2
        self.memory.write_word(self.registers.sp, self.registers.bc)
        return 16

    def _push_de(self) -> int:
        """PUSH DE - Push DE to stack."""
        self.registers.sp -= 2
        self.memory.write_word(self.registers.sp, self.registers.de)
        return 16

    def _push_hl(self) -> int:
        """PUSH HL - Push HL to stack."""
        self.registers.sp -= 2
        self.memory.write_word(self.registers.sp, self.registers.hl)
        return 16

    def _push_af(self) -> int:
        """PUSH AF - Push AF to stack."""
        self.registers.sp -= 2
        self.memory.write_word(self.registers.sp, self.registers.af)
        return 16

    def _pop_bc(self) -> int:
        """POP BC - Pop BC from stack."""
        self.registers.bc = self.memory.read_word(self.registers.sp)
        self.registers.sp += 2
        return 12

    def _pop_de(self) -> int:
        """POP DE - Pop DE from stack."""
        self.registers.de = self.memory.read_word(self.registers.sp)
        self.registers.sp += 2
        return 12

    def _pop_hl(self) -> int:
        """POP HL - Pop HL from stack."""
        self.registers.hl = self.memory.read_word(self.registers.sp)
        self.registers.sp += 2
        return 12

    def _pop_af(self) -> int:
        """POP AF - Pop AF from stack."""
        self.registers.af = self.memory.read_word(self.registers.sp)
        self.registers.sp += 2
        return 12

    def _ei(self) -> int:
        """EI - Enable interrupts."""
        self.ime = True
        return 4

    def _di(self) -> int:
        """DI - Disable interrupts."""
        self.ime = False
        return 4

    # CB prefix instructions (bit operations)
    def _bit_b(self, bit: int) -> int:
        """BIT b, B - Test bit b in register B."""
        self.registers.flag_z = not bool(self.registers.b & (1 << bit))
        self.registers.flag_n = False
        self.registers.flag_h = True
        return 8

    def _bit_c(self, bit: int) -> int:
        """BIT b, C - Test bit b in register C."""
        self.registers.flag_z = not bool(self.registers.c & (1 << bit))
        self.registers.flag_n = False
        self.registers.flag_h = True
        return 8

    def _bit_d(self, bit: int) -> int:
        """BIT b, D - Test bit b in register D."""
        self.registers.flag_z = not bool(self.registers.d & (1 << bit))
        self.registers.flag_n = False
        self.registers.flag_h = True
        return 8

    def _bit_e(self, bit: int) -> int:
        """BIT b, E - Test bit b in register E."""
        self.registers.flag_z = not bool(self.registers.e & (1 << bit))
        self.registers.flag_n = False
        self.registers.flag_h = True
        return 8

    def _bit_h(self, bit: int) -> int:
        """BIT b, H - Test bit b in register H."""
        self.registers.flag_z = not bool(self.registers.h & (1 << bit))
        self.registers.flag_n = False
        self.registers.flag_h = True
        return 8

    def _bit_l(self, bit: int) -> int:
        """BIT b, L - Test bit b in register L."""
        self.registers.flag_z = not bool(self.registers.l & (1 << bit))
        self.registers.flag_n = False
        self.registers.flag_h = True
        return 8

    def _bit_hl(self, bit: int) -> int:
        """BIT b, (HL) - Test bit b in memory at (HL)."""
        value = self.memory.read_byte(self.registers.hl)
        self.registers.flag_z = not bool(value & (1 << bit))
        self.registers.flag_n = False
        self.registers.flag_h = True
        return 12

    def _bit_a(self, bit: int) -> int:
        """BIT b, A - Test bit b in register A."""
        self.registers.flag_z = not bool(self.registers.a & (1 << bit))
        self.registers.flag_n = False
        self.registers.flag_h = True
        return 8
