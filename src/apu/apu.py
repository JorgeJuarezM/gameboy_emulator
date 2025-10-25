"""
Audio Processing Unit (APU) for Gameboy Emulator
Handles 4-channel audio system: 2 pulse, 1 wave, 1 noise
"""

import logging
import math
from typing import Optional, List
from src.memory.mmu import Memory


class AudioChannel:
    """Base class for audio channels."""

    def __init__(self, memory: Memory):
        """Initialize audio channel."""
        self.memory = memory
        self.enabled = False
        self.volume = 0
        self.output = 0

    def step(self, cycles: int) -> float:
        """Generate audio sample for given cycles."""
        return 0.0

    def trigger(self):
        """Trigger the channel (restart sound)."""
        pass


class PulseChannel(AudioChannel):
    """Pulse wave channel (Square 1 or Square 2)."""

    def __init__(self, memory: Memory, channel_num: int):
        """Initialize pulse channel."""
        super().__init__(memory)
        self.channel_num = channel_num

        # Channel registers (NR10-NR14 for channel 1, NR20-NR24 for channel 2)
        self.base_addr = 0xFF10 if channel_num == 1 else 0xFF15

        # Wave generation
        self.frequency = 0
        self.period = 0
        self.duty_cycle = 0
        self.duty_position = 0
        self.phase = 0

        # Volume envelope
        self.envelope_enabled = False
        self.envelope_direction = 0  # 0=decrease, 1=increase
        self.envelope_period = 0
        self.envelope_timer = 0
        self.envelope_volume = 0

        # Sweep (only for channel 1)
        if channel_num == 1:
            self.sweep_enabled = False
            self.sweep_period = 0
            self.sweep_direction = 0  # 0=decrease, 1=increase
            self.sweep_shift = 0
            self.sweep_timer = 0
            self.sweep_frequency = 0

    def step(self, cycles: int) -> float:
        """Generate pulse wave sample."""
        if not self.enabled:
            return 0.0

        # Update frequency sweep (channel 1 only)
        if self.channel_num == 1 and self.sweep_enabled:
            self._update_sweep()

        # Update volume envelope
        if self.envelope_enabled:
            self._update_envelope()

        # Generate wave
        self.phase += cycles

        if self.phase >= self.period:
            self.phase -= self.period
            self.duty_position = (self.duty_position + 1) % 8

        # Generate square wave based on duty cycle
        duty_patterns = [
            [0, 0, 0, 0, 0, 0, 0, 1],  # 12.5%
            [1, 0, 0, 0, 0, 0, 0, 1],  # 25%
            [1, 0, 0, 0, 0, 1, 1, 1],  # 50%
            [0, 1, 1, 1, 1, 1, 1, 0]   # 75%
        ]

        wave_value = duty_patterns[self.duty_cycle][self.duty_position]

        # Apply volume
        return (wave_value * self.volume) / 15.0

    def trigger(self):
        """Trigger pulse channel."""
        self.enabled = True

        # Load frequency
        freq_low = self.memory.read_byte(self.base_addr + 3)
        freq_high = self.memory.read_byte(self.base_addr + 4) & 7
        self.frequency = (freq_high << 8) | freq_low
        self.period = (2048 - self.frequency) * 4

        # Load duty cycle
        self.duty_cycle = (self.memory.read_byte(self.base_addr + 1) >> 6) & 3

        # Load volume and envelope
        self.volume = self.memory.read_byte(self.base_addr + 2) >> 4
        self.envelope_volume = self.volume

        envelope_data = self.memory.read_byte(self.base_addr + 2) & 0x0F
        self.envelope_period = envelope_data & 7
        self.envelope_direction = (envelope_data >> 3) & 1
        self.envelope_enabled = envelope_data > 0

        # Reset phase
        self.phase = 0
        self.duty_position = 0

        # Load sweep (channel 1 only)
        if self.channel_num == 1:
            sweep_data = self.memory.read_byte(self.base_addr)
            self.sweep_period = (sweep_data >> 4) & 7
            self.sweep_direction = (sweep_data >> 3) & 1
            self.sweep_shift = sweep_data & 7
            self.sweep_enabled = sweep_data > 0
            self.sweep_timer = self.sweep_period
            self.sweep_frequency = self.frequency

    def _update_sweep(self):
        """Update frequency sweep."""
        if self.sweep_timer > 0:
            self.sweep_timer -= 1

        if self.sweep_timer == 0:
            self.sweep_timer = self.sweep_period if self.sweep_period > 0 else 8

            if self.sweep_enabled and self.sweep_period > 0:
                new_frequency = self._calculate_sweep_frequency()

                if new_frequency <= 2047 and self.sweep_shift > 0:
                    self.sweep_frequency = new_frequency
                    self.frequency = new_frequency
                    self.period = (2048 - self.frequency) * 4

                    # Check for overflow
                    if self._calculate_sweep_frequency() > 2047:
                        self.enabled = False

    def _calculate_sweep_frequency(self) -> int:
        """Calculate new frequency after sweep."""
        delta = self.sweep_frequency >> self.sweep_shift

        if self.sweep_direction == 0:  # Decrease
            return self.sweep_frequency - delta
        else:  # Increase
            return self.sweep_frequency + delta

    def _update_envelope(self):
        """Update volume envelope."""
        if self.envelope_timer > 0:
            self.envelope_timer -= 1

        if self.envelope_timer == 0 and self.envelope_period > 0:
            self.envelope_timer = self.envelope_period

            if self.envelope_direction == 0:  # Decrease
                if self.envelope_volume > 0:
                    self.envelope_volume -= 1
            else:  # Increase
                if self.envelope_volume < 15:
                    self.envelope_volume += 1

            # Update actual volume
            self.volume = self.envelope_volume

            # Disable envelope when volume reaches limit
            if (self.envelope_direction == 0 and self.envelope_volume == 0) or \
               (self.envelope_direction == 1 and self.envelope_volume == 15):
                self.envelope_enabled = False


