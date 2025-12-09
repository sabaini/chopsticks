Command-line interface
======================

Chopsticks CLI commands and options.

chopsticks run
--------------

Run load tests with Locust.

**Synopsis:**

.. code-block:: text

   chopsticks run --workload-config CONFIG -f SCENARIO [OPTIONS]

**Required options:**

.. option:: --workload-config PATH

   Path to workload configuration file (e.g., ``config/s3_config.yaml``).

.. option:: -f, --locustfile PATH

   Path to Locust scenario file (e.g., ``src/chopsticks/scenarios/s3_large_objects.py``).

**Optional options:**

.. option:: --scenario-config PATH

   Path to scenario configuration file for customizing scenario parameters.

.. option:: --headless

   Run in headless mode without web UI.

.. option:: --users, -u INTEGER

   Number of concurrent users (headless mode).

.. option:: --spawn-rate, -r INTEGER

   Number of users spawned per second (headless mode).

.. option:: --duration, -t DURATION

   Test duration (e.g., ``5m``, ``1h``, ``30s``). Headless mode only.

.. option:: --host URL

   Override host URL from configuration.

**Examples:**

Run with web UI:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py

Run in headless mode:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --headless --users 50 --spawn-rate 5 --duration 10m

Run with custom scenario config:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     --scenario-config config/my_scenario.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --headless --users 10 --spawn-rate 2 --duration 5m

chopsticks metrics
------------------

Manage persistent metrics server.

chopsticks metrics start
~~~~~~~~~~~~~~~~~~~~~~~~

Start the persistent metrics server.

**Synopsis:**

.. code-block:: text

   chopsticks metrics start --config CONFIG [OPTIONS]

**Options:**

.. option:: --config PATH

   Path to workload configuration with metrics settings.

.. option:: --force

   Force cleanup of stale PID/socket files before starting.

**Example:**

.. code-block:: bash

   chopsticks metrics start --config config/s3_config_with_metrics.yaml

Force start after unclean shutdown:

.. code-block:: bash

   chopsticks metrics start --config config/s3_config_with_metrics.yaml --force

chopsticks metrics stop
~~~~~~~~~~~~~~~~~~~~~~~

Stop the persistent metrics server.

**Synopsis:**

.. code-block:: text

   chopsticks metrics stop --config CONFIG

**Options:**

.. option:: --config PATH

   Path to workload configuration with metrics settings.

**Example:**

.. code-block:: bash

   chopsticks metrics stop --config config/s3_config_with_metrics.yaml

chopsticks metrics status
~~~~~~~~~~~~~~~~~~~~~~~~~

Check metrics server status.

**Synopsis:**

.. code-block:: text

   chopsticks metrics status --config CONFIG

**Options:**

.. option:: --config PATH

   Path to workload configuration with metrics settings.

**Example:**

.. code-block:: bash

   chopsticks metrics status --config config/s3_config_with_metrics.yaml

Environment variables
---------------------

The following environment variables can be used:

.. envvar:: S3_CONFIG_PATH

   Override path to S3 configuration file.

.. envvar:: LARGE_OBJECT_SIZE

   Override default object size in MB for large object scenario (default: 100).

.. envvar:: SCENARIO_CONFIG_PATH

   Override path to scenario configuration file.

Exit codes
----------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Code
     - Meaning
   * - 0
     - Success
   * - 1
     - General error (configuration, connection, etc.)
   * - 2
     - Invalid command-line arguments
   * - 130
     - Interrupted by Ctrl+C
