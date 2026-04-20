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

## Step 1 - Stand Up InfluxDB with Docker

```
docker run -d \
  --name aistra-influxdb \
  -p 8086:8086 \
  -e DOCKER_INFLUXDB_INIT_MODE=setup \
  -e DOCKER_INFLUXDB_INIT_USERNAME=aistra \
  -e DOCKER_INFLUXDB_INIT_PASSWORD=aistra123 \
  -e DOCKER_INFLUXDB_INIT_ORG=aistra-org \
  -e DOCKER_INFLUXDB_INIT_BUCKET=telemetry \
  -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=aistra-dev-token-12345 \
  influxdb:2.7
```

#### Stopping and restarting InfluxDB

```
docker stop aistra-influxdb
docker start aistra-influxdb
docker rm -f aistra-influxdb
```

## Step 2 - Install Python Dependencies

```
python3 -m venv .venv
source .venv/bin/activate

pip install -r telemetry-generator/requirements.txt
pip install influxdb-client==1.40.0
```

