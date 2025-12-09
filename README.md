# Chopsticks - Ceph Stress Testing Framework

A flexible, extensible stress testing framework for Ceph storage using Locust to drive parallel workers and simulate real-world traffic patterns.

## Features

- **Extensible Workload Architecture**: Currently supports S3, designed to easily add RBD and other workloads
- **Multiple Client Drivers**: Pluggable driver system (currently uses s5cmd for S3)
- **Scenario-Based Testing**: Define and run various stress test scenarios
- **Locust-Powered**: Leverage Locust for distributed load generation
- **Configuration-Driven**: YAML-based configuration for workloads and scenarios
- **Comprehensive Metrics**: Detailed performance metrics with multiple export formats
- **CI/CD Ready**: Automated functional tests run on every pull request

## Architecture

```
chopsticks/
├── workloads/          # Workload implementations (S3, RBD, etc.)
│   ├── s3/            # S3 workload
│   └── rbd/           # RBD workload (future)
├── drivers/            # Client driver implementations
│   ├── s3/            # S3 drivers (s5cmd, boto3, etc.)
│   └── rbd/           # RBD drivers (future)
├── scenarios/          # Test scenario definitions
├── metrics/            # Metrics collection and export
├── config/             # Configuration files
└── utils/              # Utility functions
```

## Quick Start

### Installation

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### Download s5cmd (S3 driver)

```bash
./scripts/install_s5cmd.sh
```

### Configure S3 Endpoint

Edit `config/s3_config.yaml`:

```yaml
endpoint: https://s3.example.com
access_key: YOUR_ACCESS_KEY
secret_key: YOUR_SECRET_KEY
bucket: test-bucket
region: us-east-1
driver: s5cmd
```

### Run a Test

```bash
# Run with web UI (default: http://localhost:8089)
uv run chopsticks --workload-config config/s3_config.yaml \
  -f src/chopsticks/scenarios/s3_large_objects.py

# Run headless mode with 10 users, spawn rate 2/sec, run for 10 minutes
uv run chopsticks --workload-config config/s3_config.yaml \
  -f src/chopsticks/scenarios/s3_large_objects.py \
  --headless --users 10 --spawn-rate 2 --duration 10m

# Run with custom scenario config
uv run chopsticks --workload-config config/s3_config.yaml \
  --scenario-config config/my_scenario.yaml \
  -f src/chopsticks/scenarios/s3_large_objects.py \
  --headless --users 50 --spawn-rate 5 --duration 5m
```

You can also use Locust directly if needed:

```bash
# Set config path and run with Locust
S3_CONFIG_PATH=config/s3_config.yaml uv run locust \
  -f src/chopsticks/scenarios/s3_large_objects.py
```

## Metrics Collection

Chopsticks includes a comprehensive metrics collection system to analyze cluster performance.

### Collected Metrics

1. **Operation Metrics**: Per-operation performance (duration, throughput, success/failure)
2. **Aggregated Metrics**: Statistical summaries with percentiles (p50, p75, p90, p95, p99, p99.9)
3. **System Resources**: Client-side CPU, memory, network, and disk usage
4. **Network Metrics**: Latency, bandwidth, packet loss, TCP statistics
5. **Error Metrics**: Detailed failure tracking with categorization
6. **Test Configuration**: Test parameters and environment metadata

### Export Formats

Metrics can be exported in multiple formats:

- **JSON**: Complete structured export with all metrics
- **JSONL**: Streaming JSON Lines format for large datasets
- **CSV**: Spreadsheet-compatible format
- **Prometheus**: Time-series format for monitoring dashboards

### Using Metrics in Tests

```python
from chopsticks.metrics import MetricsCollector, TestConfiguration, OperationMetric
from datetime import datetime
import uuid

# Initialize collector
test_config = TestConfiguration(
    test_run_id=str(uuid.uuid4()),
    test_name="S3 Performance Test",
    start_time=datetime.utcnow(),
    scenario="s3_large_objects"
)

collector = MetricsCollector(
    test_run_id=test_config.test_run_id,
    test_config=test_config
)

# Metrics are automatically collected during test runs

# Export metrics after test
collector.export_json("metrics.json")
collector.export_csv("metrics.csv")
```

### Key Performance Indicators (KPIs)

The metrics system tracks:

- **Throughput**: MB/s and operations/second
- **Latency**: p50, p95, p99 response times
- **Success Rate**: Percentage of successful operations
- **IOPS**: I/O operations per second
- **Efficiency**: Throughput per CPU usage
- **Stability**: Latency standard deviation

