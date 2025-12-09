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


"""Metrics collection and aggregation"""

import statistics
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .models import (
    OperationMetric,
    AggregatedMetrics,
    StatisticalSummary,
    SystemResourceMetric,
    ErrorMetric,
    TestConfiguration,
    OperationType,
)


class MetricsCollector:
    """Collect and aggregate performance metrics"""

    def __init__(
        self,
        test_run_id: str,
        test_config: TestConfiguration,
        aggregation_window_seconds: int = 10,
    ):
        self.test_run_id = test_run_id
        self.test_config = test_config
        self.aggregation_window = aggregation_window_seconds

        self.operation_metrics: List[OperationMetric] = []
        self.system_metrics: List[SystemResourceMetric] = []
        self.error_metrics: List[ErrorMetric] = []

        self._window_start = datetime.utcnow()
        self._current_window_metrics: list[OperationMetric] = []

    def record_operation(self, metric: OperationMetric):
        """Record a single operation metric"""
        self.operation_metrics.append(metric)
        self._current_window_metrics.append(metric)

        # Check if we need to aggregate
        if (
            datetime.utcnow() - self._window_start
        ).total_seconds() >= self.aggregation_window:
            self._aggregate_current_window()

    def record_system_metric(self, metric: SystemResourceMetric):
        """Record system resource usage"""
        self.system_metrics.append(metric)

    def record_error(self, metric: ErrorMetric):
        """Record an error"""
        self.error_metrics.append(metric)

    def _aggregate_current_window(self) -> List[AggregatedMetrics]:
        """Aggregate metrics for current time window"""
        if not self._current_window_metrics:
            return []

        # Group by operation type
        by_operation = defaultdict(list)
        for metric in self._current_window_metrics:
            by_operation[metric.operation_type].append(metric)

        # Aggregate each operation type
        aggregated = []
        for op_type, metrics in by_operation.items():
            agg = self._compute_aggregation(metrics, op_type)
            if agg:
                aggregated.append(agg)

        # Reset window
        self._window_start = datetime.utcnow()
        self._current_window_metrics = []

        return aggregated

    def _compute_aggregation(
        self, metrics: List[OperationMetric], operation_type: OperationType
    ) -> Optional[AggregatedMetrics]:
        """Compute aggregated metrics for a list of operations"""
        if not metrics:
            return None

        successful_metrics = [m for m in metrics if m.success]

        if not successful_metrics:
            return None

        durations = [m.duration_ms for m in successful_metrics]
        throughputs = [m.throughput_mbps for m in successful_metrics]
        sizes = [m.object_size_bytes for m in metrics]

        return AggregatedMetrics(
            test_run_id=self.test_run_id,
            timestamp=datetime.utcnow(),
            window_seconds=self.aggregation_window,
            operation_type=operation_type,
            workload_type=metrics[0].workload_type,
            operations={
                "total": len(metrics),
                "successful": len(successful_metrics),
                "failed": len(metrics) - len(successful_metrics),
                "success_rate": (len(successful_metrics) / len(metrics)) * 100,
            },
            duration_ms=self._compute_statistics(durations),
            throughput_mbps=self._compute_statistics(throughputs),
            object_size_bytes={
                "min": min(sizes),
                "max": max(sizes),
                "mean": statistics.mean(sizes),
                "total": float(sum(sizes)),
            },
            request_rate={
                "rps": len(metrics) / self.aggregation_window,
                "rpm": (len(metrics) / self.aggregation_window) * 60,
            },
        )

    def _compute_statistics(self, data: List[float]) -> StatisticalSummary:
        """Compute statistical summary"""
        if not data:
            return StatisticalSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        sorted_data = sorted(data)

        return StatisticalSummary(
            min=min(data),
            max=max(data),
            mean=statistics.mean(data),
            median=statistics.median(data),
            p50=self._percentile(sorted_data, 50),
            p75=self._percentile(sorted_data, 75),
            p90=self._percentile(sorted_data, 90),
            p95=self._percentile(sorted_data, 95),
            p99=self._percentile(sorted_data, 99),
            p99_9=self._percentile(sorted_data, 99.9),
            stddev=statistics.stdev(data) if len(data) > 1 else 0,
            variance=statistics.variance(data) if len(data) > 1 else 0,
        )

    def _percentile(self, sorted_data: List[float], percentile: float) -> float:
        """Calculate percentile from sorted data"""
        if not sorted_data:
            return 0.0

        index = (len(sorted_data) - 1) * (percentile / 100)
        lower = int(index)
        upper = lower + 1

        if upper >= len(sorted_data):
            return sorted_data[-1]

        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    def get_summary(self) -> Dict[str, Any]:
        """Get overall test summary"""
        if not self.operation_metrics:
            return {}

        total_operations = len(self.operation_metrics)
        successful = sum(1 for m in self.operation_metrics if m.success)
        failed = total_operations - successful

        durations = [m.duration_ms for m in self.operation_metrics if m.success]
        throughputs = [m.throughput_mbps for m in self.operation_metrics if m.success]

        # Group by operation type
        by_operation = defaultdict(list)
        for metric in self.operation_metrics:
            by_operation[metric.operation_type].append(metric)

        operation_summaries = {}
        for op_type, metrics in by_operation.items():
            successful_ops = [m for m in metrics if m.success]
            if successful_ops:
                op_durations = [m.duration_ms for m in successful_ops]
                op_throughputs = [m.throughput_mbps for m in successful_ops]

                operation_summaries[op_type.value] = {
                    "count": len(metrics),
                    "success_rate": (len(successful_ops) / len(metrics)) * 100,
                    "duration_ms": {
                        "mean": statistics.mean(op_durations),
                        "p95": self._percentile(sorted(op_durations), 95),
                        "p99": self._percentile(sorted(op_durations), 99),
                    },
                    "throughput_mbps": {
                        "mean": statistics.mean(op_throughputs),
                        "max": max(op_throughputs),
                    },
                }

        return {
            "test_run_id": self.test_run_id,
            "test_name": self.test_config.test_name,
            "start_time": self.test_config.start_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "operations": {
                "total": total_operations,
                "successful": successful,
                "failed": failed,
                "success_rate": (
                    (successful / total_operations) * 100 if total_operations > 0 else 0
                ),
            },
            "overall_performance": {
                "duration_ms": (
                    self._compute_statistics(durations).to_dict() if durations else {}
                ),
                "throughput_mbps": (
                    self._compute_statistics(throughputs).to_dict()
                    if throughputs
                    else {}
                ),
            },
            "by_operation": operation_summaries,
            "errors": {
                "count": len(self.error_metrics),
                "by_category": self._group_errors_by_category(),
            },
        }

    def _group_errors_by_category(self) -> Dict[str, int]:
        """Group errors by category"""
        categories: dict[str, int] = defaultdict(int)
        for error in self.error_metrics:
            categories[error.error_category.value] += 1
        return dict(categories)

    def export_json(self, output_path: Path):
        """Export all metrics as JSON"""
        data = {
            "test_config": self.test_config.to_dict(),
            "summary": self.get_summary(),
            "operation_metrics": [m.to_dict() for m in self.operation_metrics],
            "system_metrics": [m.to_dict() for m in self.system_metrics],
            "error_metrics": [m.to_dict() for m in self.error_metrics],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def export_jsonl(self, output_path: Path):
        """Export operations as JSON Lines"""
        with open(output_path, "w") as f:
            for metric in self.operation_metrics:
                f.write(json.dumps(metric.to_dict(), default=str) + "\n")

    def export_csv(self, output_path: Path):
        """Export operations as CSV"""
        if not self.operation_metrics:
            return

        fieldnames = [
            "operation_id",
            "timestamp_start",
            "timestamp_end",
            "operation_type",
            "workload_type",
            "object_key",
            "object_size_bytes",
            "duration_ms",
            "throughput_mbps",
            "success",
            "error_code",
            "retry_count",
            "driver",
            "user_id",
        ]

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for metric in self.operation_metrics:
                row = metric.to_dict()
                writer.writerow(row)
