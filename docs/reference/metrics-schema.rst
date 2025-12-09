Metrics schema
==============

Complete schema for Chopsticks metrics data.

Operation metrics
-----------------

Per-operation performance data collected during tests.

Schema
~~~~~~

.. code-block:: javascript

   {
     "operation_id": "uuid-v4",
     "timestamp_start": "ISO-8601 timestamp",
     "timestamp_end": "ISO-8601 timestamp",
     "operation_type": "string",
     "workload_type": "string",
     "object_key": "string",
     "object_size_bytes": integer,
     "duration_ms": float,
     "throughput_mbps": float,
     "success": boolean,
     "error_code": "string | null",
     "error_message": "string | null",
     "retry_count": integer,
     "driver": "string",
     "user_id": "string",
     "metadata": object
   }

**Fields:**

:operation_id: Unique identifier for this operation (UUID v4)
:timestamp_start: Operation start time in UTC (ISO-8601 format)
:timestamp_end: Operation end time in UTC (ISO-8601 format)
:operation_type: Type of operation (``upload``, ``download``, ``delete``, ``list``, ``head``)
:workload_type: Workload type (``s3``, ``rbd``)
:object_key: S3 object key or RBD image name
:object_size_bytes: Object/block size in bytes
:duration_ms: Operation duration in milliseconds
:throughput_mbps: Calculated throughput in MB/s
:success: Whether operation succeeded (``true``/``false``)
:error_code: Error code if failed (``null`` if successful)
:error_message: Error message if failed (``null`` if successful)
:retry_count: Number of retries before success/failure
:driver: Driver used (``s5cmd``, ``boto3``, ``librbd``)
:user_id: Locust user identifier
:metadata: Additional operation-specific metadata

**Example:**

.. code-block:: javascript

   {
     "operation_id": "550e8400-e29b-41d4-a716-446655440000",
     "timestamp_start": "2025-12-09T08:15:30.123456Z",
     "timestamp_end": "2025-12-09T08:15:30.235678Z",
     "operation_type": "upload",
     "workload_type": "s3",
     "object_key": "test/object-123",
     "object_size_bytes": 104857600,
     "duration_ms": 112.222,
     "throughput_mbps": 892.86,
     "success": true,
     "error_code": null,
     "error_message": null,
     "retry_count": 0,
     "driver": "s5cmd",
     "user_id": "user-1",
     "metadata": {
       "multipart": false,
       "part_size_bytes": null,
       "encryption": false
     }
   }

Aggregated metrics
------------------

Statistical summaries computed over time windows.

Schema
~~~~~~

.. code-block:: javascript

   {
     "test_run_id": "uuid-v4",
     "timestamp": "ISO-8601 timestamp",
     "window_seconds": integer,
     "operation_type": "string",
     "workload_type": "string",
     
     "operations": {
       "total": integer,
       "successful": integer,
       "failed": integer,
       "success_rate": float
     },
     
     "duration_ms": {
       "min": float,
       "max": float,
       "mean": float,
       "median": float,
       "p50": float,
       "p75": float,
       "p90": float,
       "p95": float,
       "p99": float,
       "p99.9": float,
       "stddev": float
     },
     
     "throughput_mbps": {
       "min": float,
       "max": float,
       "mean": float,
       "median": float,
       "total_mb": float
     },
     
     "object_sizes": {
       "min": integer,
       "max": integer,
       "mean": float
     }
   }

**Fields:**

:test_run_id: Test run identifier (UUID v4)
:timestamp: Window start time in UTC
:window_seconds: Aggregation window size in seconds
:operation_type: Operation type being aggregated
:workload_type: Workload type (``s3``, ``rbd``)
:operations: Operation count statistics
:duration_ms: Latency statistics in milliseconds
:throughput_mbps: Throughput statistics in MB/s
:object_sizes: Object size statistics in bytes

**Example:**

.. code-block:: javascript

   {
     "test_run_id": "550e8400-e29b-41d4-a716-446655440001",
     "timestamp": "2025-12-09T08:15:00.000000Z",
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
       "stddev": 67.8
     },
     
     "throughput_mbps": {
       "min": 180.2,
       "max": 1024.5,
       "mean": 612.3,
       "median": 598.7,
       "total_mb": 15000.0
     },
     
     "object_sizes": {
       "min": 104857600,
       "max": 104857600,
       "mean": 104857600.0
     }
   }

Test configuration
------------------

Metadata about the test run.

Schema
~~~~~~

.. code-block:: javascript

   {
     "test_run_id": "uuid-v4",
     "test_name": "string",
     "start_time": "ISO-8601 timestamp",
     "end_time": "ISO-8601 timestamp | null",
     "scenario": "string",
     "workload_type": "string",
     "driver": "string",
     "num_users": integer,
     "spawn_rate": integer,
     "duration_seconds": float | null,
     "environment": object
   }

**Fields:**

:test_run_id: Unique test run identifier (UUID v4)
:test_name: Human-readable test name
:start_time: Test start time in UTC
:end_time: Test end time in UTC (``null`` if still running)
:scenario: Scenario file name
:workload_type: Workload type (``s3``, ``rbd``)
:driver: Driver used
:num_users: Number of concurrent users
:spawn_rate: User spawn rate (users/second)
:duration_seconds: Test duration (``null`` if indefinite)
:environment: Environment metadata (Python version, OS, etc.)

**Example:**

.. code-block:: javascript

   {
     "test_run_id": "550e8400-e29b-41d4-a716-446655440001",
     "test_name": "S3 Performance Test",
     "start_time": "2025-12-09T08:00:00.000000Z",
     "end_time": "2025-12-09T08:05:00.000000Z",
     "scenario": "s3_large_objects",
     "workload_type": "s3",
     "driver": "s5cmd",
     "num_users": 10,
     "spawn_rate": 2,
     "duration_seconds": 300.0,
     "environment": {
       "python_version": "3.12.0",
       "os": "Linux",
       "hostname": "test-client-01"
     }
   }

Prometheus metrics
------------------

Metrics exposed at ``/metrics`` endpoint in Prometheus format.

Histograms
~~~~~~~~~~

**chopsticks_operation_duration_seconds**

Operation duration histogram with labels:

* ``operation``: Operation type
* ``workload``: Workload type
* ``driver``: Driver name

Buckets: 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, +Inf

**chopsticks_operation_size_bytes**

Object size histogram with same labels.

Buckets: 1KB, 10KB, 100KB, 1MB, 10MB, 100MB, 1GB, +Inf

Counters
~~~~~~~~

**chopsticks_operations_total**

Total operations counter with labels:

* ``operation``: Operation type
* ``workload``: Workload type
* ``status``: ``success`` or ``failure``

**chopsticks_bytes_transferred_total**

Total bytes transferred counter with same labels.

Gauges
~~~~~~

**chopsticks_active_users**

Current number of active users.

Export formats
--------------

JSON Lines
~~~~~~~~~~

Operations exported as JSONL (one JSON object per line):

.. code-block:: text

   {"operation_id": "uuid1", ...}
   {"operation_id": "uuid2", ...}
   {"operation_id": "uuid3", ...}

CSV
~~~

Operations exported as CSV with header row:

.. code-block:: text

   operation_id,timestamp_start,timestamp_end,operation_type,duration_ms,...
   uuid1,2025-12-09T08:00:00.000Z,2025-12-09T08:00:00.112Z,upload,112.0,...
   uuid2,2025-12-09T08:00:00.200Z,2025-12-09T08:00:00.345Z,download,145.0,...

See also
--------

* :doc:`../how-to/collect-metrics`
* :doc:`../explanation/metrics-architecture`
