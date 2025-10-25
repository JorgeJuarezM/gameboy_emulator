# Test ROM for Gameboy Emulator
# This creates a simple pattern to verify the emulator is working

# Gameboy ROM header (256 bytes)
header = b'\x00' * 256

# Set entry point (0x0100) and Nintendo logo
nintendo_logo = (
    b'\xCE\xED\x66\x66\xCC\x0D\x00\x0B\x03\x73\x00\x83\x00\x0C\x00\x0D'
    b'\x00\x08\x11\x1F\x88\x89\x00\x0E\xDC\xCC\x6E\xE6\xDD\xDD\xD9\x99'
    b'\xBB\xBB\x67\x63\x6E\x0E\xEC\xCC\xDD\xDC\x99\x9F\xBB\xB9\x33\x3E'
)

# Create a simple program that:
# 1. Enables LCD
# 2. Sets up basic palette
# 3. Writes a pattern to VRAM
# 4. Infinite loop

program = b''
program += b'\x3E\x91'  # LD A, 0x91 (LCDC value with LCD enabled, BG enabled)
program += b'\xE0\x40'  # LDH (0xFF40), A (set LCDC)

program += b'\x3E\xFC'  # LD A, 0xFC (background palette)
program += b'\xE0\x47'  # LDH (0xFF47), A (set BGP)

# Fill VRAM with a simple pattern (6144 bytes for tile map)
for i in range(6144):
    program += b'\x01'

# Infinite loop
program += b'\x18\xFE'  # JR -2 (infinite loop)

# Combine everything
rom_data = header[:0x100] + nintendo_logo + header[0x134:0x150] + program
rom_data += b'\x00' * (32 * 1024 - len(rom_data))

# Write ROM file
with open('/Users/jorgejuarez/CascadeProjects/gameboy_emulator/roms/test.gb', 'wb') as f:
    f.write(rom_data)

print("Test ROM created successfully!")
