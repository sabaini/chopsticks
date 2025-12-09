Metrics architecture
====================

Understanding Chopsticks' comprehensive metrics system.

Design goals
------------

The metrics system was designed to:

**Comprehensive coverage**
   Capture all relevant performance indicators.

**Minimal overhead**
   Don't impact test execution significantly.

**Multiple export formats**
   Support JSON, CSV, and Prometheus.

**Real-time access**
   Query metrics during test execution.

**Process isolation**
   Persistent server survives test restarts.

Architecture overview
---------------------

The metrics system uses an IPC (Inter-Process Communication) architecture:

.. code-block:: text

   Workload Process                    Persistent Metrics Server
   ================                    =========================
                                       
   OperationMetric                     HTTP Server (port 8090)
        |                                      |
        |                                      | GET /metrics
        v                                      v
   MetricsCollector                    PrometheusExporter
        |                                      ^
        |---> Local storage                    |
        |     (JSON/CSV export)                |
        |                                      |
        |---> MetricsIPCClient                 |
               |                               |
               | JSON over                     |
               | Unix socket                   |
               |                               |
               +-------------> MetricsIPCServer
                              (background thread)

Components
----------

MetricsCollector
~~~~~~~~~~~~~~~~

**Location:** ``src/chopsticks/metrics/collector.py``

**Purpose:** Collect metrics within workload processes

**Responsibilities:**

* Record individual operation metrics
* Compute aggregated statistics
* Export to JSON/CSV at test completion
* Send metrics to persistent server via IPC

OperationMetric
~~~~~~~~~~~~~~~

**Location:** ``src/chopsticks/metrics/models.py``

**Purpose:** Data model for individual operations

**Fields:**

* Timestamps (start/end)
* Operation type (upload, download, delete)
* Object key and size
* Duration and throughput
* Success/failure status
* Error details (if failed)

MetricsIPCClient
~~~~~~~~~~~~~~~~

**Location:** ``src/chopsticks/metrics/ipc.py``

**Purpose:** Send metrics from workloads to persistent server

**Mechanism:**

* Connects to Unix domain socket
* Sends JSON-serialized metrics
* Non-blocking (fire-and-forget)
* Gracefully handles server unavailability

MetricsIPCServer
~~~~~~~~~~~~~~~~

**Location:** ``src/chopsticks/metrics/ipc.py``

**Purpose:** Receive metrics from workload processes

**Mechanism:**

* Listens on Unix socket (e.g., ``/tmp/chopsticks_metrics.sock``)
* Runs in background thread
* Accepts multiple concurrent connections
* Forwards metrics to Prometheus exporter

PrometheusExporter
~~~~~~~~~~~~~~~~~~

**Location:** ``src/chopsticks/metrics/prometheus_exporter.py``

**Purpose:** Export metrics in Prometheus format

**Metrics:**

* Histograms: Operation duration, object sizes
* Counters: Total operations, bytes transferred
* Gauges: Active users

HTTPServer
~~~~~~~~~~

**Location:** ``src/chopsticks/metrics/http_server.py``

**Purpose:** Serve Prometheus metrics over HTTP

**Endpoint:** ``http://localhost:8090/metrics``

Data flow
---------

During test execution
~~~~~~~~~~~~~~~~~~~~~

1. Workload performs S3 operation (e.g., upload)
2. Client wrapper times the operation
3. ``OperationMetric`` object created
4. ``MetricsCollector.record_operation()`` called
5. Metric stored locally and sent via IPC
6. Persistent server receives metric
7. Prometheus exporter updates histograms/counters
8. Metric available at ``/metrics`` endpoint

After test completion
~~~~~~~~~~~~~~~~~~~~~

1. Workload finishes execution
2. ``MetricsCollector.export_*()`` methods called
3. Local metrics written to files:
   
   * ``operations.json`` - All operation metrics
   * ``aggregated.json`` - Statistical summaries
   * ``test_config.json`` - Test metadata

4. Persistent server continues serving metrics
5. Server can be stopped manually or survives for next test

