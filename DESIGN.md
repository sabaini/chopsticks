# Chopsticks Design Document

## Architecture Overview

Chopsticks is designed as an extensible stress testing framework for Ceph storage systems. It uses Locust as the foundation for distributed load generation and implements a pluggable architecture for workloads and drivers.

## Core Components

### 1. Workloads (`chopsticks/workloads/`)

Workloads define the high-level storage interface being tested (S3, RBD, etc.). Each workload:

- Extends Locust's `User` class
- Provides a unified client interface
- Handles configuration loading
- Manages driver instantiation
- Implements Locust event integration for metrics

**Current Workloads:**
- `s3/`: S3 object storage workload

**Future Workloads:**
- `rbd/`: RADOS Block Device workload
- `cephfs/`: CephFS filesystem workload

### 2. Drivers (`chopsticks/drivers/`)

Drivers are the actual client implementations that interact with storage systems. Multiple drivers can exist for each workload, allowing flexibility in testing different client libraries and approaches.

**Driver Interface:**
Each driver must implement the base interface for its workload type (e.g., `BaseS3Driver`).

**Current S3 Drivers:**
- `s5cmd`: High-performance CLI-based S3 client
  - Fast parallel operations
  - Low memory footprint
  - Simple subprocess-based integration

**Future S3 Drivers:**
- `boto3`: Official AWS SDK for Python
- `minio-py`: MinIO Python SDK
- `aws-cli`: AWS CLI wrapper

**Future RBD Drivers:**
- `librbd`: Python bindings for librbd
- `rbd-cli`: rbd command-line tool wrapper

### 3. Scenarios (`chopsticks/scenarios/`)

Scenarios define specific test cases by:
- Inheriting from a workload class
- Defining tasks with `@task` decorator
- Setting task weights for load distribution
- Configuring wait times between tasks

**Current Scenarios:**
- `s3_large_objects.py`: Upload/download/delete large objects (100MB default)

**Planned Scenarios:**
- `s3_small_objects.py`: Many small objects (< 1MB)
- `s3_mixed_workload.py`: Mixed object sizes and operations
- `s3_multipart_upload.py`: Large files with multipart uploads
- `rbd_sequential_io.py`: Sequential read/write patterns
- `rbd_random_io.py`: Random I/O patterns

### 4. Configuration (`chopsticks/config/`)

YAML-based configuration files for each workload type. Separates test code from environment-specific settings.

**Configuration Structure:**
```yaml
# Connection settings
endpoint: <storage-endpoint>

# Authentication
access_key: <key>
secret_key: <secret>

# Target configuration
bucket: <bucket-name>
region: <region>

# Driver selection
driver: <driver-name>

# Driver-specific settings
driver_config:
  <driver-options>
```

### 5. Utilities (`chopsticks/utils/`)

Helper functions for:
- Configuration loading
- Common operations
- Metrics collection
- Logging

## Design Principles

### 1. Extensibility

The framework is designed for easy extension:

**Adding a New Workload:**
```python
# 1. Create base workload
class RBDWorkload(User):
    abstract = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load config, initialize driver
        
    # Common methods for RBD operations

# 2. Create driver interface
class BaseRBDDriver(ABC):
    @abstractmethod
    def read(self, offset, length): pass
    
    @abstractmethod
    def write(self, offset, data): pass

# 3. Implement driver
class LibRBDDriver(BaseRBDDriver):
    # Implementation using librbd

# 4. Create scenarios
class RBDRandomIO(RBDWorkload):
    @task
    def random_read(self):
        # Test implementation
```

### 2. Separation of Concerns

- **Workloads**: Define storage interface abstractions
- **Drivers**: Implement client interactions
- **Scenarios**: Define test patterns
- **Configuration**: Store environment settings

### 3. Locust Integration

Proper integration with Locust's event system ensures:
- Accurate metrics collection
- Response time tracking
- Success/failure rates
- Custom statistics

### 4. Configuration-Driven

All environment-specific settings are externalized:
- Endpoints
- Credentials
- Test parameters
- Driver selection

This allows the same test code to run against different environments.

## Data Flow

```
Locust Master
    ↓
Locust Workers (parallel)
    ↓
Scenario Instance
    ↓
Workload (S3Workload)
    ↓
Client Wrapper (S3Client)
    ↓
Driver (S5cmdDriver)
    ↓
Ceph Storage
```

## Metrics and Reporting

Locust provides built-in metrics:
- Request count
- Failure count
- Response times (min, max, avg, percentiles)
- Requests per second
- Current user count

Custom metrics can be added via Locust events:
```python
events.request.fire(
    request_type="S3",
    name="upload",
    response_time=total_time,
    response_length=size,
    exception=None,
    context={}
)
```

## Scaling

### Distributed Testing

Locust supports distributed execution:

**Master Node:**
```bash
uv run locust -f scenario.py --master
```

**Worker Nodes:**
```bash
uv run locust -f scenario.py --worker --master-host=<master-ip>
```

Workers can run on multiple machines for massive scale.

### Resource Management

- Each worker is a Python process
- Multiple workers can run on one machine
- Use process isolation for driver state
- Temporary files are cleaned up automatically

## Security Considerations

1. **Credentials**: Store in config files, not code
2. **Config files**: Add to `.gitignore`
3. **Environment variables**: Alternative to config files
4. **Network**: Support HTTPS endpoints
5. **Cleanup**: Delete test objects after runs

## Future Enhancements

### Phase 2: RBD Support
- Implement RBD workload
- Add librbd driver
- Create RBD scenarios (sequential, random, mixed I/O)
- Add block device configuration

### Phase 3: Advanced Features
- Multi-region testing
- Failure injection
- Custom metrics dashboard
- Result persistence and comparison
- CI/CD integration

### Phase 4: Additional Workloads
- CephFS testing
- RADOS object class testing
- Multi-protocol scenarios

### Phase 5: Analytics
- Historical trend analysis
- Performance regression detection
- Automated reporting
- Integration with monitoring systems

## Testing the Framework

### Unit Tests
```bash
uv run pytest tests/unit/
```

### Integration Tests
```bash
# Requires running Ceph cluster
uv run pytest tests/integration/
```

### End-to-End Tests
```bash
# Run actual load test
uv run locust -f chopsticks/scenarios/s3_large_objects.py --headless -u 10 -r 2 -t 1m
```

## Contributing

1. Follow the existing architecture patterns
2. Add tests for new components
3. Update documentation
4. Use type hints
5. Keep drivers focused and simple
6. Make scenarios representative of real workloads
