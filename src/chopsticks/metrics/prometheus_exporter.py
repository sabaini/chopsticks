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


"""Prometheus metrics exporter"""

from typing import Dict, List
from collections import defaultdict

from .models import OperationMetric


class PrometheusExporter:
    """Export metrics in Prometheus format"""

    def __init__(self, namespace: str = "chopsticks"):
        self.namespace = namespace
        self.metrics: dict[str, list[tuple[float, dict[str, str]]]] = defaultdict(list)

    def add_operation_metric(self, metric: OperationMetric):
        """Add an operation metric for export"""
        labels = {
            "operation": metric.operation_type.value,
            "workload": metric.workload_type.value,
            "driver": metric.driver,
            "success": str(metric.success).lower(),
        }

        self.metrics["operation_duration_seconds"].append(
            (metric.duration_ms / 1000, labels)
        )
        self.metrics["operation_size_bytes"].append((metric.object_size_bytes, labels))
        self.metrics["operation_throughput_mbps"].append(
            (metric.throughput_mbps, labels)
        )
        self.metrics["operation_total"].append((1, labels))

    def export(self) -> str:
        """Export metrics in Prometheus text format"""
        output = []

        # Operation duration histogram
        output.append(
            self._format_histogram(
                "operation_duration_seconds",
                "Duration of operations in seconds",
                "operation_duration_seconds",
                [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
                self.metrics["operation_duration_seconds"],
            )
        )

        # Operation size histogram
        output.append(
            self._format_histogram(
                "operation_size_bytes",
                "Size of operations in bytes",
                "operation_size_bytes",
                [1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824],
                self.metrics["operation_size_bytes"],
            )
        )

        # Throughput gauge
        output.append(
            self._format_gauge(
                "operation_throughput_mbps",
                "Operation throughput in MB/s",
                self.metrics["operation_throughput_mbps"],
            )
        )

        # Operation counter
        output.append(
            self._format_counter(
                "operation_total",
                "Total number of operations",
                self.metrics["operation_total"],
            )
        )

        return "\n".join(output)

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus"""
        if not labels:
            return ""
        label_strs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_strs) + "}"

    def _format_histogram(
        self,
        name: str,
        help_text: str,
        metric_name: str,
        buckets: List[float],
        values: List[tuple],
    ) -> str:
        """Format histogram metric"""
        full_name = f"{self.namespace}_{metric_name}"
        lines = [f"# HELP {full_name} {help_text}", f"# TYPE {full_name} histogram"]

        # Group by labels
        by_labels = defaultdict(list)
        for value, labels in values:
            label_str = self._format_labels(labels)
            by_labels[label_str].append(value)

        # Create histogram buckets
        for label_str, vals in by_labels.items():
            sorted_vals = sorted(vals)

            for bucket in buckets:
                count = sum(1 for v in sorted_vals if v <= bucket)
                bucket_labels = (
                    label_str[:-1] + f',le="{bucket}"' + "}"
                    if label_str.endswith("}")
                    else f'{{le="{bucket}"}}'
                )
                lines.append(f"{full_name}_bucket{bucket_labels} {count}")

            inf_labels = (
                label_str[:-1] + ',le="+Inf"' + "}"
                if label_str.endswith("}")
                else '{le="+Inf"}'
            )
            lines.append(f"{full_name}_bucket{inf_labels} {len(vals)}")
            lines.append(f"{full_name}_sum{label_str} {sum(vals)}")
            lines.append(f"{full_name}_count{label_str} {len(vals)}")

        return "\n".join(lines)

    def _format_gauge(self, name: str, help_text: str, values: List[tuple]) -> str:
        """Format gauge metric"""
        full_name = f"{self.namespace}_{name}"
        lines = [f"# HELP {full_name} {help_text}", f"# TYPE {full_name} gauge"]

        # Use most recent value for each label set
        by_labels = {}
        for value, labels in values:
            label_str = self._format_labels(labels)
            by_labels[label_str] = value

        for label_str, value in by_labels.items():
            lines.append(f"{full_name}{label_str} {value}")

        return "\n".join(lines)

    def _format_counter(self, name: str, help_text: str, values: List[tuple]) -> str:
        """Format counter metric"""
        full_name = f"{self.namespace}_{name}"
        lines = [f"# HELP {full_name} {help_text}", f"# TYPE {full_name} counter"]

        # Sum values by label set
        by_labels: dict[str, int] = defaultdict(int)
        for value, labels in values:
            label_str = self._format_labels(labels)
            by_labels[label_str] += value

        for label_str, total in by_labels.items():
            lines.append(f"{full_name}{label_str} {total}")

        return "\n".join(lines)

    def export_to_file(self, output_path: str):
        """Export to file"""
        with open(output_path, "w") as f:
            f.write(self.export())
