# Rover Telemetry Generator

A Python-based telemetry data generator for a simulated 4-wheeled robotic rover system. This tool generates realistic telemetry data across various operational scenarios for testing, analysis, and demonstration purposes.

## Overview

This generator simulates a rover with:
- 4 independently controlled wheel motors
- 3-axis IMU (accelerometer)
- Temperature sensors on each motor
- Onboard navigation system (position tracking)
- Fault monitoring and reporting

The system generates two types of log files per test:
1. **channel.log** - High-frequency channelized telemetry data
2. **event.log** - Event records (EVRs) for significant system events

## Data Format

### channel.log

CSV format with no header. Three columns:

```
timestamp,channel_name,value
```

- **timestamp**: Unix timestamp (floating point seconds)
- **channel_name**: Channel identifier in `component.name` format (e.g., `motors.motor1_current`)
- **value**: Telemetry value (numeric or string)

Example:
```
1708875000.100,motors.motor1_current,0.523
1708875000.100,motors.motor2_current,0.518
1708875000.100,imu.accel_x,0.142
1708875000.100,imu.accel_y,0.089
1708875000.100,imu.accel_z,-9.876
```

### event.log

CSV format with no header. Four columns:

```
timestamp,event_name,severity,message
```

- **timestamp**: Unix timestamp (floating point seconds)
- **event_name**: Event identifier in format `component.name` (e.g., `drive.start_forward`)
- **severity**: One of: `activity_hi`, `activity_lo`, `command`, `warning`
- **message**: Human-readable event description

Example:
```
1708875000.000,drive.start_forward,activity_hi,Drive command received: forward at 0.5 m/s
1708875060.500,nav.bump_detected,activity_lo,Terrain bump detected at position y=30.2m
1708875120.000,motors.high_current_warning,warning,High motor current detected: 1.25A
```

## Telemetry Channels

### High-Rate Channels (10 Hz)
- `motors.motor1_current` through `motors.motor4_current` - Motor current draw in Amps
- `imu.accel_x`, `imu.accel_y`, `imu.accel_z` - Acceleration in m/s² (includes gravity)

### Medium-Rate Channels (5 Hz)
- `motors.motor1_speed` through `motors.motor4_speed` - Motor speed in RPM

### Low-Rate Channels (1 Hz)
- `motors.motor1_temperature` through `motors.motor4_temperature` - Motor temperature in °C
- `nav.position_x`, `nav.position_y`, `nav.position_z` - Rover position in meters
- `system.fault_code` - System fault code (hex string, e.g., "0x0000" or "0x0042")

## Test Scenarios

### Test 1: Straight Line with Bumps (5 minutes)
**Directory**: `output/test_1_straight_line/`

The rover drives forward in a straight line at constant velocity, encountering several bumps along the way.

**Key Behaviors:**
- Constant forward motion (0.5 m/s along y-axis)
- All four motors at nominal speed (50 RPM)
- Periodic terrain bumps cause IMU z-axis acceleration spikes
- Motor temperatures gradually increase from nominal operation
- Start/stop activity events

**Expected Data:**
- ~3,000 channel samples
- 6-8 event records
- Final position: y ≈ 150m

### Test 2: Steep Uphill Climb (7 minutes)
**Directory**: `output/test_2_uphill/`

The rover climbs a steep incline, showing increased motor load and thermal stress.

**Key Behaviors:**
- Forward and upward motion (climbing at 15 cm/s vertical)
- Elevated motor speeds (80 RPM) and currents (1.8x normal)
- Motor temperatures reach 60-70°C
- IMU shows pitch-induced acceleration changes
- Warning events for high current and temperature thresholds

**Expected Data:**
- ~4,200 channel samples
- 4-6 event records
- Final position: y ≈ 126m, z ≈ 63m
- Maximum temperature: 60-75°C

### Test 3: Stops, Starts, and Turns (8 minutes)
**Directory**: `output/test_3_stops_starts_turns/`

Complex maneuvering sequence with multiple direction changes and differential motor control.

**Key Behaviors:**
- Multiple start/stop cycles
- Differential motor speeds for turning (left/right wheels at different speeds)
- Variable position trajectory with direction changes
- Current spikes during acceleration phases
- Activity events for each maneuver

**Expected Data:**
- ~4,800 channel samples
- 15-20 event records (one per maneuver)
- Final position: varies based on path

### Test 4: Motor Stall at Obstacle (6 minutes)
**Directory**: `output/test_4_motor_stall/`

The rover encounters an obstacle that causes Motor 4 to stall, triggering fault detection and recovery.

**Key Behaviors:**
- Normal driving for first 2 minutes
- Motor 4 stalls at t=120s (speed drops to 0, current spikes to 2.5A)
- Fault code `0x0042` set (current limit exceeded)
- Rapid temperature increase on Motor 4
- Emergency stop triggered
- Recovery after ~45 seconds, fault cleared

