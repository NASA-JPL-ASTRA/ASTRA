"""
Core telemetry generator for rover simulation.
Handles telemetry channel logging and event logging with configurable sampling rates.
"""

import os
import csv
import time
from typing import List, Tuple, Dict, Any
import numpy as np


class TelemetryLogger:
    """Handles writing telemetry data to channel.log and event.log files."""
    
    def __init__(self, output_dir: str):
        """
        Initialize telemetry logger.
        
        Args:
            output_dir: Directory where log files will be written
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.channel_log_path = os.path.join(output_dir, "channel.log")
        self.event_log_path = os.path.join(output_dir, "event.log")
        
        self.channel_buffer = []
        self.event_buffer = []
    
    def log_channel(self, timestamp: float, channel: str, value: Any):
        """
        Log a channel telemetry point.
        
        Args:
            timestamp: Unix timestamp
            channel: Channel name in format 'component.name'
            value: Telemetry value
        """
        self.channel_buffer.append((timestamp, channel, value))
    
    def log_event(self, timestamp: float, evr_name: str, severity: str, message: str):
        """
        Log an EVR event.
        
        Args:
            timestamp: Unix timestamp
            evr_name: EVR name in format 'component.name'
            severity: One of: activity_hi, activity_lo, command, warning
            message: Human-readable event message
        """
        self.event_buffer.append((timestamp, evr_name, severity, message))
    
    def flush(self):
        """Write all buffered telemetry to disk."""
        # Write channel log (no header)
        with open(self.channel_log_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for timestamp, channel, value in sorted(self.channel_buffer):
                writer.writerow([timestamp, channel, value])
        
        # Write event log (no header)
        with open(self.event_log_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for timestamp, evr_name, severity, message in sorted(self.event_buffer):
                writer.writerow([timestamp, evr_name, severity, message])
        
        print(f"Wrote {len(self.channel_buffer)} channel samples to {self.channel_log_path}")
        print(f"Wrote {len(self.event_buffer)} events to {self.event_log_path}")


class RoverSimulator:
    """
    Simulates a 4-wheeled rover with telemetry generation.
    
    Telemetry channels:
    - motor.motor[1-4].speed (5 Hz) - RPM
    - motor.motor[1-4].current (10 Hz) - Amps
    - motor.motor[1-4].temperature (1 Hz) - Celsius
    - imu.accel_[x,y,z] (10 Hz) - m/s²
    - nav.position_[x,y,z] (1 Hz) - meters
    - system.fault_code (1 Hz) - hex string
    """
    
    def __init__(self, logger: TelemetryLogger, start_time: float = None):
        """
        Initialize rover simulator.
        
        Args:
            logger: TelemetryLogger instance for recording data
            start_time: Starting unix timestamp (default: current time)
        """
        self.logger = logger
        self.start_time = start_time if start_time is not None else time.time()
        self.current_time = self.start_time
        
        # Rover state
        self.motor_speeds = [0.0, 0.0, 0.0, 0.0]  # RPM
        self.motor_currents = [0.0, 0.0, 0.0, 0.0]  # Amps
        self.motor_temperatures = [25.0, 25.0, 25.0, 25.0]  # Celsius (ambient temp)
        self.motor_heat_accumulators = [0.0, 0.0, 0.0, 0.0]  # For thermal inertia
        
        self.position = [0.0, 0.0, 0.0]  # x, y, z in meters
        self.velocity = [0.0, 0.0, 0.0]  # x, y, z in m/s
        self.acceleration = [0.0, 0.0, -9.81]  # x, y, z in m/s² (with gravity)
        
        self.fault_code = "0x0000"
        
        # Sampling intervals
        self.last_sample_times = {
            'high_rate': self.start_time,  # 10 Hz
            'medium_rate': self.start_time,  # 5 Hz
            'low_rate': self.start_time,  # 1 Hz
        }
    
    def set_motor_speeds(self, speeds: List[float]):
        """Set target motor speeds in RPM."""
        self.motor_speeds = speeds.copy()
    
    def set_position(self, position: List[float]):
        """Set rover position in meters."""
        self.position = position.copy()
    
    def set_velocity(self, velocity: List[float]):
        """Set rover velocity in m/s."""
        self.velocity = velocity.copy()
    
    def set_acceleration(self, acceleration: List[float]):
        """Set rover acceleration in m/s² (including gravity)."""
        self.acceleration = acceleration.copy()
    
    def set_fault_code(self, fault_code: str):
        """Set system fault code (hex string like '0x0042')."""
        self.fault_code = fault_code
    
    def update(self, dt: float):
        """
        Update rover state and log telemetry based on sampling rates.
        
        Args:
            dt: Time step in seconds
        """
        self.current_time += dt
        
        # Update motor temperatures based on current draw
        for i in range(4):
            # Heat generation from current
            heat_rate = abs(self.motor_currents[i]) * 2.0  # Simplified heating model
            
            # Cooling towards ambient (25°C)
            cooling_rate = (self.motor_temperatures[i] - 25.0) * 0.1
            
            # Update temperature with thermal inertia
            self.motor_heat_accumulators[i] += (heat_rate - cooling_rate) * dt
            self.motor_temperatures[i] = 25.0 + self.motor_heat_accumulators[i]
        
        # Sample at different rates
        self._sample_high_rate()
        self._sample_medium_rate()
        self._sample_low_rate()
    
    def _sample_high_rate(self):
        """Sample 10 Hz channels: motor currents and IMU."""
        interval = 1.0 / 10.0
        if self.current_time - self.last_sample_times['high_rate'] >= interval - 1e-6:
            self.last_sample_times['high_rate'] = self.current_time
            
            # Motor currents (with noise)
            for i in range(4):
                # Base current from speed
                base_current = abs(self.motor_speeds[i]) / 100.0  # ~0.5A per 100 RPM
                noise = np.random.normal(0, 0.05)  # 50mA noise
                current = max(0, base_current + noise)
                self.motor_currents[i] = current
                
                self.logger.log_channel(
                    self.current_time,
                    f"motors.motor{i+1}_current",
                    round(current, 3)
                )
            
            # IMU accelerometer (with noise)
            for axis, value in zip(['x', 'y', 'z'], self.acceleration):
                noise = np.random.normal(0, 0.1)  # 0.1 m/s² noise
                self.logger.log_channel(
                    self.current_time,
                    f"imu.accel_{axis}",
                    round(value + noise, 3)
                )
    
    def _sample_medium_rate(self):
        """Sample 5 Hz channels: motor speeds."""
        interval = 1.0 / 5.0
        if self.current_time - self.last_sample_times['medium_rate'] >= interval - 1e-6:
            self.last_sample_times['medium_rate'] = self.current_time
            
            for i in range(4):
                self.logger.log_channel(
                    self.current_time,
                    f"motors.motor{i+1}_speed",
                    round(self.motor_speeds[i], 1)
                )
    
    def _sample_low_rate(self):
        """Sample 1 Hz channels: temperatures, position, fault code."""
        interval = 1.0
        if self.current_time - self.last_sample_times['low_rate'] >= interval - 1e-6:
            self.last_sample_times['low_rate'] = self.current_time
            
            # Motor temperatures
            for i in range(4):
                self.logger.log_channel(
                    self.current_time,
                    f"motors.motor{i+1}_temperature",
                    round(self.motor_temperatures[i], 1)
                )
            
            # Position
            for axis, value in zip(['x', 'y', 'z'], self.position):
                self.logger.log_channel(
                    self.current_time,
                    f"nav.position_{axis}",
                    round(value, 2)
                )
            
            # Fault code
            self.logger.log_channel(
                self.current_time,
                "system.fault_code",
                self.fault_code
            )
    
    def log_event(self, evr_name: str, severity: str, message: str):
        """
        Log an event at the current simulation time.
        
        Args:
            evr_name: EVR name in format 'component.name'
            severity: One of: activity_hi, activity_lo, command, warning
            message: Human-readable message
        """
        self.logger.log_event(self.current_time, evr_name, severity, message)
