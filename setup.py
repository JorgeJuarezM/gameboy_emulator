#!/usr/bin/env python3
"""
Setup script for Gameboy Emulator
Installs dependencies and sets up the project
"""

import os
import sys
import subprocess
import logging


def install_dependencies():
    """Install required Python packages."""
    print("Installing dependencies...")

    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_directories():
    """Create necessary directories."""
    print("Setting up directories...")

    directories = [
        'roms',
        'saves',
        'logs',
        'screenshots'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def create_sample_roms():
    """Create sample ROM files (if any)."""
    print("Checking for sample ROMs...")

    # This would be where you'd add any sample ROMs or test files
    # For now, just create a README in the roms directory
    roms_readme = os.path.join('roms', 'README.md')
    if not os.path.exists(roms_readme):
        with open(roms_readme, 'w') as f:
            f.write("""# ROMs Directory

Place your Gameboy ROM files (.gb) in this directory.

## Supported Formats
- .gb (Gameboy)
- .rom (Generic ROM format)

## Controls
- Arrow Keys: D-Pad
- Z: A Button
- X: B Button
- Enter: Start
- Shift: Select

## Note
ROM files should be legally obtained. This emulator is for educational purposes only.
""")
        print("✓ Created ROMs README")


def run_tests():
    """Run the test suite."""
    print("Running tests...")

    try:
        result = subprocess.run([sys.executable, 'test_emulator.py'],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("✓ All tests passed")
            return True
        else:
            print("❌ Tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("❌ Test file not found")
        return False


def main():
    """Run setup process."""
    print("Gameboy Emulator Setup")
    print("=" * 30)

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    success = True

    # Install dependencies
    if not install_dependencies():
        success = False

    # Setup directories
    setup_directories()

    # Create sample files
    create_sample_roms()

    # Run tests
    if not run_tests():
        success = False

    print("\n" + "=" * 30)
    if success:
        print("🎉 Setup completed successfully!")
        print("\nTo run the emulator:")
        print("  python main.py")
        print("\nTo run tests:")
        print("  python test_emulator.py")
        print("\nTo load a ROM:")
        print("  File -> Open ROM... and select a .gb file")
    else:
        print("❌ Setup completed with errors")
        print("Please check the error messages above")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
