"""S3 Large Object Stress Test with Metrics Collection"""

import os
import random
from datetime import datetime
from locust import task, between, events
import uuid

from chopsticks.workloads.s3.s3_workload import S3Workload
from chopsticks.metrics import (
    MetricsCollector,
    TestConfiguration,
    OperationMetric,
    OperationType,
    WorkloadType,
)
from chopsticks.metrics.http_server import MetricsHTTPServer


# Global metrics server and collector
metrics_server = None
metrics_collector = None
test_config = None


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize metrics collection when Locust starts"""
    global metrics_server, metrics_collector, test_config

    # Create test configuration
    test_config = TestConfiguration(
        test_run_id=str(uuid.uuid4()),
        test_name="S3 Large Objects with Metrics",
        start_time=datetime.utcnow(),
        scenario="s3_large_objects_with_metrics",
        workload_type=WorkloadType.S3,
        test_config={
            "object_size_mb": int(os.getenv("LARGE_OBJECT_SIZE", "100")),
            "users": environment.parsed_options.num_users
            if hasattr(environment, "parsed_options")
            else 1,
        },
    )

    # Initialize metrics collector
    metrics_collector = MetricsCollector(
        test_run_id=test_config.test_run_id,
        test_config=test_config,
        aggregation_window_seconds=10,
    )

    # Start metrics HTTP server
    metrics_server = MetricsHTTPServer(host="0.0.0.0", port=8090)
    metrics_server.start()

    print(f"\n{'=' * 70}")
    print("Metrics Collection Initialized")
    print(f"{'=' * 70}")
    print(f"Test Run ID: {test_config.test_run_id}")
    print("Chopsticks Metrics Endpoint: http://0.0.0.0:8090/metrics")
    print(f"{'=' * 70}\n")


@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Export metrics when Locust quits"""
    global metrics_server, metrics_collector, test_config

    if metrics_collector:
        # Update test end time
        test_config.end_time = datetime.utcnow()
        test_config.duration_seconds = int(
            (test_config.end_time - test_config.start_time).total_seconds()
        )

        # Export metrics to run directory if set, otherwise use default
        output_dir = os.environ.get("CHOPSTICKS_RUN_DIR", "/tmp/chopsticks_metrics")
        os.makedirs(output_dir, exist_ok=True)

        metrics_collector.export_json(
            f"{output_dir}/metrics.json"
        )
        metrics_collector.export_csv(
            f"{output_dir}/metrics.csv"
        )
        metrics_collector.export_jsonl(
            f"{output_dir}/metrics.jsonl"
        )

        # Get summary
        summary = metrics_collector.get_summary()

        print(f"\n{'=' * 70}")
        print("Metrics Collection Summary")
        print(f"{'=' * 70}")
        print(f"Total Operations: {summary['operations']['total']}")
        print(f"Success Rate: {summary['operations']['success_rate']:.2f}%")
        print(f"Metrics exported to: {output_dir}")
        print(f"{'=' * 70}\n")

    if metrics_server:
        metrics_server.stop()


class S3LargeObjectsWithMetrics(S3Workload):
    """
    S3 stress test for large objects with comprehensive metrics collection.

    This test uploads, downloads, and deletes large objects while collecting
    detailed performance metrics including:
    - Per-operation latency and throughput
    - Statistical aggregations (percentiles, mean, stddev)
    - Success/failure rates
    - Error tracking

    The metrics are exposed via Prometheus endpoint at http://localhost:9090/metrics
    and also exported as JSON/CSV files at the end of the test.

    Environment Variables:
        LARGE_OBJECT_SIZE: Size of objects in MB (default: 100)
    """

    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_size_mb = int(os.getenv("LARGE_OBJECT_SIZE", "100"))
        self.object_size = self.object_size_mb * 1024 * 1024
        self.uploaded_keys = []

    def _record_metric(
        self,
        operation_type: OperationType,
        key: str,
        size_bytes: int,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        error_code: str | None = None,
        error_msg: str | None = None,
    ):
        """Record operation metric"""
        global metrics_collector, metrics_server

        duration_ms = (end_time - start_time).total_seconds() * 1000
        throughput_mbps = (
            (size_bytes / 1024 / 1024) / (duration_ms / 1000) if duration_ms > 0 else 0
        )

        metric = OperationMetric(
            operation_id=str(uuid.uuid4()),
            timestamp_start=start_time,
            timestamp_end=end_time,
            operation_type=operation_type,
            workload_type=WorkloadType.S3,
            object_key=key,
            object_size_bytes=size_bytes,
            duration_ms=duration_ms,
            throughput_mbps=throughput_mbps,
            success=success,
            error_code=error_code,
            error_message=error_msg,
            driver="s5cmd",
            user_id=str(id(self)),
        )

        if metrics_collector:
            metrics_collector.record_operation(metric)

        if metrics_server:
            metrics_server.get_exporter().add_operation_metric(metric)

    @task(3)
    def upload_large_object(self):
        """Upload a large object"""
        key = self.generate_key(f"large-{self.object_size_mb}mb")
        data = self.generate_data(self.object_size)

        start_time = datetime.utcnow()
        try:
            self.client.upload(key, data)
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.UPLOAD, key, self.object_size, start_time, end_time, True
            )
            self.uploaded_keys.append(key)
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.UPLOAD,
                key,
                self.object_size,
                start_time,
                end_time,
                False,
                error_code=type(e).__name__,
                error_msg=str(e),
            )
            raise

    @task(2)
    def download_large_object(self):
        """Download a previously uploaded object"""
        if not self.uploaded_keys:
            return

        key = random.choice(self.uploaded_keys)

        start_time = datetime.utcnow()
        try:
            data = self.client.download(key)
            end_time = datetime.utcnow()

            # Check if download was successful
            if data is None:
                self._record_metric(
                    OperationType.DOWNLOAD,
                    key,
                    0,
                    start_time,
                    end_time,
                    False,
                    error_code="DownloadFailed",
                    error_msg="Download returned None",
                )
                raise Exception("Download failed: returned None")

            self._record_metric(
                OperationType.DOWNLOAD, key, len(data), start_time, end_time, True
            )

            # Verify data size
            if len(data) != self.object_size:
                print(
                    f"Warning: Downloaded size {len(data)} != expected {self.object_size}"
                )
        except Exception as e:
            end_time = datetime.utcnow()
            # Only record metric if not already recorded
            if data is not None or "Download failed" not in str(e):
                self._record_metric(
                    OperationType.DOWNLOAD,
                    key,
                    0,
                    start_time,
                    end_time,
                    False,
                    error_code=type(e).__name__,
                    error_msg=str(e),
                )
            raise

    @task(1)
    def delete_object(self):
        """Delete an uploaded object"""
        if not self.uploaded_keys:
            return

        key = self.uploaded_keys.pop(0)

        start_time = datetime.utcnow()
        try:
            self.client.delete(key)
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.DELETE, key, 0, start_time, end_time, True
            )
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.DELETE,
                key,
                0,
                start_time,
                end_time,
                False,
                error_code=type(e).__name__,
                error_msg=str(e),
            )
            raise