See [METRICS_DESIGN.md](METRICS_DESIGN.md) for complete details.

## Creating New Scenarios

1. Create a new scenario file in `src/chopsticks/scenarios/`
2. Inherit from the appropriate workload class
3. Define your test tasks with `@task` decorator

Example:

```python
from locust import task, between
from chopsticks.workloads.s3.s3_workload import S3Workload

class MyCustomScenario(S3Workload):
    wait_time = between(1, 3)
    
    @task(3)
    def upload_large_file(self):
        key = self.generate_key("large")
        data = self.generate_data(100 * 1024 * 1024)  # 100MB
        self.client.upload(key, data)
    
    @task(2)
    def download_file(self):
        # Download previously uploaded file
        if self.uploaded_keys:
            key = random.choice(self.uploaded_keys)
            self.client.download(key)
```

## Available Scenarios

### S3 Large Objects

Tests upload and download of large objects (configurable size, default 100MB).

```bash
# Default 100MB objects with web UI
uv run chopsticks --workload-config config/s3_config.yaml \
  -f src/chopsticks/scenarios/s3_large_objects.py

# Custom object size (50MB) via scenario config
# Create config/custom_scenario.yaml with:
# s3_large_objects:
#   object_size_mb: 50
#   max_keys_in_memory: 10

uv run chopsticks --workload-config config/s3_config.yaml \
  --scenario-config config/custom_scenario.yaml \
  -f src/chopsticks/scenarios/s3_large_objects.py \
  --headless --users 10 --spawn-rate 2 --duration 5m
```

## Adding New Drivers

1. Create driver class in `src/chopsticks/drivers/s3/` (or appropriate workload)
2. Implement the `BaseS3Driver` interface
3. Update workload configuration to use new driver

Example:

```python
from chopsticks.drivers.s3.base import BaseS3Driver

class MyS3Driver(BaseS3Driver):
    def upload(self, key: str, data: bytes, metadata=None) -> bool:
        # Implementation
        pass
    
    def download(self, key: str) -> bytes:
        # Implementation
        pass
    
    def delete(self, key: str) -> bool:
        # Implementation
        pass
```

Register in workload:

```python
# In s3_workload.py
def _get_driver(self, driver_name: str) -> BaseS3Driver:
    drivers = {
        's5cmd': S5cmdDriver,
        'my_driver': MyS3Driver,  # Add here
    }
    return drivers[driver_name](self.config)
```

## Extending to New Workloads

The framework is designed for easy extension. To add a new workload (e.g., RBD):

### 1. Create Driver Interface

```python
# src/chopsticks/drivers/rbd/base.py
from abc import ABC, abstractmethod

class BaseRBDDriver(ABC):
    @abstractmethod
    def read(self, offset: int, length: int) -> bytes:
        pass
    
    @abstractmethod
    def write(self, offset: int, data: bytes) -> bool:
        pass
```

### 2. Implement Driver

```python
# src/chopsticks/drivers/rbd/librbd_driver.py
from .base import BaseRBDDriver
import rbd

class LibRBDDriver(BaseRBDDriver):
    def __init__(self, config):
        self.config = config
        # Initialize RBD connection
    
    def read(self, offset, length):
        # Implementation using librbd
        pass
    
    def write(self, offset, data):
        # Implementation using librbd
        pass
```

### 3. Create Workload

```python
# src/chopsticks/workloads/rbd/rbd_workload.py
from locust import User
from chopsticks.drivers.rbd.librbd_driver import LibRBDDriver
from chopsticks.metrics import MetricsCollector, OperationMetric

class RBDWorkload(User):
    abstract = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load config, initialize driver
        self.driver = LibRBDDriver(config)
        
        # Initialize metrics collector
        self.metrics_collector = MetricsCollector(...)
    
    def read_block(self, offset, length):
        # Implement with metrics collection
        start = datetime.utcnow()
        data = self.driver.read(offset, length)
        end = datetime.utcnow()
        
        # Record metric
        metric = OperationMetric(
            operation_id=str(uuid.uuid4()),
            timestamp_start=start,
            timestamp_end=end,
            operation_type=OperationType.READ,
            workload_type=WorkloadType.RBD,
            # ... other fields
        )
        self.metrics_collector.record_operation(metric)
        
        return data
```

### 4. Create Scenario