class WaveChannel(AudioChannel):
    """Wave channel with custom waveform."""

    def __init__(self, memory: Memory):
        """Initialize wave channel."""
        super().__init__(memory)
        self.base_addr = 0xFF1A

        # Wave data (32 4-bit samples)
        self.wave_data = [0] * 32

        # Wave generation
        self.frequency = 0
        self.period = 0
        self.wave_position = 0
        self.sample_position = 0

        # Volume shift
        self.volume_shift = 0

    def step(self, cycles: int) -> float:
        """Generate wave sample."""
        if not self.enabled:
            return 0.0

        self.wave_position += cycles

        if self.wave_position >= self.period:
            self.wave_position -= self.period
            self.sample_position = (self.sample_position + 1) % 32

        # Get sample from wave RAM
        sample = self.wave_data[self.sample_position]

        # Apply volume shift
        volume = 15 - self.volume_shift
        sample = (sample * volume) / 15.0

        return sample / 15.0

    def trigger(self):
        """Trigger wave channel."""
        self.enabled = True

        # Load frequency
        freq_low = self.memory.read_byte(self.base_addr + 3)
        freq_high = self.memory.read_byte(self.base_addr + 4) & 7
        self.frequency = (freq_high << 8) | freq_low
        self.period = (2048 - self.frequency) * 2

        # Load volume shift
        self.volume_shift = (self.memory.read_byte(self.base_addr + 2) >> 5) & 3

        # Load wave data
        for i in range(16):
            wave_byte = self.memory.read_byte(0xFF30 + i)
            self.wave_data[i * 2] = (wave_byte >> 4) & 0x0F
            self.wave_data[i * 2 + 1] = wave_byte & 0x0F

        # Reset position
        self.wave_position = 0
        self.sample_position = 0


