"""
Test scenario definitions for rover telemetry generation.
Each scenario simulates a different operational condition over 5-10 minutes.
"""

import numpy as np
from telemetry_generator import RoverSimulator, TelemetryLogger


def scenario_1_straight_line_bumps(output_dir: str):
    """
    Test 1: Straight line driving with bumps (5 minutes)
    
    - Constant forward velocity
    - Position increments along y-axis
    - Periodic bumps cause IMU z-axis spikes
    - Activity EVRs: drive start/stop
    - Normal motor currents, gradual temp rise
    """
    print("\nGenerating Test 1: Straight Line with Bumps (5 min)")
    
    logger = TelemetryLogger(output_dir)
    rover = RoverSimulator(logger)
    
    # Log start event
    rover.log_event("drive.start_forward", "activity_hi", "Drive command received: forward at 0.5 m/s")
    
    # Simulation parameters
    duration = 5 * 60  # 5 minutes
    dt = 0.01  # 10ms timestep
    velocity = 0.5  # m/s forward
    
    # Set nominal motor speeds for forward motion
    nominal_speed = 50.0  # RPM
    rover.set_motor_speeds([nominal_speed] * 4)
    
    # Simulate
    t = 0
    bump_times = [60, 90, 150, 210, 270]  # Bumps at these times
    
    while t < duration:
        # Update position
        rover.position[1] += velocity * dt  # Move along y-axis
        
        # Check for bumps
        if any(abs(t - bt) < 0.5 for bt in bump_times):
            # Bump detected - spike in z acceleration
            bump_magnitude = np.random.uniform(2.0, 4.0)
            rover.set_acceleration([0, 0, -9.81 + bump_magnitude])
            
            # Log bump event if at exact bump time
            if any(abs(t - bt) < dt for bt in bump_times):
                rover.log_event("nav.bump_detected", "activity_lo", f"Terrain bump detected at position y={rover.position[1]:.1f}m")
        else:
            # Normal gravity
            rover.set_acceleration([0, 0, -9.81])
        
        rover.update(dt)
        t += dt
    
    # Log stop event
    rover.log_event("drive.stop", "activity_hi", "Drive command received: stop")
    rover.set_motor_speeds([0.0] * 4)
    
    # Final samples
    for _ in range(20):
        rover.update(dt)
    
    logger.flush()
    print(f"Final position: y={rover.position[1]:.1f}m")


def scenario_2_uphill_climb(output_dir: str):
    """
    Test 2: Steep uphill climb (7 minutes)
    
    - Increasing z-position (climbing)
    - Higher motor currents (1.5-2x normal)
    - Elevated temperatures (approaching limits)
    - IMU shows increased pitch
    - Warning EVRs for high current/temp thresholds
    """
    print("\nGenerating Test 2: Steep Uphill Climb (7 min)")
    
    logger = TelemetryLogger(output_dir)
    rover = RoverSimulator(logger)
    
    rover.log_event("drive.start_climb", "activity_hi", "Drive command received: climb hill")
    
    duration = 7 * 60  # 7 minutes
    dt = 0.01
    velocity = 0.3  # m/s slower due to incline
    climb_rate = 0.15  # m/s vertical
    
    # Higher motor speeds for climbing
    climb_speed = 80.0  # RPM
    rover.set_motor_speeds([climb_speed] * 4)
    
    # Simulate higher currents for climbing
    high_current_multiplier = 1.8
    
    t = 0
    warned_current = False
    warned_temp = False
    
    while t < duration:
        # Update position (forward and upward)
        rover.position[1] += velocity * dt
        rover.position[2] += climb_rate * dt
        
        # Increased acceleration due to pitch
        pitch_accel_y = 1.5  # Forward acceleration component
        pitch_accel_z = -9.81 + 2.0  # Reduced normal force
        rover.set_acceleration([0, pitch_accel_y, pitch_accel_z])
        
        # Manually increase motor currents for climbing load
        for i in range(4):
            base_current = abs(rover.motor_speeds[i]) / 100.0 * high_current_multiplier
            noise = np.random.normal(0, 0.05)
            rover.motor_currents[i] = max(0, base_current + noise)
        
        rover.update(dt)
        
        # Check for warning thresholds
        if not warned_current and max(rover.motor_currents) > 1.2:
            rover.log_event("motors.high_current_warning", "warning", f"High motor current detected: {max(rover.motor_currents):.2f}A")
            warned_current = True
        
        if not warned_temp and max(rover.motor_temperatures) > 60.0:
            rover.log_event("motors.high_temp_warning", "warning", f"Elevated motor temperature: {max(rover.motor_temperatures):.1f}°C")
            warned_temp = True
        
        t += dt
    
    rover.log_event("drive.stop", "activity_hi", "Drive command received: stop")
    rover.log_event("nav.climb_complete", "activity_lo", f"Hill climb complete: elevation gain {rover.position[2]:.1f}m")
    
    rover.set_motor_speeds([0.0] * 4)
    for _ in range(20):
        rover.update(dt)
    
    logger.flush()
    print(f"Final position: y={rover.position[1]:.1f}m, z={rover.position[2]:.1f}m")
    print(f"Max temperature: {max(rover.motor_temperatures):.1f}°C")


