# Chopsticks Metrics Collection Standard

## Overview

This document defines a comprehensive standard for collecting, storing, and analyzing performance metrics from Ceph stress testing workloads. The metrics system is designed to provide deep insights into cluster performance, identify bottlenecks, and enable data-driven optimization decisions.

## Design Principles

1. **Comprehensive**: Capture all relevant performance indicators
2. **Standardized**: Consistent format across workloads (S3, RBD, etc.)
3. **Efficient**: Minimal overhead on test execution
4. **Exportable**: Support multiple output formats (JSON, CSV, Prometheus, etc.)
5. **Analyzable**: Enable statistical analysis and visualization
6. **Timestamped**: All metrics with precise timestamps for correlation
7. **Contextual**: Include test configuration and environment metadata

## Metric Categories

### 1. **Operation Metrics** (Per-Operation Level)

Track individual I/O operation performance.

```json
{
  "operation_id": "uuid-v4",
  "timestamp_start": "2025-12-03T09:30:45.123456Z",
  "timestamp_end": "2025-12-03T09:30:45.234567Z",
  "operation_type": "upload|download|delete|list|head|read|write",
  "workload_type": "s3|rbd",
  "object_key": "test/object-123",
  "object_size_bytes": 104857600,
  "duration_ms": 111.111,
  "throughput_mbps": 900.45,
  "success": true,
  "error_code": null,
  "error_message": null,
  "retry_count": 0,
  "driver": "s5cmd|boto3|librbd",
  "user_id": "user-1",
  "metadata": {
    "multipart": false,
    "part_size_bytes": null,
    "encryption": false,
    "compression": false
  }
}
```

**Key Metrics:**
- `duration_ms`: Total operation time in milliseconds
- `throughput_mbps`: Calculated as `(object_size_bytes / 1024 / 1024) / (duration_ms / 1000)`
- `success`: Boolean operation outcome
- `retry_count`: Number of retries before success/failure

### 2. **Aggregated Metrics** (Per-Test-Run Level)

Statistical summaries computed over time windows.

```json
{
  "test_run_id": "uuid-v4",
  "timestamp": "2025-12-03T09:30:00.000000Z",
  "window_seconds": 10,
  "operation_type": "upload",
  "workload_type": "s3",
  
  "operations": {
    "total": 150,
    "successful": 148,
    "failed": 2,
    "success_rate": 98.67
  },
  
  "duration_ms": {
    "min": 85.5,
    "max": 523.8,
    "mean": 156.3,
    "median": 142.7,
    "p50": 142.7,
    "p75": 178.2,
    "p90": 234.5,
    "p95": 312.8,
    "p99": 487.3,
    "p99.9": 523.8,
    "stddev": 67.8,
    "variance": 4596.84
  },
  
  "throughput_mbps": {
    "min": 180.2,
    "max": 1024.5,
    "mean": 612.3,
    "median": 598.7,
    "p50": 598.7,
    "p75": 723.4,
    "p90": 856.2,
    "p95": 912.7,
    "p99": 987.3,
    "p99.9": 1024.5,
    "total_mb": 15000.0,
    "total_gb": 14.65
  },
  
  "object_size_bytes": {
    "min": 104857600,
    "max": 104857600,
    "mean": 104857600,
    "total": 15728640000
  },
  
  "request_rate": {
    "rps": 15.0,
    "rpm": 900.0
  }
}
```

### 3. **System Resource Metrics** (Client-Side)

Monitor resource usage on load testing clients.

```json
{
  "timestamp": "2025-12-03T09:30:00.000000Z",
  "test_run_id": "uuid-v4",
  "client_id": "worker-1",
  
  "cpu": {
    "usage_percent": 45.3,
    "user_percent": 38.2,
    "system_percent": 7.1,
    "iowait_percent": 2.5,
    "cores": 8
  },
  
  "memory": {
    "used_mb": 2048,
    "available_mb": 6144,
    "total_mb": 8192,
    "usage_percent": 25.0,
    "swap_used_mb": 0
  },
  
  "network": {
    "bytes_sent": 15728640000,
    "bytes_received": 15728640000,
    "packets_sent": 125000,
    "packets_received": 125000,
    "errors_in": 0,
    "errors_out": 0,
    "drops_in": 0,
    "drops_out": 0
  },
  
  "disk_io": {
    "read_bytes": 0,
    "write_bytes": 524288000,
    "read_ops": 0,
    "write_ops": 12500
  }
}
```

