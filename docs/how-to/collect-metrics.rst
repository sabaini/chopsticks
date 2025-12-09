Collect metrics
===============

This guide shows how to collect and export performance metrics from Chopsticks tests.

Enable metrics collection
--------------------------

Metrics are controlled via the workload configuration file.

Basic metrics configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit your ``config/s3_config_with_metrics.yaml``:

.. code-block:: yaml

   endpoint: https://your-s3-endpoint.com
   access_key: YOUR_ACCESS_KEY
   secret_key: YOUR_SECRET_KEY
   bucket: test-bucket
   region: us-east-1
   driver: s5cmd
   
   metrics:
     enabled: true
     export_dir: /tmp/chopsticks_metrics
     test_name: "S3 Performance Test"
     aggregation_window_seconds: 10

Start persistent metrics server
--------------------------------

The persistent server collects metrics from all test runs:

.. code-block:: bash

   chopsticks metrics start --config config/s3_config_with_metrics.yaml

The server:

* Runs in the background
* Exposes HTTP endpoint on port 8090
* Accepts metrics via Unix socket from workloads
* Exports Prometheus format metrics

Run tests with metrics
----------------------

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config_with_metrics.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --headless --users 10 --spawn-rate 2 --duration 5m

Metrics are automatically collected and sent to the persistent server.

Access Prometheus metrics
--------------------------

Query the metrics endpoint:

.. code-block:: bash

   curl http://localhost:8090/metrics

Example output:

.. code-block:: text

   # HELP chopsticks_operation_duration_seconds Operation duration
   # TYPE chopsticks_operation_duration_seconds histogram
   chopsticks_operation_duration_seconds_bucket{operation="upload",workload="s3",le="0.1"} 0
   chopsticks_operation_duration_seconds_bucket{operation="upload",workload="s3",le="0.5"} 5
   chopsticks_operation_duration_seconds_bucket{operation="upload",workload="s3",le="1.0"} 45
   chopsticks_operation_duration_seconds_count{operation="upload",workload="s3"} 150
   chopsticks_operation_duration_seconds_sum{operation="upload",workload="s3"} 16.8

Export metrics files
--------------------

At test completion, metrics are exported to ``export_dir``:

**Operations metrics** (``operations.json``):

.. code-block:: json

   {
     "operation_id": "uuid",
     "timestamp_start": "2025-12-09T08:00:00.000000Z",
     "timestamp_end": "2025-12-09T08:00:00.112000Z",
     "operation_type": "upload",
     "object_key": "test-obj-123",
     "object_size_bytes": 104857600,
     "duration_ms": 112.0,
     "throughput_mbps": 892.86,
     "success": true
   }

**Aggregated metrics** (``aggregated.json``):

.. code-block:: json

   {
     "operation_type": "upload",
     "duration_ms": {
       "min": 85.5,
       "max": 145.2,
       "mean": 112.3,
       "median": 110.0,
       "p95": 138.7,
       "p99": 143.1
     },
     "throughput_mbps": {
       "mean": 890.2,
       "median": 900.1
     }
   }

**Test configuration** (``test_config.json``):

.. code-block:: json

   {
     "test_run_id": "uuid",
     "test_name": "S3 Performance Test",
     "start_time": "2025-12-09T08:00:00.000000Z",
     "scenario": "s3_large_objects",
     "num_users": 10,
     "spawn_rate": 2
   }

Stop metrics server
-------------------

.. code-block:: bash

   chopsticks metrics stop --config config/s3_config_with_metrics.yaml

Cleanup stale processes
~~~~~~~~~~~~~~~~~~~~~~~

If the server doesn't stop cleanly:

.. code-block:: bash

   chopsticks metrics start --config config/s3_config_with_metrics.yaml --force

The ``--force`` flag cleans up stale PID files and socket files.

Advanced configuration
----------------------

Full metrics configuration options:

.. code-block:: yaml

   metrics:
     enabled: true
     
     # Export settings
     export_dir: /tmp/chopsticks_metrics
     test_name: "S3 Performance Test"
     
     # Aggregation window
     aggregation_window_seconds: 10
     
     # HTTP server for Prometheus
     http_host: 0.0.0.0
     http_port: 8090
     
     # Persistent server settings
     persistent:
       enabled: true
       pid_file: /tmp/chopsticks_metrics.pid
       state_file: /tmp/chopsticks_metrics_state.json
       socket_path: /tmp/chopsticks_metrics.sock

Integrate with Prometheus
--------------------------

Add to ``prometheus.yml``:

.. code-block:: yaml

   scrape_configs:
     - job_name: 'chopsticks'
       static_configs:
         - targets: ['localhost:8090']
       scrape_interval: 10s

Prometheus will scrape metrics every 10 seconds during your tests.

See also
--------

* :doc:`../reference/metrics-schema`
* :doc:`../explanation/metrics-architecture`