def scenario_3_stops_starts_turns(output_dir: str):
    """
    Test 3: Stops, starts, and turns (8 minutes)
    
    - Variable motor speeds (differential for turns)
    - Position changes direction multiple times
    - Current spikes during acceleration
    - Activity EVRs for each maneuver command
    """
    print("\nGenerating Test 3: Stops, Starts, and Turns (8 min)")
    
    logger = TelemetryLogger(output_dir)
    rover = RoverSimulator(logger)
    
    duration = 8 * 60
    dt = 0.01
    
    # Define maneuver sequence: (start_time, duration, command, speeds, velocity)
    maneuvers = [
        (0, 60, "forward", [50, 50, 50, 50], [0, 0.5, 0]),
        (60, 5, "stop", [0, 0, 0, 0], [0, 0, 0]),
        (65, 40, "forward", [50, 50, 50, 50], [0, 0.5, 0]),
        (105, 5, "stop", [0, 0, 0, 0], [0, 0, 0]),
        (110, 30, "turn_right", [60, 60, 30, 30], [0.3, 0.3, 0]),  # Right wheels slower
        (140, 5, "stop", [0, 0, 0, 0], [0, 0, 0]),
        (145, 50, "forward", [50, 50, 50, 50], [0, 0.5, 0]),
        (195, 5, "stop", [0, 0, 0, 0], [0, 0, 0]),
        (200, 30, "turn_left", [30, 30, 60, 60], [0.3, 0.3, 0]),  # Left wheels slower
        (230, 5, "stop", [0, 0, 0, 0], [0, 0, 0]),
        (235, 60, "forward_fast", [70, 70, 70, 70], [0, 0.7, 0]),
        (295, 5, "stop", [0, 0, 0, 0], [0, 0, 0]),
        (300, 40, "reverse", [-40, -40, -40, -40], [0, -0.4, 0]),
        (340, 5, "stop", [0, 0, 0, 0], [0, 0, 0]),
        (345, 135, "forward", [50, 50, 50, 50], [0, 0.5, 0]),
    ]
    
    t = 0
    current_maneuver_idx = 0
    heading = 0.0  # Radians
    
    while t < duration:
        # Find current maneuver
        for idx, (start, dur, cmd, speeds, vel) in enumerate(maneuvers):
            if start <= t < start + dur:
                if idx != current_maneuver_idx:
                    # New maneuver starting
                    current_maneuver_idx = idx
                    rover.set_motor_speeds(speeds)
                    rover.log_event("drive.maneuver", "activity_hi", f"Drive command received: {cmd}")
                
                # Update velocity based on heading
                speed = np.sqrt(vel[0]**2 + vel[1]**2 + vel[2]**2)
                vx = speed * np.sin(heading)
                vy = speed * np.cos(heading)
                
                rover.position[0] += vx * dt
                rover.position[1] += vy * dt
                
                # Adjust heading during turns
                if "turn_right" in cmd:
                    heading += 0.01 * dt
                elif "turn_left" in cmd:
                    heading -= 0.01 * dt
                
                # Add some lateral acceleration during turns
                if "turn" in cmd:
                    rover.set_acceleration([2.0 * np.sign(speeds[0] - speeds[2]), 0, -9.81])
                else:
                    rover.set_acceleration([0, 0, -9.81])
                
                break
        
        rover.update(dt)
        t += dt
    
    rover.log_event("drive.mission_complete", "activity_hi", "Mission sequence complete")
    
    logger.flush()
    print(f"Final position: x={rover.position[0]:.1f}m, y={rover.position[1]:.1f}m")


