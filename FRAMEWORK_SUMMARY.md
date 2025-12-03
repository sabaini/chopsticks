# Chopsticks Framework Summary

## Overview

Chopsticks is a flexible, extensible Ceph stress testing framework built on Locust for distributed load generation. It uses a pluggable architecture supporting multiple workloads and client drivers.

## Key Design Decisions

### 1. **Workload Abstraction Layer**
Each storage protocol (S3, RBD) is a separate workload with:
- Unified client interface
- Configuration management
- Driver selection logic
- Locust integration for metrics

### 2. **Pluggable Driver System**
Multiple client implementations per workload:
- **Current**: s5cmd for S3
- **Future**: boto3, minio-py, aws-cli for S3
- **Future**: librbd, rbd-cli for RBD

### 3. **Scenario-Based Testing**
Test scenarios are Python classes that:
- Inherit from workload base classes
- Define tasks with `@task` decorator
- Set task weights for load distribution
- Control timing between operations

### 4. **Configuration-Driven**
YAML configuration separates code from environment:
- Connection endpoints
- Authentication credentials
- Target resources (buckets, pools)
- Driver selection and options

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Locust Framework                    │
│  (Distributed Load Generation & Metrics)         │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    ┌────▼────┐        ┌────▼────┐
    │   S3    │        │   RBD   │
    │Workload │        │Workload │
    └────┬────┘        └────┬────┘
         │                   │
    ┌────▼─────────┐    ┌───▼──────────┐
    │  S3 Drivers  │    │ RBD Drivers  │
    │  - s5cmd     │    │  - librbd    │
    │  - boto3     │    │  - rbd-cli   │
    │  - minio     │    │              │
    └──────┬───────┘    └──────┬───────┘
           │                   │
    ┌──────▼───────────────────▼──────┐
    │        Ceph Storage              │
    │  (RADOS, RGW, RBD, CephFS)       │
    └──────────────────────────────────┘
```

## Directory Structure

```
chopsticks/
├── src/chopsticks/           # Main package (src layout for uv)
│   ├── workloads/            # Storage workload implementations
│   │   ├── s3/              # S3 object storage
│   │   │   └── s3_workload.py
│   │   └── rbd/             # RBD block storage (future)
│   │       └── rbd_workload.py
│   ├── drivers/              # Client driver implementations
│   │   ├── s3/              
│   │   │   ├── base.py      # Base driver interface
│   │   │   └── s5cmd_driver.py
│   │   └── rbd/             # Future RBD drivers
│   ├── scenarios/            # Test scenario definitions
│   │   ├── s3_large_objects.py
│   │   └── example_scenario.py
│   ├── utils/                # Helper utilities
│   │   └── config_loader.py
│   └── config/               # (empty, actual configs in root)
├── config/                   # Configuration files
│   ├── s3_config.yaml        # User's config (gitignored)
│   └── s3_config.yaml.example
├── scripts/                  # Utility scripts
│   └── install_s5cmd.sh
├── pyproject.toml           # Project metadata (uv_build)
├── README.md                # User documentation
├── DESIGN.md                # Architecture documentation
├── QUICKSTART.md            # Quick start guide
└── FRAMEWORK_SUMMARY.md     # This file
```

## Current Implementation

### S3 Workload
- **Base Class**: `S3Workload` (extends Locust's `User`)
- **Client Wrapper**: `S3Client` (integrates with Locust events)
- **Operations**: upload, download, delete, list, head

### S3 Driver (s5cmd)
- **Implementation**: Subprocess-based CLI wrapper
- **Features**: Fast, low memory, parallel operations
- **Authentication**: Environment variables

### Scenario: Large Objects
- **File**: `s3_large_objects.py`
- **Default Size**: 100MB (configurable via `LARGE_OBJECT_SIZE`)
- **Tasks**: 
  - Upload (weight: 3)
  - Download (weight: 2)
  - Delete (weight: 1)

## Extension Points

### Adding a New S3 Driver

1. Create `src/chopsticks/drivers/s3/boto3_driver.py`:
```python
from .base import BaseS3Driver