### 4. **Ceph Cluster Metrics** (Server-Side)

Collect Ceph cluster health and performance indicators.

```json
{
  "timestamp": "2025-12-03T09:30:00.000000Z",
  "test_run_id": "uuid-v4",
  
  "cluster_health": {
    "status": "HEALTH_OK|HEALTH_WARN|HEALTH_ERR",
    "num_osds": 3,
    "num_osds_up": 3,
    "num_osds_in": 3,
    "num_pgs": 128,
    "num_pgs_active": 128,
    "num_pgs_clean": 128
  },
  
  "pool_stats": {
    "pool_name": ".rgw.buckets.data",
    "pool_id": 8,
    "objects": 150,
    "size_bytes": 15728640000,
    "size_gb": 14.65,
    "read_ops": 1250,
    "write_ops": 1500,
    "read_bytes": 10485760000,
    "write_bytes": 15728640000
  },
  
  "osd_stats": [
    {
      "osd_id": 0,
      "host": "ceph-test",
      "up": true,
      "in": true,
      "weight": 1.0,
      "used_bytes": 5242880000,
      "available_bytes": 15000000000,
      "utilization_percent": 25.9,
      "pgs": 42,
      "apply_latency_ms": 2.3,
      "commit_latency_ms": 3.1
    }
  ],
  
  "rgw_stats": {
    "num_requests": 150,
    "successful_requests": 148,
    "failed_requests": 2,
    "avg_latency_ms": 156.3
  }
}
```

### 5. **Network Metrics** (Connection Level)

Track network performance and quality.

```json
{
  "timestamp": "2025-12-03T09:30:00.000000Z",
  "test_run_id": "uuid-v4",
  "connection_id": "conn-1",
  
  "latency": {
    "rtt_min_ms": 0.5,
    "rtt_max_ms": 5.3,
    "rtt_mean_ms": 1.2,
    "rtt_stddev_ms": 0.8
  },
  
  "bandwidth": {
    "upload_mbps": 950.5,
    "download_mbps": 980.3,
    "utilization_percent": 95.0
  },
  
  "packet_stats": {
    "packets_sent": 125000,
    "packets_received": 125000,
    "packet_loss_percent": 0.01,
    "retransmissions": 12
  },
  
  "tcp_stats": {
    "connections_established": 50,
    "connections_closed": 48,
    "connection_errors": 0,
    "timeouts": 0
  }
}
```

### 6. **Error Metrics** (Failure Analysis)

Detailed error tracking for debugging.

```json
{
  "timestamp": "2025-12-03T09:30:45.123456Z",
  "test_run_id": "uuid-v4",
  "operation_id": "uuid-v4",
  
  "error": {
    "code": "503",
    "type": "ServiceUnavailable",
    "message": "Slow Down",
    "category": "rate_limiting|network|storage|authentication|unknown",
    "retryable": true,
    "severity": "error|warning|critical"
  },
  
  "context": {
    "operation_type": "upload",
    "object_key": "test/object-123",
    "object_size_bytes": 104857600,
    "retry_attempt": 2,
    "elapsed_ms": 5234.5
  },
  
  "stack_trace": "...",
  "driver": "s5cmd",
  "client_id": "worker-1"
}
```

### 7. **Test Configuration Metadata**

Contextual information about the test run.

