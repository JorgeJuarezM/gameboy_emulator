"""
Main Window for Gameboy Emulator using PyQt5
Provides the main interface with menu, controls, and game display
"""

import sys
import os
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QAction,
    QFileDialog, QMessageBox, QMenuBar, QStatusBar, QLabel,
    QFrame, QPushButton, QGroupBox, QCheckBox, QSlider
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage, QPainter, QKeyEvent

from src.core.emulator import GameboyEmulator
from config import Config
import pygame


class EmulatorSignals(QObject):
    """Signals for emulator communication."""
    frame_updated = pyqtSignal()
    state_changed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)


class GameScreen(QWidget):
    """Widget that displays the Gameboy screen using Pygame integration."""

    def __init__(self):
        """Initialize the game screen."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Screen setup
        self.setMinimumSize(Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)
        self.setMaximumSize(Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)

        # Screen buffer (160x144 pixels, 4 shades of green)
        self.screen_buffer = [[0 for _ in range(Config.DISPLAY_WIDTH)]
                             for _ in range(Config.DISPLAY_HEIGHT)]

        # Initialize pygame if available
        self._init_pygame()

    def _init_pygame(self):
        """Initialize Pygame for rendering."""
        try:
            import pygame
            pygame.init()

            # Create pygame surface
            self.pygame_surface = pygame.Surface((Config.DISPLAY_WIDTH, Config.DISPLAY_HEIGHT))

            # Set up display (hidden, we'll render to surface)
            self.pygame_display = pygame.display.set_mode(
                (Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT), pygame.HIDDEN
            )

            self.logger.info("Pygame initialized for rendering")

        except ImportError:
            self.logger.warning("Pygame not available, using Qt rendering")
            self.pygame_surface = None

    def update_screen(self, screen_data: list):
        """Update the screen with new frame data."""
        self.logger.debug(f"GameScreen update_screen called with {len(screen_data)} lines")
        if len(screen_data) == Config.DISPLAY_HEIGHT:
            for y in range(Config.DISPLAY_HEIGHT):
                if len(screen_data[y]) == Config.DISPLAY_WIDTH:
                    self.screen_buffer[y] = screen_data[y][:]
                    self.logger.debug(f"Updated line {y} with {len(screen_data[y])} pixels")
        self.update()

    def paintEvent(self, event):
        """Paint the Gameboy screen."""
        self.logger.debug("GameScreen paintEvent called")
        painter = QPainter(self)

        # Use Qt rendering (more reliable)
        self._render_with_qt(painter)
        self.logger.debug("Painted using Qt rendering")

    def _render_with_pygame(self):
        """Render using Pygame."""
        if not self.pygame_surface:
            return

        # Clear surface
        self.pygame_surface.fill(Config.PALETTE[0])

        # Draw pixels
        for y in range(Config.DISPLAY_HEIGHT):
            for x in range(Config.DISPLAY_WIDTH):
                color_index = self.screen_buffer[y][x]
                color = Config.PALETTE[color_index % len(Config.PALETTE)]
                self.pygame_surface.set_at((x, y), color)

    def _render_with_qt(self, painter: QPainter):
        """Render using Qt."""
        # Draw each pixel
        pixels_drawn = 0
        for y in range(Config.DISPLAY_HEIGHT):
            for x in range(Config.DISPLAY_WIDTH):
                color_index = self.screen_buffer[y][x]
                color_tuple = Config.PALETTE[color_index % len(Config.PALETTE)]

                # Create QColor from RGB tuple
                from PyQt5.QtGui import QColor
                color = QColor(*color_tuple)

                # Draw pixel
                painter.fillRect(
                    x * Config.SCALE_FACTOR, y * Config.SCALE_FACTOR,
                    Config.SCALE_FACTOR, Config.SCALE_FACTOR,
                    color
                )
                pixels_drawn += 1

        self.logger.debug(f"Rendered {pixels_drawn} pixels using Qt")

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        # This will be connected to the emulator's input handling
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent):
        """Handle key release events."""
        # This will be connected to the emulator's input handling
        event.accept()


class ControlPanel(QWidget):
    """Control panel with emulator controls."""

    def __init__(self, main_window=None):
        """Initialize the control panel."""
        super().__init__()
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        self.setup_ui()

    def setup_ui(self):
        """Set up the control panel UI."""
        layout = QVBoxLayout(self)

        # Emulator controls
        controls_group = QGroupBox("Emulator Controls")
        controls_layout = QVBoxLayout(controls_group)

        # Play/Pause/Stop buttons
        buttons_layout = QHBoxLayout()

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._on_play_clicked)
        buttons_layout.addWidget(self.play_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.pause_button.setEnabled(False)
        buttons_layout.addWidget(self.pause_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)

        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self._on_reset_clicked)
        self.reset_button.setEnabled(False)
        buttons_layout.addWidget(self.reset_button)

        controls_layout.addLayout(buttons_layout)

        # Speed control
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(25)
        self.speed_slider.setMaximum(300)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickInterval(25)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        speed_layout.addWidget(self.speed_slider)

        self.speed_label = QLabel("100%")
        speed_layout.addWidget(self.speed_label)

        controls_layout.addLayout(speed_layout)

        layout.addWidget(controls_group)

        # Status information
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)

        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)

        self.frame_label = QLabel("Frames: 0")
        status_layout.addWidget(self.frame_label)

        self.cycle_label = QLabel("Cycles: 0")
        status_layout.addWidget(self.cycle_label)

        layout.addWidget(status_group)

        # Debug options
        debug_group = QGroupBox("Debug")
        debug_layout = QVBoxLayout(debug_group)

        self.debug_checkbox = QCheckBox("Enable Debug Mode")
        self.debug_checkbox.stateChanged.connect(self.on_debug_toggled)
        debug_layout.addWidget(self.debug_checkbox)

        layout.addWidget(debug_group)

        # Stretch to fill available space
        layout.addStretch()

    def _on_play_clicked(self):
        """Handle play button click - delegate to MainWindow."""
        if self.main_window:
            self.main_window.on_play()

    def _on_pause_clicked(self):
        """Handle pause button click - delegate to MainWindow."""
        if self.main_window:
            self.main_window.on_pause()

    def _on_stop_clicked(self):
        """Handle stop button click - delegate to MainWindow."""
        if self.main_window:
            self.main_window.on_stop()

    def _on_reset_clicked(self):
        """Handle reset button click - delegate to MainWindow."""
        if self.main_window:
            self.main_window.on_reset()

    def _on_test_clicked(self):
        """Handle test button click - delegate to MainWindow."""
        if self.main_window:
            self.main_window.on_test_clicked()

    def on_speed_changed(self, value: int):
        """Handle speed slider change."""
        self.speed_label.setText(f"{value}%")

    def on_debug_toggled(self, state: int):
        """Handle debug checkbox toggle."""
        # This will be connected to emulator debug mode
        pass

    def update_status(self, status: str):
        """Update status label."""
        self.status_label.setText(status)
        self.logger.debug(f"Updated status: {status}")

    def update_frame_count(self, frames: int):
        """Update frame counter."""
        self.frame_label.setText(f"Frames: {frames}")
        self.logger.debug(f"Updated frame count: {frames}")

    def update_cycle_count(self, cycles: int):
        """Update cycle counter."""
        self.cycle_label.setText(f"Cycles: {cycles:,}")
        self.logger.debug(f"Updated cycle count: {cycles}")


class MainWindow(QMainWindow):
    """Main window for the Gameboy emulator."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Emulator instance
        self.emulator = GameboyEmulator()
        self.signals = EmulatorSignals()

        # UI components
        self.game_screen = None
        self.control_panel = None

        # Emulation timer
        self.emulation_timer = QTimer()
        self.emulation_timer.timeout.connect(self.on_emulation_tick)
        self.logger.info(f"Emulation timer created and connected: {self.emulation_timer.isActive()}")

        # Setup UI
        self.setup_ui()
        self.setup_menus()
        self.setup_status_bar()

        # Connect signals
        self.connect_signals()

        # Connect emulator to UI
        self.emulator.set_frame_callback(self.on_frame_updated)

        self.logger.info("Main window initialized")

    def setup_ui(self):
        """Set up the main window UI."""
        self.setWindowTitle("Gameboy Emulator")
        self.setGeometry(100, 100, 1000, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Game screen (left side)
        self.game_screen = GameScreen()
        main_layout.addWidget(self.game_screen, 1)

        # Control panel (right side)
        self.control_panel = ControlPanel(self)
        main_layout.addWidget(self.control_panel, 0)

    def setup_menus(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        open_rom_action = QAction('Open ROM...', self)
        open_rom_action.setShortcut('Ctrl+O')
        open_rom_action.triggered.connect(self.on_open_rom)
        file_menu.addAction(open_rom_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Emulator menu
        emulator_menu = menubar.addMenu('Emulator')

        play_action = QAction('Play', self)
        play_action.setShortcut('F5')
        play_action.triggered.connect(self.on_play)
        emulator_menu.addAction(play_action)

        pause_action = QAction('Pause', self)
        pause_action.setShortcut('F6')
        pause_action.triggered.connect(self.on_pause)
        emulator_menu.addAction(pause_action)

        stop_action = QAction('Stop', self)
        stop_action.setShortcut('F7')
        stop_action.triggered.connect(self.on_stop)
        emulator_menu.addAction(stop_action)

        emulator_menu.addSeparator()

        reset_action = QAction('Reset', self)
        reset_action.setShortcut('F8')
        reset_action.triggered.connect(self.on_reset)
        emulator_menu.addAction(reset_action)

        # Debug menu
        debug_menu = menubar.addMenu('Debug')

        debug_action = QAction('Enable Debug', self)
        debug_action.setShortcut('F12')
        debug_action.setCheckable(True)
        debug_action.triggered.connect(self.on_debug_toggle)
        debug_menu.addAction(debug_action)

    def setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def connect_signals(self):
        """Connect internal signals."""
        self.signals.frame_updated.connect(self.on_frame_updated)
        self.signals.state_changed.connect(self.on_state_changed)
        self.signals.error_occurred.connect(self.on_error_occurred)

    def on_open_rom(self):
        """Handle open ROM file."""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Gameboy ROMs (*.gb *.rom)")
        file_dialog.setDirectory(Config.ROMS_DIR)

        if file_dialog.exec_():
            filenames = file_dialog.selectedFiles()
            if filenames:
                rom_path = filenames[0]
                self.load_rom(rom_path)

    def load_rom(self, rom_path: str):
        """Load a ROM file into the emulator."""
        try:
            success = self.emulator.load_rom(rom_path)
            if success:
                self.status_bar.showMessage(f"ROM loaded: {os.path.basename(rom_path)}")
                self.control_panel.update_status("ROM loaded")
                self.control_panel.reset_button.setEnabled(True)  # Enable reset button when ROM is loaded
            else:
                self.status_bar.showMessage("Failed to load ROM")
                self.control_panel.update_status("Failed to load ROM")

        except Exception as e:
            self.logger.error(f"Error loading ROM: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load ROM:\n{str(e)}")

    def on_play(self):
        """Handle play action."""
        self.logger.info(f"Play button pressed - Emulator running: {self.emulator.running}, paused: {self.emulator.paused}")

        if not self.emulator.running:
            self.logger.info("Starting emulator...")
            self.emulator.resume()

            # Update button states in ControlPanel
            self.control_panel.play_button.setEnabled(False)
            self.control_panel.pause_button.setEnabled(True)
            self.control_panel.stop_button.setEnabled(True)
            self.control_panel.reset_button.setEnabled(True)

            self.status_bar.showMessage("Emulator running")
            self.control_panel.update_status("Running")

            # Start emulation timer
            self.logger.info(f"Starting emulation timer (active: {self.emulation_timer.isActive()})...")
            self.emulation_timer.start(16)  # ~60 FPS
            self.logger.info(f"Emulation timer started (active: {self.emulation_timer.isActive()})")

            # Force initial state update
            state = self.emulator.get_state()
            self.signals.state_changed.emit(state)

            # Force immediate frame execution to test
            self.logger.info("Forcing immediate frame execution for testing...")
            self._force_frame_execution()

            # Verify emulator is running after 1 second
            QTimer.singleShot(1000, self._verify_emulation_running)
        else:
            self.logger.info("Emulator already running")

    def on_pause(self):
        """Handle pause action."""
        if self.emulator.running:
            self.emulator.pause()

            # Update button states
            self.control_panel.play_button.setEnabled(True)
            self.control_panel.pause_button.setEnabled(False)
            self.control_panel.stop_button.setEnabled(True)
            self.control_panel.reset_button.setEnabled(True)

            self.status_bar.showMessage("Emulator paused")
            self.control_panel.update_status("Paused")

            # Stop emulation timer
            self.emulation_timer.stop()

    def on_stop(self):
        """Handle stop action."""
        self.emulator.stop()

        # Update button states
        self.control_panel.play_button.setEnabled(True)
        self.control_panel.pause_button.setEnabled(False)
        self.control_panel.stop_button.setEnabled(False)
        self.control_panel.reset_button.setEnabled(True)

        self.status_bar.showMessage("Emulator stopped")
        self.control_panel.update_status("Stopped")

        # Stop emulation timer
        self.emulation_timer.stop()

    def on_reset(self):
        """Handle reset action."""
        self.emulator.reset()

        # Update button states
        self.control_panel.play_button.setEnabled(True)
        self.control_panel.pause_button.setEnabled(False)
        self.control_panel.stop_button.setEnabled(False)
        self.control_panel.reset_button.setEnabled(False)

        self.status_bar.showMessage("Emulator reset")
        self.control_panel.update_status("Reset")

    def on_debug_toggle(self):
        """Handle debug toggle."""
        # This will be implemented when debug system is ready
        self.status_bar.showMessage("Debug mode toggled")

    def on_emulation_tick(self):
        """Handle emulation timer tick."""
        self.logger.debug("Emulation tick started")
        try:
            # Run one frame
            self.logger.debug(f"Calling emulator.run_frame() - running: {self.emulator.running}, paused: {self.emulator.paused}")
            result = self.emulator.run_frame()
            self.logger.debug(f"run_frame() returned: {result}")

            # Update UI
            state = self.emulator.get_state()
            self.logger.debug(f"Emulator state: {state}")
            self.signals.state_changed.emit(state)

        except Exception as e:
            self.logger.error(f"Emulation error: {e}")
            self.signals.error_occurred.emit(str(e))
            self.emulation_timer.stop()

    def on_frame_updated(self, frame_buffer):
        """Handle frame update signal."""
        # Update game screen with new frame data
        if self.game_screen:
            self.game_screen.update_screen(frame_buffer)
            self.logger.debug(f"Frame updated in UI: {len(frame_buffer)} lines")

    def on_state_changed(self, state: dict):
        """Handle state change signal."""
        self.logger.debug(f"State changed: {state}")
        self.control_panel.update_frame_count(state.get('frame_count', 0))
        self.control_panel.update_cycle_count(state.get('cycle_count', 0))

    def on_error_occurred(self, error: str):
        """Handle error signal."""
        QMessageBox.critical(self, "Emulator Error", error)
        self.on_stop()

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for game controls."""
        # Gameboy controls mapping
        key = event.key()

        # Map Qt keys to input manager
        if key == Qt.Key_Z:  # A button
            self.emulator.input_manager.key_press('z')
        elif key == Qt.Key_X:  # B button
            self.emulator.input_manager.key_press('x')
        elif key == Qt.Key_Return:  # Start
            self.emulator.input_manager.key_press('return')
        elif key == Qt.Key_Shift:  # Select
            self.emulator.input_manager.key_press('shift')
        elif key == Qt.Key_Up:  # Up
            self.emulator.input_manager.key_press('up')
        elif key == Qt.Key_Down:  # Down
            self.emulator.input_manager.key_press('down')
        elif key == Qt.Key_Left:  # Left
            self.emulator.input_manager.key_press('left')
        elif key == Qt.Key_Right:  # Right
            self.emulator.input_manager.key_press('right')
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        """Handle key release events for game controls."""
        # Gameboy controls mapping
        key = event.key()

        # Map Qt keys to input manager
        if key == Qt.Key_Z:  # A button
            self.emulator.input_manager.key_release('z')
        elif key == Qt.Key_X:  # B button
            self.emulator.input_manager.key_release('x')
        elif key == Qt.Key_Return:  # Start
            self.emulator.input_manager.key_release('return')
        elif key == Qt.Key_Shift:  # Select
            self.emulator.input_manager.key_release('shift')
        elif key == Qt.Key_Up:  # Up
            self.emulator.input_manager.key_release('up')
        elif key == Qt.Key_Down:  # Down
            self.emulator.input_manager.key_release('down')
        elif key == Qt.Key_Left:  # Left
            self.emulator.input_manager.key_release('left')
        elif key == Qt.Key_Right:  # Right
            self.emulator.input_manager.key_release('right')
        else:
            super().keyReleaseEvent(event)

    def _force_frame_execution(self):
        """Force immediate frame execution for testing."""
        self.logger.info("Forcing frame execution...")
        try:
            # First try to run a frame
            result = self.emulator.run_frame()
            self.logger.info(f"Forced frame execution result: {result}")

            # Update UI immediately
            state = self.emulator.get_state()
            self.signals.state_changed.emit(state)
            self.logger.info(f"After forced execution - State: {state}")

            # If no frames were generated, try to force LCD on and generate test pattern
            if state['frame_count'] == 0:
                self.logger.warning("No frames generated, forcing LCD on and test pattern...")
                self.emulator.force_test_pattern()

                # Try running another frame
                result = self.emulator.run_frame()
                state = self.emulator.get_state()
                self.signals.state_changed.emit(state)
                self.logger.info(f"After test pattern - Result: {result}, State: {state}")

        except Exception as e:
            self.logger.error(f"Error in forced frame execution: {e}")

    def _verify_emulation_running(self):
        """Verify that emulation is running correctly."""
        state = self.emulator.get_state()
        self.logger.info(f"Emulation verification - Timer active: {self.emulation_timer.isActive()}, "
                        f"Emulator running: {state['running']}, Frame count: {state['frame_count']}, "
                        f"PC: {state['pc']}, SP: {state['sp']}")

        if state['frame_count'] == 0:
            self.logger.warning("No frames executed! Forcing frame execution...")
            # Force a frame execution
            self.emulator.run_frame()
            state = self.emulator.get_state()
            self.signals.state_changed.emit(state)
            self.logger.info(f"After forced execution - Frame count: {state['frame_count']}")

            # If still no frames, try test pattern
            if state['frame_count'] == 0:
                self.logger.warning("Still no frames! Forcing test pattern...")
                self.emulator.force_test_pattern()
                self.emulator.run_frame()
                state = self.emulator.get_state()
                self.signals.state_changed.emit(state)
                self.logger.info(f"After test pattern - Frame count: {state['frame_count']}")

    def on_test_clicked(self):
        """Handle test button click."""
        self.logger.info("Test button clicked - manual frame execution")
        try:
            # Force test pattern
            self.emulator.force_test_pattern()

            # Run a frame
            result = self.emulator.run_frame()
            self.logger.info(f"Test frame result: {result}")

            # Update UI
            state = self.emulator.get_state()
            self.signals.state_changed.emit(state)

            # Force screen update
            if self.game_screen:
                self.game_screen.update()

            self.logger.info(f"Test completed - State: {state}")

        except Exception as e:
            self.logger.error(f"Test error: {e}")
            QMessageBox.critical(self, "Test Error", f"Test failed:\n{str(e)}")
