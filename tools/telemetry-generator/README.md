# Rover Telemetry Generator

Python-based telemetry data generator for a simulated 4-wheeled rover system.

## What It Generates

For each scenario, the generator writes:

1. `channel.log` (CSV, no header): `timestamp,channel_name,value`
2. `event.log` (CSV, no header): `timestamp,event_name,severity,message`

Timestamp format is human-readable local time: `YYYY-MM-DD HH:MM:SS`.

## Run

```bash
pip install -r requirements.txt
python generate_all.py
```

Output is written under `output/`:

- `output/test_1_straight_line/`
- `output/test_2_uphill/`
- `output/test_3_stops_starts_turns/`
- `output/test_4_motor_stall/`
- `output/test_5_imu_malfunction/`
- `output/test_6_command_error/`

## Notes

- This is test/demo data generation, not production simulation.
- Generated timestamps are rebased at write time:
  - The last row in each log is aligned to the current device time.
  - Each earlier row is offset by 2 seconds from the next row.
  - This rule applies to both `channel.log` and `event.log`.
- Channels include motor current/speed/temperature, IMU accel, position, and fault code.
