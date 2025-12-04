"""Base workload with optional metrics collection support"""

import os
import uuid
from datetime import datetime
from typing import Optional
from locust import events

from chopsticks.metrics import (
    MetricsCollector,
    TestConfiguration,
    OperationMetric,
    OperationType,
    WorkloadType,
)
from chopsticks.metrics.http_server import MetricsHTTPServer


# Global metrics instances (shared across all workload instances)
_metrics_server: Optional[MetricsHTTPServer] = None
_metrics_collector: Optional[MetricsCollector] = None
_test_config: Optional[TestConfiguration] = None
_metrics_enabled = False


def load_workload_config() -> dict:
    """
    Load workload configuration to check metrics settings.

    Tries to load config from CHOPSTICKS_WORKLOAD_CONFIG environment variable.
    Falls back to checking various *_CONFIG_PATH variables.
    """
    from chopsticks.utils.config_loader import load_config

    # Try generic workload config first
    config_path = os.environ.get("CHOPSTICKS_WORKLOAD_CONFIG")
    if config_path and os.path.exists(config_path):
        return load_config(config_path)

    # Try S3_CONFIG_PATH
    config_path = os.environ.get("S3_CONFIG_PATH")
    if config_path and os.path.exists(config_path):
        return load_config(config_path)

    # Try RBD_CONFIG_PATH
    config_path = os.environ.get("RBD_CONFIG_PATH")
    if config_path and os.path.exists(config_path):
        return load_config(config_path)

    return {}


def get_metrics_config(workload_config: dict) -> dict:
    """
    Get metrics configuration from workload config file.

    Looks for 'metrics' section in workload config.
    Falls back to environment variables if not found.

    Args:
        workload_config: Loaded workload configuration

    Returns:
        Dictionary with metrics configuration
    """
    metrics_section = workload_config.get("metrics", {})

    return {
        "enabled": metrics_section.get(
            "enabled",
            os.environ.get("CHOPSTICKS_ENABLE_METRICS", "false").lower()
            in ("true", "1", "yes"),
        ),
        "http_host": metrics_section.get(
            "http_host", os.environ.get("CHOPSTICKS_METRICS_HOST", "0.0.0.0")
        ),
        "http_port": int(
            metrics_section.get(
                "http_port", os.environ.get("CHOPSTICKS_METRICS_PORT", "8090")
            )
        ),
        "aggregation_window": int(
            metrics_section.get(
                "aggregation_window_seconds",
                os.environ.get("CHOPSTICKS_METRICS_WINDOW", "10"),
            )
        ),
        "export_dir": metrics_section.get(
            "export_dir",
            os.environ.get("CHOPSTICKS_RUN_DIR", "/tmp/chopsticks_metrics"),
        ),
        "test_name": metrics_section.get(
            "test_name", os.environ.get("CHOPSTICKS_TEST_NAME", "Chopsticks Load Test")
        ),
    }


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize metrics collection when Locust starts"""
    global _metrics_server, _metrics_collector, _test_config, _metrics_enabled

    # Load workload config to check metrics settings
    workload_config = load_workload_config()
    config = get_metrics_config(workload_config)

    _metrics_enabled = config["enabled"]

    if not _metrics_enabled:
        return

    # Create test configuration
    _test_config = TestConfiguration(
        test_run_id=str(uuid.uuid4()),
        test_name=config["test_name"],
        start_time=datetime.utcnow(),
        scenario=os.environ.get("CHOPSTICKS_SCENARIO", "unknown"),
        workload_type=WorkloadType.S3,  # Will be overridden by specific workload
        test_config={
            "users": environment.parsed_options.num_users
            if hasattr(environment, "parsed_options")
            else 1,
        },
    )

    # Initialize metrics collector
    _metrics_collector = MetricsCollector(
        test_run_id=_test_config.test_run_id,
        test_config=_test_config,
        aggregation_window_seconds=config["aggregation_window"],
    )

    # Start metrics HTTP server
    _metrics_server = MetricsHTTPServer(
        host=config["http_host"], port=config["http_port"]
    )
    _metrics_server.start()

    print(f"\n{'=' * 70}")
    print("Metrics Collection Enabled")
    print(f"{'=' * 70}")
    print(f"Test Run ID: {_test_config.test_run_id}")
    print(
        f"Metrics Endpoint: http://{config['http_host']}:{config['http_port']}/metrics"
    )
    print(f"Export Directory: {config['export_dir']}")
    print(f"{'=' * 70}\n")


@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Export metrics when Locust quits"""
    global _metrics_server, _metrics_collector, _test_config, _metrics_enabled

    if not _metrics_enabled or not _metrics_collector:
        return

    # Reload config for export directory
    workload_config = load_workload_config()
    config = get_metrics_config(workload_config)

    # Update test end time
    _test_config.end_time = datetime.utcnow()
    _test_config.duration_seconds = int(
        (_test_config.end_time - _test_config.start_time).total_seconds()
    )

    # Export metrics
    output_dir = config["export_dir"]
    os.makedirs(output_dir, exist_ok=True)

    _metrics_collector.export_json(f"{output_dir}/metrics.json")
    _metrics_collector.export_csv(f"{output_dir}/metrics.csv")
    _metrics_collector.export_jsonl(f"{output_dir}/metrics.jsonl")

    # Get summary
    summary = _metrics_collector.get_summary()

    print(f"\n{'=' * 70}")
    print("Metrics Collection Summary")
    print(f"{'=' * 70}")
    print(f"Total Operations: {summary['operations']['total']}")
    print(f"Success Rate: {summary['operations']['success_rate']:.2f}%")
    print(f"Metrics exported to: {output_dir}")
    print(f"{'=' * 70}\n")

    if _metrics_server:
        _metrics_server.stop()