def scenario_4_motor_stall(output_dir: str):
    """
    Test 4: Motor stall at obstacle (6 minutes)
    
    - Normal driving, then motor4 stalls (speed → 0, current → max)
    - Fault code set to 0x0042 (current limit)
    - Temperature spike on motor4
    - Warning EVR: "Motor 4 current limit exceeded"
    - Activity EVR: "Emergency stop initiated"
    - Recovery sequence with fault cleared
    """
    print("\nGenerating Test 4: Motor Stall at Obstacle (6 min)")
    
    logger = TelemetryLogger(output_dir)
    rover = RoverSimulator(logger)
    
    rover.log_event("drive.start_forward", "activity_hi", "Drive command received: forward")
    
    duration = 6 * 60
    dt = 0.01
    
    # Stall occurs at t=120s
    stall_time = 120.0
    stall_duration = 45.0
    recovery_time = stall_time + stall_duration
    
    t = 0
    stall_occurred = False
    recovery_started = False
    
    # Normal forward motion
    nominal_speed = 50.0
    rover.set_motor_speeds([nominal_speed] * 4)
    
    while t < duration:
        if t >= stall_time and t < recovery_time:
            if not stall_occurred:
                # Stall motor 4
                rover.log_event("nav.obstacle_detected", "activity_lo", "Obstacle encountered at right rear wheel")
                rover.set_motor_speeds([nominal_speed, nominal_speed, nominal_speed, 0.0])
                
                # Immediately trigger fault
                rover.set_fault_code("0x0042")
                rover.log_event("motors.current_limit_fault", "warning", "Motor 4 current limit exceeded: 2.5A")
                rover.log_event("drive.emergency_stop", "activity_hi", "Emergency stop initiated")
                
                # Stop all motors
                rover.set_motor_speeds([0.0] * 4)
                
                stall_occurred = True
            
            # Manually set high current on motor 4 during stall
            rover.motor_currents[3] = 2.5 + np.random.normal(0, 0.1)
            
            # Rapid temperature increase on motor 4
            rover.motor_heat_accumulators[3] += 0.5 * dt
            
            # Very slow reverse motion (blocked)
            rover.position[1] += 0.01 * dt
            
        elif t >= recovery_time:
            if not recovery_started:
                rover.log_event("drive.resume_operation", "activity_hi", "Obstacle cleared, resuming operation")
                rover.log_event("motors.fault_cleared", "activity_lo", "Motor 4 current normal, fault cleared")
                rover.set_fault_code("0x0000")
                rover.set_motor_speeds([nominal_speed] * 4)
                recovery_started = True
            
            # Normal forward motion
            rover.position[1] += 0.5 * dt
        
        else:
            # Normal driving before stall
            rover.position[1] += 0.5 * dt
        
        rover.set_acceleration([0, 0, -9.81])
        rover.update(dt)
        t += dt
    
    rover.log_event("drive.stop", "activity_hi", "Drive command received: stop")
    rover.set_motor_speeds([0.0] * 4)
    
    for _ in range(20):
        rover.update(dt)
    
    logger.flush()
    print(f"Final position: y={rover.position[1]:.1f}m")
    print(f"Motor 4 final temperature: {rover.motor_temperatures[3]:.1f}°C")