Why Unix sockets?
-----------------

The IPC system uses Unix domain sockets because:

**No port conflicts**
   Multiple workload processes can communicate without port clashes.

**Fast**
   Unix sockets are faster than TCP for local communication.

**Process isolation**
   Workloads and metrics server run independently.

**Automatic cleanup**
   Socket files removed on clean shutdown.

**Security**
   Filesystem permissions control access.

Metrics types
-------------

Operation-level metrics
~~~~~~~~~~~~~~~~~~~~~~~

Individual operation data:

* Unique operation ID
* Precise timestamps
* Operation type and key
* Duration and throughput
* Success/failure status

**Use cases:**

* Detailed performance analysis
* Identifying slow operations
* Debugging failures
* Export to analytics tools

Aggregated metrics
~~~~~~~~~~~~~~~~~~

Statistical summaries over time windows:

* Min, max, mean, median
* Percentiles (p50, p75, p90, p95, p99)
* Standard deviation
* Success rates

**Use cases:**

* Performance trends
* Comparing test runs
* SLA verification
* Capacity planning

Test metadata
~~~~~~~~~~~~~

Configuration and environment:

* Test run ID
* Start/end times
* User count and spawn rate
* Scenario and driver info
* Environment details

**Use cases:**

* Result correlation
* Test reproducibility
* Historical analysis
* Compliance reporting

Export formats
--------------

JSON
~~~~

**Format:** Standard JSON

**Use case:** Import into analytics tools

**Size:** Largest (pretty-printed)

**Example:**

.. code-block:: json

   {
     "operation_id": "uuid",
     "timestamp_start": "2025-12-09T08:00:00.000Z",
     "operation_type": "upload",
     "duration_ms": 112.5
   }

JSONL
~~~~~

**Format:** JSON Lines (one object per line)

**Use case:** Streaming, large datasets

**Size:** Smaller than JSON

**Example:**

.. code-block:: text

   {"operation_id":"uuid1","duration_ms":112.5}
   {"operation_id":"uuid2","duration_ms":145.3}

CSV
~~~

**Format:** Comma-separated values

**Use case:** Spreadsheet analysis

**Size:** Smallest

**Example:**

.. code-block:: text

   operation_id,timestamp_start,operation_type,duration_ms
   uuid1,2025-12-09T08:00:00.000Z,upload,112.5
   uuid2,2025-12-09T08:00:00.200Z,download,145.3

Prometheus
~~~~~~~~~~

**Format:** Prometheus exposition format

**Use case:** Real-time monitoring, dashboards

**Access:** HTTP endpoint (``/metrics``)

**Example:**

.. code-block:: text

   # HELP chopsticks_operation_duration_seconds Operation duration
   # TYPE chopsticks_operation_duration_seconds histogram
   chopsticks_operation_duration_seconds_bucket{operation="upload",le="0.1"} 5
   chopsticks_operation_duration_seconds_bucket{operation="upload",le="0.5"} 45
   chopsticks_operation_duration_seconds_count{operation="upload"} 150

Performance considerations
--------------------------

**Overhead**
   Metrics collection adds <1% overhead to test execution.

**Memory**
   Local collector stores metrics in memory; exports at completion.

**Disk I/O**
   Metrics files written once at test end.

**Network**
   IPC uses Unix sockets (no network overhead).

**Scalability**
   Persistent server handles metrics from multiple concurrent tests.

Integration with monitoring
---------------------------

Prometheus
~~~~~~~~~~

Add to ``prometheus.yml``:

.. code-block:: yaml

   scrape_configs:
     - job_name: 'chopsticks'
       static_configs:
         - targets: ['localhost:8090']
       scrape_interval: 10s

Grafana
~~~~~~~

Create dashboards with Prometheus data source:

* Operation duration histograms
* Throughput graphs
* Success rate gauges
* Active user count

See also
--------

* :doc:`../reference/metrics-schema`
* :doc:`../how-to/collect-metrics`
* :doc:`architecture`
