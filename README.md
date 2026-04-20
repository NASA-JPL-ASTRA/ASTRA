```
AiSTRA/
├── telemetry-generator/
│   ├── generate_all.py
│   ├── telemetry_generator.py
│   ├── scenarios.py
│   ├── requirements.txt
│   └── output/                   ← generated .log files land here
│       ├── test_1_straight_line/
│       │   ├── channel.log
│       │   └── event.log
│       └── ... (5 more scenarios)
│
└── telemetry-ingest/             
    ├── requirements.txt
    ├── ingestor.py               ← reads .log files, writes to InfluxDB
    ├── query.py                  ← helper functions to read data back out
    └── smoke_test.py             ← runs all 6 scenarios and verifies results
```