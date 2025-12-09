# Copyright (C) 2024 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""Data models for metrics collection"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class OperationType(str, Enum):
    """Supported operation types"""

    UPLOAD = "upload"
    DOWNLOAD = "download"
    DELETE = "delete"
    LIST = "list"
    HEAD = "head"
    READ = "read"
    WRITE = "write"


class WorkloadType(str, Enum):
    """Supported workload types"""

    S3 = "s3"
    RBD = "rbd"


class ErrorCategory(str, Enum):
    """Error categories for analysis"""

    RATE_LIMITING = "rate_limiting"
    NETWORK = "network"
    STORAGE = "storage"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class OperationMetric:
    """Metric for a single I/O operation"""

    operation_id: str
    timestamp_start: datetime
    timestamp_end: datetime
    operation_type: OperationType
    workload_type: WorkloadType
    object_key: str
    object_size_bytes: int
    duration_ms: float
    throughput_mbps: float
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    driver: str = ""
    user_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with string timestamps"""
        data = asdict(self)
        data["timestamp_start"] = self.timestamp_start.isoformat()
        data["timestamp_end"] = self.timestamp_end.isoformat()
        data["operation_type"] = self.operation_type.value
        data["workload_type"] = self.workload_type.value
        return data


@dataclass
class StatisticalSummary:
    """Statistical summary of a metric"""

    min: float
    max: float
    mean: float
    median: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    p99_9: float
    stddev: float
    variance: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a time window"""

    test_run_id: str
    timestamp: datetime
    window_seconds: int
    operation_type: OperationType
    workload_type: WorkloadType

    operations: Dict[str, Any]
    duration_ms: StatisticalSummary
    throughput_mbps: StatisticalSummary
    object_size_bytes: Dict[str, float]
    request_rate: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "test_run_id": self.test_run_id,
            "timestamp": self.timestamp.isoformat(),
            "window_seconds": self.window_seconds,
            "operation_type": self.operation_type.value,
            "workload_type": self.workload_type.value,
            "operations": self.operations,
            "duration_ms": asdict(self.duration_ms),
            "throughput_mbps": asdict(self.throughput_mbps),
            "object_size_bytes": self.object_size_bytes,
            "request_rate": self.request_rate,
        }
        return data


@dataclass
class SystemResourceMetric:
    """System resource usage metrics"""

    timestamp: datetime
    test_run_id: str
    client_id: str

    cpu_usage_percent: float
    cpu_user_percent: float
    cpu_system_percent: float
    cpu_iowait_percent: float
    cpu_cores: int

    memory_used_mb: int
    memory_available_mb: int
    memory_total_mb: int
    memory_usage_percent: float

    network_bytes_sent: int
    network_bytes_received: int
    network_packets_sent: int
    network_packets_received: int
    network_errors: int
    network_drops: int

    disk_read_bytes: int
    disk_write_bytes: int
    disk_read_ops: int
    disk_write_ops: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class ErrorMetric:
    """Detailed error tracking"""

    timestamp: datetime
    test_run_id: str
    operation_id: str

    error_code: str
    error_type: str
    error_message: str
    error_category: ErrorCategory
    retryable: bool
    severity: str

    operation_type: OperationType
    object_key: str
    object_size_bytes: int
    retry_attempt: int
    elapsed_ms: float

    driver: str
    client_id: str
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["error_category"] = self.error_category.value
        data["operation_type"] = self.operation_type.value
        return data


@dataclass
class TestConfiguration:
    """Test run configuration and metadata"""

    test_run_id: str
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    scenario: str = ""
    workload_type: WorkloadType = WorkloadType.S3
    driver: str = ""

    test_config: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)
    client_info: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        data["workload_type"] = self.workload_type.value
        return data