```python
# src/chopsticks/scenarios/rbd_random_io.py
from locust import task, between
from chopsticks.workloads.rbd.rbd_workload import RBDWorkload

class RBDRandomIO(RBDWorkload):
    wait_time = between(0.1, 0.5)
    
    @task
    def random_read(self):
        offset = random.randint(0, self.image_size)
        self.read_block(offset, 4096)
    
    @task
    def random_write(self):
        offset = random.randint(0, self.image_size)
        data = os.urandom(4096)
        self.write_block(offset, data)
```

### 5. Integrating Metrics

All workloads should integrate metrics for comprehensive performance tracking:

```python
from chopsticks.metrics import (
    MetricsCollector,
    OperationMetric,
    OperationType,
    WorkloadType
)
from datetime import datetime
import uuid

# Record operation
start = datetime.utcnow()
result = perform_operation()
end = datetime.utcnow()

duration_ms = (end - start).total_seconds() * 1000
throughput_mbps = (size_bytes / 1024 / 1024) / (duration_ms / 1000) if duration_ms > 0 else 0

metric = OperationMetric(
    operation_id=str(uuid.uuid4()),
    timestamp_start=start,
    timestamp_end=end,
    operation_type=OperationType.UPLOAD,  # or READ, WRITE, etc.
    workload_type=WorkloadType.S3,  # or RBD
    object_key=key,
    object_size_bytes=size_bytes,
    duration_ms=duration_ms,
    throughput_mbps=throughput_mbps,
    success=result.success,
    error_code=result.error_code if not result.success else None,
    driver="my_driver"
)

metrics_collector.record_operation(metric)
```

## Configuration

### S3 Configuration (`config/s3_config.yaml`)

- `endpoint`: S3 endpoint URL
- `access_key`: Access key ID
- `secret_key`: Secret access key
- `bucket`: Default bucket name
- `region`: AWS region (optional, default: us-east-1)
- `driver`: Driver to use (default: s5cmd)
- `driver_config`: Driver-specific configuration

Example:

```yaml
endpoint: http://10.240.47.47:80
access_key: YOUR_ACCESS_KEY
secret_key: YOUR_SECRET_KEY
bucket: test-bucket
region: default
driver: s5cmd
driver_config:
  s5cmd_path: s5cmd
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run black src/chopsticks/

# Lint code
uv run ruff check src/chopsticks/
```

## Testing

### Linting

```bash
# Check code quality
uv run ruff check src/chopsticks/

# Format code
uv run ruff format src/chopsticks/
```

### Unit Tests

```bash
# Run unit tests
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest tests/unit/ --cov=src/chopsticks --cov-report=term
```

### Functional Tests

```bash
# Run with default settings (requires MicroCeph)
./scripts/run-functional-test.sh

# Custom configuration
TEST_DURATION=5m LARGE_OBJECT_SIZE=50 TEST_USERS=5 ./scripts/run-functional-test.sh
```

### CI/CD

All pull requests automatically run:
- **Lint** - Code quality checks (~2 minutes)
- **Unit Tests** - Fast, isolated tests (~2 minutes)
- **Functional Tests** - Full integration with MicroCeph (~15-20 minutes, runs independently)

See [`.github/workflows/README.md`](.github/workflows/README.md) for details.

## Documentation

📚 **Full documentation**: https://canonical-chopsticks.readthedocs-hosted.com

The documentation follows the [Diátaxis framework](https://diataxis.fr/) with four content types:

- **[Tutorial](https://canonical-chopsticks.readthedocs-hosted.com/en/latest/tutorial/)** - Learning-oriented guides for getting started
- **[How-to Guides](https://canonical-chopsticks.readthedocs-hosted.com/en/latest/how-to/)** - Task-oriented instructions for specific goals
- **[Reference](https://canonical-chopsticks.readthedocs-hosted.com/en/latest/reference/)** - Information-oriented technical specifications
- **[Explanation](https://canonical-chopsticks.readthedocs-hosted.com/en/latest/explanation/)** - Understanding-oriented conceptual discussions

Additional documentation:
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guidelines
- [.github/workflows/README.md](.github/workflows/README.md) - CI/CD workflows

## Contributing

1. Follow existing architecture patterns
2. Implement base interfaces for new components
3. Add metrics collection to new workloads
4. Include comprehensive docstrings
5. Follow Conventional Commits for commit messages
6. Run linting and unit tests before submitting PR
7. Ensure CI pipeline passes

## License

This project is licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later).

See the [LICENSE](LICENSE) file for the full license text.

## Author

Utkarsh Bhatt <utkarsh.bhatt@canonical.com>

Copyright (C) 2024 Canonical Ltd.
