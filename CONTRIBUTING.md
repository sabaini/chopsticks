# Contributing to Chopsticks

Thank you for your interest in contributing to Chopsticks! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://astral.sh/uv/) package manager
- Git
- MicroCeph (for functional testing)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/canonical/chopsticks.git
cd chopsticks

# Install dependencies
uv sync

# Install s5cmd
./scripts/install_s5cmd.sh
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

Follow the existing code structure and patterns:
- Use type hints
- Add docstrings to all public functions/classes
- Follow PEP 8 style guide
- Keep functions focused and small

### 3. Run Tests

Before submitting a PR, ensure tests pass:

```bash
# Run functional tests (requires MicroCeph)
./scripts/run-functional-test.sh

# Run linting
uv run ruff check src/chopsticks/

# Format code
uv run black src/chopsticks/
```

### 4. Commit Changes

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```bash
# Feature
git commit -m "feat: add RBD workload support"

# Bug fix
git commit -m "fix: resolve s5cmd path resolution issue"

# Documentation
git commit -m "docs: update metrics collection guide"

# Refactor
git commit -m "refactor: simplify driver initialization"

# Tests
git commit -m "test: add unit tests for S3 driver"
```

**Commit message structure:**
```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub targeting the `main` branch.

## Pull Request Guidelines

### PR Checklist

- [ ] Code follows project style and conventions
- [ ] All tests pass locally
- [ ] Added/updated tests for new functionality
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow Conventional Commits
- [ ] PR description explains the changes clearly

### PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How were these changes tested?

## Related Issues
Closes #123
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use meaningful variable names

### Example

```python
from typing import Optional
from datetime import datetime


class S3Driver:
    """S3 driver implementation using s5cmd.
    
    Args:
        config: S3 configuration dictionary
        
    Attributes:
        endpoint: S3 endpoint URL
        bucket: Target bucket name
    """
    
    def __init__(self, config: dict) -> None:
        self.endpoint = config['endpoint']
        self.bucket = config['bucket']
    
    def upload(
        self,
        key: str,
        data: bytes,
        metadata: Optional[dict] = None
    ) -> bool:
        """Upload object to S3.
        
        Args:
            key: Object key
            data: Object data
            metadata: Optional metadata dictionary
            
        Returns:
            True if upload successful, False otherwise
        """
        # Implementation
        pass
```

## Adding New Features

### Adding a New Workload

1. Create driver interface in `src/chopsticks/drivers/<workload>/base.py`
2. Implement driver in `src/chopsticks/drivers/<workload>/<driver_name>.py`
3. Create workload class in `src/chopsticks/workloads/<workload>/`
4. Add scenario in `src/chopsticks/scenarios/`
5. Update documentation

See [README.md](README.md#extending-to-new-workloads) for detailed examples.

### Adding a New S3 Driver

1. Create driver class in `src/chopsticks/drivers/s3/`
2. Implement `BaseS3Driver` interface
3. Register in `S3Workload._get_driver()`
4. Add configuration in `config/s3_config.yaml`
5. Update documentation

### Adding a New Scenario

1. Create scenario file in `src/chopsticks/scenarios/`
2. Extend appropriate workload class
3. Define tasks using Locust decorators
4. Add metrics collection
5. Document in README

## Testing

### Functional Tests

Functional tests validate the framework against a real Ceph cluster:

```bash
# Run with defaults
./scripts/run-functional-test.sh

# Custom configuration
TEST_DURATION=5m \
LARGE_OBJECT_SIZE=100 \
TEST_USERS=10 \
./scripts/run-functional-test.sh
```

### Unit Tests (Future)

```bash
uv run pytest tests/
```

### CI/CD

All PRs automatically trigger functional tests via GitHub Actions. The workflow:
1. Sets up MicroCeph
2. Runs S3 stress tests
3. Validates metrics
4. Uploads artifacts

## Documentation

When adding features, update:
- `README.md` - Main documentation
- `DESIGN.md` - Architecture details (if applicable)
- `METRICS_DESIGN.md` - Metrics specification (if adding metrics)
- `.github/workflows/README.md` - CI/CD (if modifying tests)

Use clear, concise language and include examples.

## Metrics Integration

All new workloads and scenarios should integrate metrics:

1. Import metrics components:
```python
from chopsticks.metrics import (
    MetricsCollector,
    OperationMetric,
    OperationType,
    WorkloadType,
)
```

2. Record operations:
```python
from datetime import datetime
import uuid

start = datetime.utcnow()
# Perform operation
end = datetime.utcnow()

metric = OperationMetric(
    operation_id=str(uuid.uuid4()),
    timestamp_start=start,
    timestamp_end=end,
    operation_type=OperationType.UPLOAD,
    workload_type=WorkloadType.S3,
    driver_name="s5cmd",
    object_key=key,
    size_bytes=len(data),
    success=True,
)
metrics_collector.record_operation(metric)
```

See [METRICS_DESIGN.md](METRICS_DESIGN.md) for comprehensive guidance.

## Getting Help

- **Issues**: Browse existing issues or create new ones
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check docs/ directory

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers
- Focus on what's best for the community
- Show empathy towards other community members