class Boto3Driver(BaseS3Driver):
    def upload(self, key, data, metadata=None):
        # Implementation using boto3
        pass
```

2. Register in `S3Workload._get_driver()`:
```python
drivers = {
    's5cmd': S5cmdDriver,
    'boto3': Boto3Driver,  # Add here
}
```

3. Update config to use new driver:
```yaml
driver: boto3
```

### Adding RBD Workload

1. Create base driver interface:
```python
# src/chopsticks/drivers/rbd/base.py
class BaseRBDDriver(ABC):
    @abstractmethod
    def read(self, offset, length): pass
    
    @abstractmethod
    def write(self, offset, data): pass
```

2. Implement driver:
```python
# src/chopsticks/drivers/rbd/librbd_driver.py
class LibRBDDriver(BaseRBDDriver):
    # Use Python rbd bindings
```

3. Create workload:
```python
# src/chopsticks/workloads/rbd/rbd_workload.py
class RBDWorkload(User):
    # Similar to S3Workload
```

4. Create scenario:
```python
# src/chopsticks/scenarios/rbd_random_io.py
class RBDRandomIO(RBDWorkload):
    @task
    def random_read(self):
        # Implementation
```

### Creating Custom Scenarios

```python
from locust import task, between
from chopsticks.workloads.s3.s3_workload import S3Workload

class MixedWorkload(S3Workload):
    wait_time = between(0.5, 2)
    
    def on_start(self):
        self.small_size = 10 * 1024      # 10KB
        self.large_size = 100 * 1024 * 1024  # 100MB
    
    @task(5)  # 50% of operations
    def upload_small(self):
        key = self.generate_key("small")
        data = self.generate_data(self.small_size)
        self.client.upload(key, data)
    
    @task(3)  # 30% of operations
    def upload_large(self):
        key = self.generate_key("large")
        data = self.generate_data(self.large_size)
        self.client.upload(key, data)
    
    @task(2)  # 20% of operations
    def list_objects(self):
        self.client.list_objects(max_keys=1000)
```

## Technology Stack

- **Build System**: uv (native uv_build backend)
- **Load Testing**: Locust 2.20+
- **Configuration**: PyYAML
- **S3 Client**: s5cmd (initial), boto3 (planned)
- **Python**: 3.12+

## Benefits

1. **Extensible**: Easy to add new workloads, drivers, scenarios
2. **Scalable**: Locust's distributed architecture
3. **Realistic**: Simulate real-world traffic patterns
4. **Flexible**: Multiple drivers per workload
5. **Observable**: Built-in metrics and reporting
6. **Maintainable**: Clean separation of concerns

## Future Roadmap

### Phase 1: S3 Foundation ✅
- [x] Framework architecture
- [x] S3 workload implementation
- [x] s5cmd driver
- [x] Large object scenario
- [x] Configuration system
- [x] Documentation

### Phase 2: S3 Enhancement
- [ ] Additional S3 scenarios (small objects, multipart, mixed)
- [ ] boto3 driver
- [ ] minio-py driver
- [ ] Metrics persistence
- [ ] Result comparison

### Phase 3: RBD Support
- [ ] RBD workload
- [ ] librbd driver
- [ ] rbd-cli driver
- [ ] Sequential I/O scenario
- [ ] Random I/O scenario
- [ ] RBD configuration

### Phase 4: Advanced Features
- [ ] Multi-region testing
- [ ] Failure injection
- [ ] Custom metrics dashboard
- [ ] CI/CD integration
- [ ] Historical analysis

### Phase 5: Additional Workloads
- [ ] CephFS testing
- [ ] RADOS object class testing
- [ ] Multi-protocol scenarios

## Contributing

When adding components:
1. Follow existing patterns
2. Implement base interfaces
3. Add docstrings
4. Update configuration examples
5. Create example scenarios
6. Document in DESIGN.md