class NoiseChannel(AudioChannel):
    """Noise channel with pseudo-random generation."""

    def __init__(self, memory: Memory):
        """Initialize noise channel."""
        super().__init__(memory)
        self.base_addr = 0xFF1F

        # Noise generation
        self.lfsr = 0x7FFF  # Linear Feedback Shift Register
        self.period = 0
        self.timer = 0

        # LFSR parameters
        self.clock_shift = 0
        self.lfsr_width = 0  # 7 or 15 bits
        self.clock_divisor = 0

    def step(self, cycles: int) -> float:
        """Generate noise sample."""
        if not self.enabled:
            return 0.0

        # Update envelope (same as pulse channels)
        if self.envelope_enabled:
            self._update_envelope()

        # Generate noise
        self.timer -= cycles

        if self.timer <= 0:
            self.timer += self.period

            # Generate new bit
            bit = (self.lfsr & 1) ^ ((self.lfsr >> 1) & 1)

            # Shift LFSR
            self.lfsr >>= 1
            self.lfsr |= bit << 14

            # XOR with bit 6 for 7-bit mode
            if self.lfsr_width == 7:
                self.lfsr &= ~(1 << 6)
                self.lfsr |= bit << 6

        # Output based on LFSR bit 0
        output = 1.0 if self.lfsr & 1 else 0.0
        return (output * self.volume) / 15.0

    def trigger(self):
        """Trigger noise channel."""
        self.enabled = True

        # Load parameters
        self.clock_shift = self.memory.read_byte(self.base_addr + 3) >> 4
        self.lfsr_width = 7 if self.memory.read_byte(self.base_addr + 3) & 8 else 15
        self.clock_divisor = self.memory.read_byte(self.base_addr + 3) & 7

        # Calculate period
        divisors = [8, 16, 32, 48, 64, 80, 96, 112]
        self.period = divisors[self.clock_divisor] << self.clock_shift

        # Load volume and envelope
        self.volume = self.memory.read_byte(self.base_addr + 2) >> 4
        self.envelope_volume = self.volume

        envelope_data = self.memory.read_byte(self.base_addr + 2) & 0x0F
        self.envelope_period = envelope_data & 7
        self.envelope_direction = (envelope_data >> 3) & 1
        self.envelope_enabled = envelope_data > 0

        # Reset LFSR
        self.lfsr = 0x7FFF

        # Reset timer
        self.timer = self.period

    def _update_envelope(self):
        """Update volume envelope (same as pulse channels)."""
        if self.envelope_timer > 0:
            self.envelope_timer -= 1

        if self.envelope_timer == 0 and self.envelope_period > 0:
            self.envelope_timer = self.envelope_period

            if self.envelope_direction == 0:  # Decrease
                if self.envelope_volume > 0:
                    self.envelope_volume -= 1
            else:  # Increase
                if self.envelope_volume < 15:
                    self.envelope_volume += 1

            self.volume = self.envelope_volume

            if (self.envelope_direction == 0 and self.envelope_volume == 0) or \
               (self.envelope_direction == 1 and self.envelope_volume == 15):
                self.envelope_enabled = False