```json
{
  "test_run_id": "uuid-v4",
  "test_name": "S3 Large Object Stress Test",
  "start_time": "2025-12-03T09:30:00.000000Z",
  "end_time": "2025-12-03T09:40:00.000000Z",
  "duration_seconds": 600,
  
  "test_config": {
    "scenario": "s3_large_objects",
    "workload_type": "s3",
    "driver": "s5cmd",
    "object_size_mb": 100,
    "num_users": 10,
    "spawn_rate": 2,
    "duration": "10m",
    "task_weights": {
      "upload": 3,
      "download": 2,
      "delete": 1
    }
  },
  
  "environment": {
    "ceph_version": "18.2.4",
    "deployment": "microceph",
    "num_osds": 3,
    "osd_type": "bluestore",
    "replication": 3,
    "pool": ".rgw.buckets.data",
    "rgw_endpoint": "http://10.240.47.47:80",
    "region": "default"
  },
  
  "client_info": {
    "num_workers": 5,
    "worker_cpu_cores": 8,
    "worker_memory_gb": 8,
    "worker_os": "Ubuntu 22.04",
    "network_bandwidth_gbps": 10
  },
  
  "tags": {
    "environment": "staging",
    "purpose": "performance_baseline",
    "ticket": "STOR-1234"
  }
}
```

## Metric Collection Implementation

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Locust Test Workers                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │ Worker N │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │           │
│       └─────────────┴─────────────┴─────────────┘           │
│                         │                                    │
│                    ┌────▼─────┐                             │
│                    │ Metrics  │                             │
│                    │Collector │                             │
│                    └────┬─────┘                             │
└─────────────────────────┼─────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │   Local   │  │Prometheus │  │ InfluxDB  │
    │   JSON    │  │  Exporter │  │ Exporter  │
    └───────────┘  └───────────┘  └───────────┘
          │               │               │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │   File    │  │Prometheus │  │ InfluxDB  │
    │  Storage  │  │  Server   │  │  Server   │
    └───────────┘  └───────────┘  └───────────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                    ┌─────▼─────┐
                    │  Grafana  │
                    │ Dashboard │
                    └───────────┘
```

### Python Implementation Sketch

```python
# src/chopsticks/metrics/collector.py
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import json
import statistics

@dataclass
class OperationMetric:
    """Single operation metric"""
    operation_id: str
    timestamp_start: datetime
    timestamp_end: datetime
    operation_type: str
    workload_type: str
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
    metadata: Dict[str, Any] = None

