# Metrics IPC Architecture Summary

## Problem
The CI tests were failing because both the persistent metrics server and the workload process were trying to bind to the same HTTP port (8090), causing an "Address already in use" error.

## Solution
Implemented an IPC (Inter-Process Communication) architecture using Unix domain sockets to separate the metrics HTTP endpoint from the workload processes.

## Architecture

### Components

1. **Persistent Metrics Server** (one per controller)
   - Runs as a background daemon process
   - Exposes HTTP endpoint for Prometheus scraping
   - Listens on Unix socket for IPC connections from workloads
   - Location: `src/chopsticks/metrics/http_server.py`

2. **IPC Server** (embedded in metrics server)
   - Accepts connections on Unix domain socket (default: `/tmp/chopsticks_metrics.sock`)
   - Receives metrics from workload processes
   - Forwards metrics to Prometheus exporter
   - Location: `src/chopsticks/metrics/ipc.py` - `MetricsIPCServer`

3. **IPC Client** (in workload processes)
   - Connects to Unix socket
   - Sends operation metrics as JSON over socket
   - Non-blocking, fails gracefully if server unavailable
   - Location: `src/chopsticks/metrics/ipc.py` - `MetricsIPCClient`

4. **Metrics Collector** (in workload processes)
   - Collects metrics locally for JSON/CSV export at test end
   - Also sends metrics to persistent server via IPC client
   - Location: `src/chopsticks/workloads/base_metrics_workload.py`

### Data Flow

```
Workload Process                    Persistent Metrics Server
================                    =========================
                                    
OperationMetric                     HTTP Server (port 8090)
     |                                      |
     |                                      | GET /metrics
     v                                      v
MetricsCollector                    PrometheusExporter
     |                                      ^
     |---> Local storage                    |
     |     (JSON/CSV export)                |
     |                                      |
     |---> MetricsIPCClient                 |
            |                               |
            | JSON over                     |
            | Unix socket                   |
            |                               |
            +-------------> MetricsIPCServer
                           (background thread)
```

### Key Features

1. **No Port Conflicts**: Only one process (persistent server) binds to HTTP port
2. **Graceful Degradation**: Workloads continue if persistent server unavailable
3. **Real-time Metrics**: Prometheus can scrape metrics while tests run
4. **Post-test Export**: Local collector still exports JSON/CSV at test completion
5. **Process Isolation**: Uses Unix sockets for efficient local IPC

## Configuration

Example `s3_config_with_metrics.yaml`:

```yaml
metrics:
  enabled: true
  http_host: 0.0.0.0
  http_port: 8090
  aggregation_window_seconds: 10
  export_dir: /tmp/chopsticks_metrics
  test_name: "S3 Load Test"
  
  persistent:
    enabled: true
    pid_file: /tmp/chopsticks_metrics.pid
    state_file: /tmp/chopsticks_metrics_state.json
    socket_path: /tmp/chopsticks_metrics.sock  # Unix socket for IPC
```

## Usage

### Start Persistent Server

```bash
chopsticks metrics start --config config/s3_config_with_metrics.yaml

# Force cleanup of stale files/processes
chopsticks metrics start --config config/s3_config_with_metrics.yaml --force
```

### Run Workload (connects automatically)

```bash
chopsticks run --workload-config config/s3_config_with_metrics.yaml \
  -f src/chopsticks/scenarios/s3_large_objects.py \
  --headless --users 10 --spawn-rate 2 --duration 5m
```

### Check Metrics

```bash
curl http://localhost:8090/metrics
```

### Stop Server

```bash
chopsticks metrics stop --config config/s3_config_with_metrics.yaml
```

## Changes Made

### New Files
- `src/chopsticks/metrics/ipc.py` - IPC client/server implementation
- `tests/integration/test_metrics_ipc.py` - Integration test for IPC

### Modified Files
- `src/chopsticks/metrics/http_server.py` - Added IPC server integration
- `src/chopsticks/metrics/daemon.py` - Added socket_path support, cleanup method
- `src/chopsticks/metrics/server_daemon.py` - Added socket_path parameter
- `src/chopsticks/workloads/base_metrics_workload.py` - Removed ephemeral server, added IPC client
- `src/chopsticks/cli.py` - Added --force flag to metrics start
- `src/chopsticks/commands/metrics.py` - Handle --force flag for cleanup
- `config/s3_config_with_metrics.yaml` - Added socket_path configuration

### Removed
- Ephemeral metrics HTTP server (was starting in each workload process)
- Direct Prometheus exporter access from workload

## Testing

### Integration Test
Run the full IPC integration test:
```bash
pytest tests/integration/test_metrics_ipc.py -v -s
```

This test:
1. Starts persistent metrics server
2. Runs a workload that generates metrics
3. Verifies metrics are received via IPC
4. Checks Prometheus endpoint returns data

### Unit Tests
All existing unit tests pass with no regressions:
```bash
pytest tests/unit/ -v
```

## Benefits

1. **CI-Safe**: No port conflicts between processes
2. **Scalable**: Multiple workload processes can send to same server
3. **Efficient**: Unix sockets are faster than HTTP for local IPC
4. **Reliable**: Automatic reconnection on connection failures
5. **Clean**: Proper daemon management with PID files and --force cleanup