def scenario_5_imu_malfunction(output_dir: str):
    """
    Test 5: IMU malfunction (10 minutes)
    
    - Nominal trajectory (gentle path)
    - IMU data shows intermittent glitches/dropouts or stuck values
    - Warning EVRs for "IMU data anomaly detected"
    - Other telemetry remains normal
    """
    print("\nGenerating Test 5: IMU Malfunction (10 min)")
    
    logger = TelemetryLogger(output_dir)
    rover = RoverSimulator(logger)
    
    rover.log_event("drive.start_nominal", "activity_hi", "Drive command received: nominal trajectory")
    rover.log_event("imu.selftest_anomaly", "warning", "IMU self-test anomaly detected")
    
    duration = 10 * 60
    dt = 0.01
    
    nominal_speed = 50.0
    rover.set_motor_speeds([nominal_speed] * 4)
    
    # IMU glitch parameters
    glitch_intervals = [80, 180, 250, 350, 450, 520]
    stuck_value = None
    stuck_until = 0
    
    t = 0
    while t < duration:
        # Normal motion
        rover.position[1] += 0.5 * dt
        
        # Check for IMU glitches
        in_glitch = False
        for glitch_time in glitch_intervals:
            if glitch_time <= t < glitch_time + 15:
                in_glitch = True
                
                # Log glitch detection once per interval
                if abs(t - glitch_time) < dt:
                    rover.log_event("imu.data_anomaly", "warning", f"IMU data anomaly detected at t={t:.1f}s")
                
                # Stuck or random IMU data
                if stuck_value is None:
                    stuck_value = [np.random.uniform(-2, 2), 
                                  np.random.uniform(-2, 2),
                                  np.random.uniform(-12, -8)]
                    stuck_until = glitch_time + 15
                
                rover.set_acceleration(stuck_value)
                break
        
        if not in_glitch:
            stuck_value = None
            # Normal acceleration with small variations
            rover.set_acceleration([
                np.random.normal(0, 0.3),
                np.random.normal(0, 0.3),
                -9.81
            ])
        
        rover.update(dt)
        t += dt
    
    rover.log_event("drive.stop", "activity_hi", "Drive command received: stop")
    rover.log_event("imu.maintenance_required", "activity_lo", "Mission complete - IMU requires maintenance")
    
    rover.set_motor_speeds([0.0] * 4)
    for _ in range(20):
        rover.update(dt)
    
    logger.flush()
    print(f"Final position: y={rover.position[1]:.1f}m")


def scenario_6_command_error(output_dir: str):
    """
    Test 6: Stationary command error (2 minutes)
    
    - All motors at zero
    - Position constant
    - Fault code set to 0x00F1 (command parse error)
    - Command severity EVR: "Invalid command format received"
    - Command severity EVR: "Command rejected"
    """
    print("\nGenerating Test 6: Stationary Command Error (2 min)")
    
    logger = TelemetryLogger(output_dir)
    rover = RoverSimulator(logger)
    
    rover.log_event("system.ready", "activity_hi", "System ready, awaiting commands")
    
    duration = 2 * 60
    dt = 0.01
    
    # Rover is stationary
    rover.set_motor_speeds([0.0] * 4)
    rover.set_acceleration([0, 0, -9.81])
    
    # Command error occurs at t=30s
    error_time = 30.0
    error_occurred = False
    
    t = 0
    while t < duration:
        if t >= error_time and not error_occurred:
            # Malformed command received
            rover.set_fault_code("0x00F1")
            rover.log_event("command.invalid_format", "command", "Invalid command format received: 'DRIV3 F0RWARD @#$%'")
            rover.log_event("command.rejected", "command", "Command rejected: syntax error at position 5")
            rover.log_event("system.fault_set", "warning", "Fault code set: 0x00F1 (command parse error)")
            error_occurred = True
        
        # Clear fault at t=60s
        if t >= 60.0 and rover.fault_code != "0x0000":
            rover.set_fault_code("0x0000")
            rover.log_event("command.parser_reset", "activity_lo", "Fault cleared: command parser reset")
        
        # Additional command error at t=90s
        if 90.0 <= t < 90.1:
            rover.set_fault_code("0x00F1")
            rover.log_event("command.invalid_format", "command", "Invalid command format received: checksum mismatch")
            rover.log_event("command.rejected", "command", "Command rejected: verification failed")
        
        # Clear fault at t=100s
        if t >= 100.0 and rover.fault_code != "0x0000":
            rover.set_fault_code("0x0000")
            rover.log_event("command.parser_reset", "activity_lo", "Fault cleared: ready for commands")
        
        rover.update(dt)
        t += dt
    
    rover.log_event("system.test_complete", "activity_hi", "Test sequence complete")
    
    logger.flush()
    print(f"Position unchanged: x={rover.position[0]:.1f}m, y={rover.position[1]:.1f}m")
