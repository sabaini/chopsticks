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


"""Unit tests for metrics module."""

from datetime import datetime, timedelta
from chopsticks.metrics import (
    OperationMetric,
    OperationType,
    WorkloadType,
    MetricsCollector,
    TestConfiguration,
)


class TestOperationMetric:
    """Tests for OperationMetric model."""

    def test_metric_creation(self):
        """Test creating a basic metric."""
        start = datetime.utcnow()
        end = start + timedelta(seconds=1)

        metric = OperationMetric(
            operation_id="test-123",
            timestamp_start=start,
            timestamp_end=end,
            operation_type=OperationType.UPLOAD,
            workload_type=WorkloadType.S3,
            object_key="test-object",
            object_size_bytes=1024,
            duration_ms=1000.0,
            throughput_mbps=0.001,
            success=True,
            driver="s5cmd",
        )

        assert metric.operation_id == "test-123"
        assert metric.operation_type == OperationType.UPLOAD
        assert metric.success is True
        assert metric.object_size_bytes == 1024

    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        start = datetime.utcnow()
        end = start + timedelta(milliseconds=500)

        metric = OperationMetric(
            operation_id="test-dict",
            timestamp_start=start,
            timestamp_end=end,
            operation_type=OperationType.DOWNLOAD,
            workload_type=WorkloadType.S3,
            object_key="test-key",
            object_size_bytes=2048,
            duration_ms=500.0,
            throughput_mbps=0.004,
            success=True,
            driver="s5cmd",
        )

        data = metric.to_dict()
        assert data["operation_id"] == "test-dict"
        assert data["operation_type"] == "download"
        assert data["workload_type"] == "s3"
        assert isinstance(data["timestamp_start"], str)


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_collector_initialization(self, sample_test_config):
        """Test collector can be initialized."""
        collector = MetricsCollector(
            test_run_id="test-123",
            test_config=sample_test_config,
        )
        assert collector is not None
        assert len(collector.operation_metrics) == 0

    def test_record_operation(self, sample_test_config):
        """Test recording a single operation."""
        collector = MetricsCollector(
            test_run_id="test-123",
            test_config=sample_test_config,
        )

        start = datetime.utcnow()
        end = start + timedelta(seconds=1)

        metric = OperationMetric(
            operation_id="test-record",
            timestamp_start=start,
            timestamp_end=end,
            operation_type=OperationType.UPLOAD,
            workload_type=WorkloadType.S3,
            object_key="test-key",
            object_size_bytes=1024,
            duration_ms=1000.0,
            throughput_mbps=0.001,
            success=True,
            driver="s5cmd",
        )

        collector.record_operation(metric)
        assert len(collector.operation_metrics) == 1
        assert collector.operation_metrics[0].operation_id == "test-record"

    def test_multiple_operations(self, sample_test_config):
        """Test recording multiple operations."""
        collector = MetricsCollector(
            test_run_id="test-123",
            test_config=sample_test_config,
        )

        for i in range(5):
            start = datetime.utcnow()
            end = start + timedelta(seconds=1)

            metric = OperationMetric(
                operation_id=f"test-{i}",
                timestamp_start=start,
                timestamp_end=end,
                operation_type=OperationType.UPLOAD,
                workload_type=WorkloadType.S3,
                object_key=f"key-{i}",
                object_size_bytes=1024,
                duration_ms=1000.0,
                throughput_mbps=0.001,
                success=True,
                driver="s5cmd",
            )
            collector.record_operation(metric)

        assert len(collector.operation_metrics) == 5

    def test_success_failure_tracking(self, sample_test_config):
        """Test tracking successful and failed operations."""
        collector = MetricsCollector(
            test_run_id="test-123",
            test_config=sample_test_config,
        )

        for idx, success in enumerate([True, True, False, True]):
            start = datetime.utcnow()
            end = start + timedelta(seconds=1)

            metric = OperationMetric(
                operation_id=f"test-{idx}",
                timestamp_start=start,
                timestamp_end=end,
                operation_type=OperationType.UPLOAD,
                workload_type=WorkloadType.S3,
                object_key=f"key-{idx}",
                object_size_bytes=1024,
                duration_ms=1000.0,
                throughput_mbps=0.001,
                success=success,
                driver="s5cmd",
            )
            collector.record_operation(metric)

        assert len(collector.operation_metrics) == 4
        successful = sum(1 for m in collector.operation_metrics if m.success)
        assert successful == 3


class TestTestConfiguration:
    """Tests for TestConfiguration model."""

    def test_config_creation(self):
        """Test creating test configuration."""
        start_time = datetime.utcnow()
        config = TestConfiguration(
            test_run_id="config-test",
            test_name="Test Configuration",
            start_time=start_time,
            scenario="s3_large_objects",
            workload_type=WorkloadType.S3,
            driver="s5cmd",
        )

        assert config.test_run_id == "config-test"
        assert config.test_name == "Test Configuration"
        assert config.workload_type == WorkloadType.S3

    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        start_time = datetime.utcnow()
        config = TestConfiguration(
            test_run_id="config-test",
            test_name="Test",
            start_time=start_time,
            workload_type=WorkloadType.S3,
        )

        data = config.to_dict()
        assert data["test_run_id"] == "config-test"
        assert data["workload_type"] == "s3"
        assert isinstance(data["start_time"], str)