**Expected Data:**
- ~3,600 channel samples
- 6-8 event records including warnings
- Motor 4 temperature spike to 50-60°C during stall

### Test 5: IMU Malfunction (10 minutes)
**Directory**: `output/test_5_imu_malfunction/`

The rover executes a nominal trajectory while the IMU exhibits intermittent malfunctions.

**Key Behaviors:**
- Normal forward driving motion
- IMU data shows periodic glitches (stuck values, dropouts)
- Glitches occur at approximately: 80s, 180s, 250s, 350s, 450s, 520s
- Each glitch lasts ~15 seconds
- Warning events for IMU anomalies
- All other telemetry remains normal

**Expected Data:**
- ~6,000 channel samples
- 8-10 event records (warnings for each glitch)
- IMU acceleration values stuck or erratic during glitches

### Test 6: Stationary Command Error (2 minutes)
**Directory**: `output/test_6_command_error/`

The rover remains stationary while receiving malformed commands that trigger parsing errors.

**Key Behaviors:**
- All motors at zero speed
- Position remains constant at origin
- Two command errors at t=30s and t=90s
- Fault code `0x00F1` set (command parse error)
- Command severity events for rejected commands
- Faults cleared after brief periods

**Expected Data:**
- ~1,200 channel samples
- 8-10 event records (command errors and fault status)
- All position values remain at 0.0m

## Usage

### Installation

1. Ensure Python 3.7+ is installed
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Generating Telemetry

Run the main generator script:

```bash
python generate_all.py
```

This will generate all 6 test scenarios. Output will be created in the `output/` directory:

```
output/
├── test_1_straight_line/
│   ├── channel.log
│   └── event.log
├── test_2_uphill/
│   ├── channel.log
│   └── event.log
├── test_3_stops_starts_turns/
│   ├── channel.log
│   └── event.log
├── test_4_motor_stall/
│   ├── channel.log
│   └── event.log
├── test_5_imu_malfunction/
│   ├── channel.log
│   └── event.log
└── test_6_command_error/
    ├── channel.log
    └── event.log
```

### Generation Time

Total generation time is approximately 30-60 seconds for all 6 scenarios, depending on system performance.

## Implementation Details

### Physics Simulation

The simulator implements realistic physical behaviors:

- **Motor Current**: Proportional to motor speed and load (climbing, obstacles)
- **Temperature Dynamics**: 
  - Heating from current draw (simplified: ΔT ∝ current)
  - Cooling toward ambient temperature (25°C)
  - Thermal inertia prevents instant changes
- **IMU Response**: Reflects terrain changes, rover motion, and orientation
- **Noise**: Gaussian noise added to high-frequency channels for realism

### Sampling Rates

Channels are sampled at different rates to simulate real-world systems:

- **10 Hz** (100ms): Fast-changing data (motor currents, IMU)
- **5 Hz** (200ms): Medium-rate data (motor speeds)
- **1 Hz** (1000ms): Slow-changing data (temperatures, position, fault codes)

### Event Severities

- **activity_hi**: Major operational state changes (commands, mode changes)
- **activity_lo**: Minor operational events (routine state updates)
- **command**: Command processing events (received, rejected, parsed)
- **warning**: Threshold violations, anomalies, fault conditions

## File Structure

```
telemetry-generator/
├── generate_all.py          # Main entry point
├── telemetry_generator.py   # Core simulator and logger classes
├── scenarios.py             # Scenario implementations
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── output/                 # Generated data (created by script)
```

## Example Data Snippets

### Sample channel.log entries:
```csv
1708875000.000,motors.motor1_speed,50.0
1708875000.000,motors.motor2_speed,50.0
1708875000.100,motors.motor1_current,0.523
1708875000.100,imu.accel_z,-9.876
1708875001.000,motors.motor1_temperature,25.5
1708875001.000,nav.position_y,0.50
1708875001.000,system.fault_code,0x0000
```

### Sample event.log entries:
```csv
1708875000.000,drive.start_forward,activity_hi,Drive command received: forward at 0.5 m/s
1708875060.000,nav.bump_detected,activity_lo,Terrain bump detected at position y=30.2m
1708875120.000,motors.high_current_warning,warning,High motor current detected: 1.25A
1708875125.000,drive.emergency_stop,activity_hi,Emergency stop initiated
1708875180.000,command.invalid_format,command,Invalid command format received: 'DRIV3 F0RWARD @#$%'
```

## Notes

- This is example/test data generation code, not production quality
- Time steps are simulated (not real-time)
- Physics models are simplified but realistic enough for testing
- Timestamps are Unix time (seconds since epoch)
- All data is deterministic except for random noise components

## License

This is example code for demonstration and testing purposes.