class BaseMetricsWorkload:
    """Mixin class for workloads with metrics collection support"""

    workload_type: WorkloadType = WorkloadType.S3

    def get_metrics_collector(self) -> Optional[MetricsCollector]:
        """Get the global metrics collector instance"""
        return _metrics_collector if _metrics_enabled else None

    def get_metrics_server(self) -> Optional[MetricsHTTPServer]:
        """Get the global metrics HTTP server instance"""
        return _metrics_server if _metrics_enabled else None

    def record_operation_metric(
        self,
        operation_type: OperationType,
        key: str,
        size_bytes: int,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        error_code: Optional[str] = None,
        error_msg: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Record an operation metric.

        This is the base implementation that handles metrics collection.
        Scenarios can override _record_metric() to customize behavior.
        """
        if not _metrics_enabled:
            return

        duration_ms = (end_time - start_time).total_seconds() * 1000
        throughput_mbps = (
            (size_bytes / 1024 / 1024) / (duration_ms / 1000) if duration_ms > 0 else 0
        )

        metric = OperationMetric(
            operation_id=str(uuid.uuid4()),
            timestamp_start=start_time,
            timestamp_end=end_time,
            operation_type=operation_type,
            workload_type=self.workload_type,
            object_key=key,
            object_size_bytes=size_bytes,
            duration_ms=duration_ms,
            throughput_mbps=throughput_mbps,
            success=success,
            error_code=error_code,
            error_message=error_msg,
            driver=getattr(self, "driver_name", "unknown"),
            user_id=str(id(self)),
            metadata=metadata or {},
        )

        # Record to collector
        if _metrics_collector:
            _metrics_collector.record_operation(metric)

        # Record to Prometheus exporter
        if _metrics_server:
            _metrics_server.get_exporter().add_operation_metric(metric)

    def _record_metric(
        self,
        operation_type: OperationType,
        key: str,
        size_bytes: int,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        error_code: Optional[str] = None,
        error_msg: Optional[str] = None,
        **kwargs,
    ):
        """
        Hook for scenarios to customize metric recording.

        Scenarios can override this method to add custom logic or metadata.
        By default, it calls record_operation_metric().
        """
        self.record_operation_metric(
            operation_type=operation_type,
            key=key,
            size_bytes=size_bytes,
            start_time=start_time,
            end_time=end_time,
            success=success,
            error_code=error_code,
            error_msg=error_msg,
            metadata=kwargs,
        )