@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a time window"""
    test_run_id: str
    timestamp: datetime
    window_seconds: int
    operation_type: str
    workload_type: str
    operations: Dict[str, Any]
    duration_ms: Dict[str, float]
    throughput_mbps: Dict[str, float]
    object_size_bytes: Dict[str, int]
    request_rate: Dict[str, float]

class MetricsCollector:
    """Collect and aggregate metrics from test runs"""
    
    def __init__(self, test_run_id: str, export_format: str = "json"):
        self.test_run_id = test_run_id
        self.export_format = export_format
        self.operation_metrics = []
        self.aggregation_window = 10  # seconds
        
    def record_operation(self, metric: OperationMetric):
        """Record a single operation metric"""
        self.operation_metrics.append(metric)
        
    def aggregate_window(self, metrics: list) -> AggregatedMetrics:
        """Aggregate metrics for a time window"""
        durations = [m.duration_ms for m in metrics if m.success]
        throughputs = [m.throughput_mbps for m in metrics if m.success]
        sizes = [m.object_size_bytes for m in metrics]
        
        return AggregatedMetrics(
            test_run_id=self.test_run_id,
            timestamp=datetime.utcnow(),
            window_seconds=self.aggregation_window,
            operation_type=metrics[0].operation_type,
            workload_type=metrics[0].workload_type,
            operations={
                "total": len(metrics),
                "successful": sum(1 for m in metrics if m.success),
                "failed": sum(1 for m in metrics if not m.success),
                "success_rate": (sum(1 for m in metrics if m.success) / len(metrics)) * 100
            },
            duration_ms={
                "min": min(durations),
                "max": max(durations),
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "p95": self._percentile(durations, 95),
                "p99": self._percentile(durations, 99),
                "stddev": statistics.stdev(durations) if len(durations) > 1 else 0
            },
            throughput_mbps={
                "min": min(throughputs),
                "max": max(throughputs),
                "mean": statistics.mean(throughputs),
                "median": statistics.median(throughputs),
                "p95": self._percentile(throughputs, 95),
                "p99": self._percentile(throughputs, 99)
            },
            object_size_bytes={
                "min": min(sizes),
                "max": max(sizes),
                "mean": statistics.mean(sizes),
                "total": sum(sizes)
            },
            request_rate={
                "rps": len(metrics) / self.aggregation_window
            }
        )
    
    def _percentile(self, data: list, percentile: float) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def export(self, output_path: str):
        """Export metrics to file"""
        if self.export_format == "json":
            self._export_json(output_path)
        elif self.export_format == "csv":
            self._export_csv(output_path)
    
    def _export_json(self, output_path: str):
        """Export as JSON"""
        data = [asdict(m) for m in self.operation_metrics]
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
```

## Storage Formats

### JSON Lines (JSONL)
Append-only format for streaming metrics.

```jsonl
{"operation_id":"123","timestamp":"2025-12-03T09:30:45.123Z","operation_type":"upload",...}
{"operation_id":"124","timestamp":"2025-12-03T09:30:46.234Z","operation_type":"download",...}
```

### CSV
For spreadsheet analysis and compatibility.

```csv
operation_id,timestamp_start,timestamp_end,operation_type,object_size_bytes,duration_ms,throughput_mbps,success
123,2025-12-03T09:30:45.123Z,2025-12-03T09:30:45.234Z,upload,104857600,111.0,900.45,true
```

### Prometheus Format
For time-series monitoring.

```prometheus
# HELP chopsticks_operation_duration_seconds Duration of operations in seconds
# TYPE chopsticks_operation_duration_seconds histogram
chopsticks_operation_duration_seconds_bucket{operation="upload",workload="s3",le="0.1"} 5
chopsticks_operation_duration_seconds_bucket{operation="upload",workload="s3",le="0.5"} 45
chopsticks_operation_duration_seconds_sum{operation="upload",workload="s3"} 156.3
chopsticks_operation_duration_seconds_count{operation="upload",workload="s3"} 150
```

## Key Performance Indicators (KPIs)

### Primary KPIs

1. **Throughput**: MB/s or operations/sec
2. **Latency**: p50, p95, p99 response times
3. **Success Rate**: Percentage of successful operations
4. **IOPS**: I/O operations per second
5. **Concurrency**: Concurrent operations handled

### Derived KPIs

1. **Efficiency**: Throughput / CPU usage
2. **Stability**: Latency standard deviation
3. **Reliability**: Mean time between failures (MTBF)
4. **Scalability**: Throughput vs. concurrency curve
5. **Cost-Performance**: Operations per resource unit

## Analysis and Reporting

### Statistical Analysis

```python
def analyze_performance(metrics: list):
    """Analyze performance characteristics"""
    return {
        "throughput": {
            "mean": statistics.mean([m.throughput_mbps for m in metrics]),
            "trend": calculate_trend([m.throughput_mbps for m in metrics])
        },
        "latency": {
            "p95": percentile([m.duration_ms for m in metrics], 95),
            "stability": statistics.stdev([m.duration_ms for m in metrics])
        },
        "bottlenecks": identify_bottlenecks(metrics),
        "outliers": detect_outliers(metrics)
    }
```

### Visualization Recommendations

1. **Time Series**: Throughput and latency over time
2. **Histograms**: Latency distribution
3. **Heatmaps**: Operation patterns
4. **Percentile Charts**: p50, p95, p99 trends
5. **Resource Utilization**: CPU, memory, network over time

## Integration Points

### 1. Locust Integration
Use Locust's event system for metric collection.

### 2. Ceph Integration
Query Ceph mgr and admin socket for cluster metrics.

### 3. Prometheus/Grafana
Export metrics for real-time monitoring.

### 4. CI/CD Integration
Automated performance regression detection.

## Next Steps

1. Implement MetricsCollector class
2. Add Prometheus exporter
3. Create Grafana dashboard templates
4. Build performance analysis tools
5. Add automated alerting for anomalies

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-03  
**Status**: Design Proposal
