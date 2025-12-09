# Chopsticks Charm

A Juju charm for distributed Ceph stress testing using [Locust](https://locust.io/) and the Chopsticks framework.

## Overview

This charm deploys distributed Locust workers for scalable load generation against Ceph S3 (RGW) endpoints. The leader unit runs as the Locust coordinator, while all other units run as workers that connect to it.

## Quick Start

```bash
# Deploy with 5 units (1 leader + 4 workers)
juju deploy ./chopsticks -n 5

# Configure S3 endpoint
juju config chopsticks \
    s3-endpoint=http://10.0.0.1:80 \
    s3-access-key=YOUR_ACCESS_KEY \
    s3-secret-key=YOUR_SECRET_KEY \
    s3-bucket=test-bucket

# Start a test
juju run chopsticks/leader start-test users=50 spawn-rate=5 duration=10m

# Check status
juju run chopsticks/leader test-status

# Stop test
juju run chopsticks/leader stop-test

# Get metrics
juju run chopsticks/leader fetch-metrics
```

## Actions

### start-test

Start a distributed stress test.

```bash
juju run chopsticks/leader start-test users=10 spawn-rate=2.5 duration=30m
```

Tests will run asynchronously for the specified duration. Query current status with the `test-status` action, cf. below. 

The output of this action will summarize the parameters for the test, and where on the leader metrics are collected. Also cf. the `fetch-metrics` action below.


Parameters:
- `users`: Simulated user count at start of test
- `spawn-rate`: Rate of additional users spawned per second (float)
- `duration`: Test run time, e.g. 300s, 1h30m
- `scenario-file`: Scenario file to use. This is a path relative to the chopsticks repo.
- `headless`: Run without web UI (default: true)

### stop-test

Stop the current test.

```bash
juju run chopsticks/leader stop-test
```

### test-status

Get current test status.

```bash
juju run chopsticks/leader test-status
```

### fetch-metrics

Retrieve metrics from the last test.

```bash
juju run chopsticks/leader fetch-metrics format=summary
```

## File Locations

| Path | Description |
|------|-------------|
| `/opt/chopsticks/src` | Cloned repository |
| `/opt/chopsticks/venv` | Python virtual environment |
| `/etc/chopsticks/s3_config.yaml` | S3 configuration |
| `/var/lib/chopsticks/<run-id>/` | Test metrics and reports |

## Systemd Services

- `chopsticks-leader.service` - Headless leader
- `chopsticks-leader-webui.service` - Leader with web UI
- `chopsticks-worker.service` - Worker process


## Security Considerations

> **Warning**: This charm clones and executes code from the configured `repo-url` as root. Only use repositories you trust. If `repo-url` is set to an untrusted or compromised repository, arbitrary code will be executed on the deployed units.

S3 credentials are stored at `/etc/chopsticks/s3_config.yaml` with restricted permissions.