class APU:
    """Audio Processing Unit for Gameboy."""

    def __init__(self, memory: Memory):
        """Initialize the APU."""
        self.logger = logging.getLogger(__name__)
        self.memory = memory

        # Audio channels
        self.pulse1 = PulseChannel(memory, 1)
        self.pulse2 = PulseChannel(memory, 2)
        self.wave = WaveChannel(memory)
        self.noise = NoiseChannel(memory)

        # Master audio control
        self.master_enable = True
        self.sound_output = [0.0, 0.0]  # Left and right channels

        # Audio buffer for mixing
        self.sample_rate = 44100
        self.buffer_size = 1024
        self.audio_buffer = []

        # Frame sequencer for envelope and sweep updates
        self.frame_sequencer = 0
        self.frame_timer = 0

        self.logger.info("APU initialized")

    def reset(self):
        """Reset the APU."""
        self.pulse1 = PulseChannel(self.memory, 1)
        self.pulse2 = PulseChannel(self.memory, 2)
        self.wave = WaveChannel(self.memory)
        self.noise = NoiseChannel(self.memory)

        self.frame_sequencer = 0
        self.frame_timer = 0
        self.audio_buffer = []

        self.logger.info("APU reset")

    def step(self, cycles: int):
        """Update APU for given number of cycles."""
        if not self.master_enable:
            return

        # Update frame sequencer (every 8192 cycles)
        self.frame_timer += cycles

        if self.frame_timer >= 8192:
            self.frame_timer -= 8192
            self._update_frame_sequencer()

        # Mix audio channels
        left_sample = 0.0
        right_sample = 0.0

        # Get samples from each channel
        pulse1_sample = self.pulse1.step(cycles)
        pulse2_sample = self.pulse2.step(cycles)
        wave_sample = self.wave.step(cycles)
        noise_sample = self.noise.step(cycles)

        # Mix channels (simplified - no stereo panning for now)
        total_sample = pulse1_sample + pulse2_sample + wave_sample + noise_sample
        total_sample = max(-1.0, min(1.0, total_sample / 4.0))  # Normalize and clip

        # Apply master volume
        master_volume = self._get_master_volume()
        total_sample *= master_volume

        # Store in buffer
        self.audio_buffer.append(total_sample)

        # Keep buffer size manageable
        if len(self.audio_buffer) > self.buffer_size:
            self.audio_buffer = self.audio_buffer[-self.buffer_size:]

    def _update_frame_sequencer(self):
        """Update frame sequencer for envelope and sweep timing."""
        self.frame_sequencer = (self.frame_sequencer + 1) % 8

        # Length counter and envelope updates happen at different steps
        if self.frame_sequencer in [0, 2, 4, 6]:
            # Length counter
            pass  # Will implement when length counters are added

        if self.frame_sequencer in [2, 6]:
            # Envelope update
            if self.pulse1.envelope_enabled:
                self.pulse1._update_envelope()
            if self.pulse2.envelope_enabled:
                self.pulse2._update_envelope()
            if self.noise.envelope_enabled:
                self.noise._update_envelope()

        if self.frame_sequencer == 7:
            # Sweep update (pulse 1 only)
            if self.pulse1.sweep_enabled:
                self.pulse1._update_sweep()

    def _get_master_volume(self) -> float:
        """Get master volume from NR50 and NR51."""
        nr50 = self.memory.get_io_register(0xFF24)
        nr51 = self.memory.get_io_register(0xFF25)

        # Extract master volume (0-7 for each channel)
        master_left = (nr50 >> 4) & 7
        master_right = nr50 & 7

        # For simplicity, return average volume
        return (master_left + master_right) / 14.0

    def trigger_channel(self, channel: str):
        """Trigger a specific audio channel."""
        if channel == 'pulse1':
            self.pulse1.trigger()
        elif channel == 'pulse2':
            self.pulse2.trigger()
        elif channel == 'wave':
            self.wave.trigger()
        elif channel == 'noise':
            self.noise.trigger()

    def get_audio_buffer(self) -> List[float]:
        """Get current audio buffer."""
        return self.audio_buffer.copy()

    def clear_audio_buffer(self):
        """Clear the audio buffer."""
        self.audio_buffer.clear()

    def set_master_enable(self, enable: bool):
        """Enable or disable master audio."""
        self.master_enable = enable

    def get_channel_info(self) -> dict:
        """Get information about all channels."""
        return {
            'pulse1': {
                'enabled': self.pulse1.enabled,
                'frequency': self.pulse1.frequency,
                'volume': self.pulse1.volume
            },
            'pulse2': {
                'enabled': self.pulse2.enabled,
                'frequency': self.pulse2.frequency,
                'volume': self.pulse2.volume
            },
            'wave': {
                'enabled': self.wave.enabled,
                'frequency': self.wave.frequency,
                'volume': self.wave.volume
            },
            'noise': {
                'enabled': self.noise.enabled,
                'volume': self.noise.volume
            },
            'master_enable': self.master_enable
        }
