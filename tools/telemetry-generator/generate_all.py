#!/usr/bin/env python3
"""
Main script to generate all telemetry test scenarios.
Runs all 6 test cases and outputs data to the output/ directory.
"""

import os
from scenarios import (
    scenario_1_straight_line_bumps,
    scenario_2_uphill_climb,
    scenario_3_stops_starts_turns,
    scenario_4_motor_stall,
    scenario_5_imu_malfunction,
    scenario_6_command_error
)


def main():
    """Generate all test scenarios."""

    print("=" * 70)
    print("Rover Telemetry Generator")
    print("=" * 70)
    print("Generating 6 test scenarios with telemetry data...")
    print()

    # Create base output directory
    base_output_dir = "output"
    os.makedirs(base_output_dir, exist_ok=True)

    # Define scenarios with their output directories
    scenarios = [
        ("test_1_straight_line", scenario_1_straight_line_bumps),
        ("test_2_uphill", scenario_2_uphill_climb),
        ("test_3_stops_starts_turns", scenario_3_stops_starts_turns),
        ("test_4_motor_stall", scenario_4_motor_stall),
        ("test_5_imu_malfunction", scenario_5_imu_malfunction),
        ("test_6_command_error", scenario_6_command_error),
    ]

    # Run each scenario
    for test_name, scenario_func in scenarios:
        output_dir = os.path.join(base_output_dir, test_name)

        try:
            scenario_func(output_dir)
            print(f"[OK] Completed: {test_name}")
            print()
        except Exception as e:
            print(f"[FAIL] Failed: {test_name}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 70)
    print("Generation complete!")
    print(f"Output directory: {os.path.abspath(base_output_dir)}")
    print()
    print("Each test directory contains:")
    print("  - channel.log: Channelized telemetry (timestamp, channel, value)")
    print("  - event.log: Event records (timestamp, evr name, severity, message)")
    print("=" * 70)


if __name__ == "__main__":
    main()
