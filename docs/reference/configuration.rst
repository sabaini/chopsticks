Configuration reference
=======================

Configuration file formats and options.

S3 workload configuration
--------------------------

File: ``config/s3_config.yaml``

Basic configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   endpoint: https://s3.example.com
   access_key: YOUR_ACCESS_KEY
   secret_key: YOUR_SECRET_KEY
   bucket: test-bucket
   region: us-east-1
   driver: s5cmd

**Fields:**

.. option:: endpoint

   **Type:** string (URL)

   S3 endpoint URL. Can be AWS S3, Ceph RGW, MinIO, or any S3-compatible service.

.. option:: access_key

   **Type:** string

   S3 access key ID for authentication.

.. option:: secret_key

   **Type:** string

   S3 secret access key for authentication.

.. option:: bucket

   **Type:** string

   Default bucket name for test operations.

.. option:: region

   **Type:** string
   **Default:** ``us-east-1``

   AWS region or Ceph zone name.

.. option:: driver

   **Type:** string
   **Values:** ``s5cmd``, ``boto3`` (future)
   **Default:** ``s5cmd``

   S3 client driver to use.

Driver configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   driver: s5cmd
   driver_config:
     s5cmd_path: s5cmd
     timeout: 30

**Fields:**

.. option:: driver_config

   **Type:** object

   Driver-specific configuration options.

.. option:: driver_config.s5cmd_path

   **Type:** string
   **Default:** ``s5cmd``

   Path to s5cmd binary. Use absolute path if not in PATH.

.. option:: driver_config.timeout

   **Type:** integer
   **Default:** ``30``

   Operation timeout in seconds.

Metrics configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   metrics:
     enabled: true
     http_host: 0.0.0.0
     http_port: 8090
     aggregation_window_seconds: 10
     export_dir: /tmp/chopsticks_metrics
     test_name: "S3 Load Test"
     
     persistent:
       enabled: true
       pid_file: /tmp/chopsticks_metrics.pid
       state_file: /tmp/chopsticks_metrics_state.json
       socket_path: /tmp/chopsticks_metrics.sock

**Fields:**

.. option:: metrics.enabled

   **Type:** boolean
   **Default:** ``false``

   Enable metrics collection.

.. option:: metrics.http_host

   **Type:** string
   **Default:** ``0.0.0.0``

   HTTP server bind address for Prometheus endpoint.

.. option:: metrics.http_port

   **Type:** integer
   **Default:** ``8090``

   HTTP server port for Prometheus endpoint.

.. option:: metrics.aggregation_window_seconds

   **Type:** integer
   **Default:** ``10``

   Time window in seconds for aggregating metrics.

.. option:: metrics.export_dir

   **Type:** string
   **Default:** ``/tmp/chopsticks_metrics``

   Directory for exporting metrics files (JSON, CSV).

.. option:: metrics.test_name

   **Type:** string
   **Default:** ``"Chopsticks Test"``

   Human-readable test name for identification.

.. option:: metrics.persistent.enabled

   **Type:** boolean
   **Default:** ``false``

   Enable persistent metrics server (recommended for production).

.. option:: metrics.persistent.pid_file

   **Type:** string
   **Default:** ``/tmp/chopsticks_metrics.pid``

   PID file for metrics server process.

.. option:: metrics.persistent.state_file

   **Type:** string
   **Default:** ``/tmp/chopsticks_metrics_state.json``

   State file for persistent metrics storage.

.. option:: metrics.persistent.socket_path

   **Type:** string
   **Default:** ``/tmp/chopsticks_metrics.sock``

   Unix socket path for IPC between workloads and metrics server.

Scenario configuration
----------------------

File: ``config/scenario_config.yaml``

S3 large objects scenario
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   s3_large_objects:
     object_size_mb: 100
     max_keys_in_memory: 100

**Fields:**

.. option:: s3_large_objects.object_size_mb

   **Type:** integer
   **Default:** ``100``

   Object size in megabytes for upload operations.

.. option:: s3_large_objects.max_keys_in_memory

   **Type:** integer
   **Default:** ``100``

   Maximum number of uploaded object keys to keep in memory for download/delete operations.

Complete example
----------------

Example ``config/s3_config_with_metrics.yaml``:

.. code-block:: yaml

   # S3 endpoint configuration
   endpoint: http://10.240.47.47:80
   access_key: Y2AFX47EKQX9MUBB55Y2
   secret_key: your-secret-key-here
   bucket: chopsticks-test
   region: default
   
   # Driver configuration
   driver: s5cmd
   driver_config:
     s5cmd_path: s5cmd
     timeout: 30
   
   # Metrics configuration
   metrics:
     enabled: true
     http_host: 0.0.0.0
     http_port: 8090
     aggregation_window_seconds: 10
     export_dir: /tmp/chopsticks_metrics
     test_name: "S3 Performance Test"
     
     persistent:
       enabled: true
       pid_file: /tmp/chopsticks_metrics.pid
       state_file: /tmp/chopsticks_metrics_state.json
       socket_path: /tmp/chopsticks_metrics.sock

Example ``config/my_scenario.yaml``:

.. code-block:: yaml

   s3_large_objects:
     object_size_mb: 50
     max_keys_in_memory: 20

See also
--------

* :doc:`../how-to/collect-metrics`
* :doc:`../explanation/architecture`
