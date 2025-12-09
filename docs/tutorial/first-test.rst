Running your first test
=======================

This guide walks through running your first stress test with Chopsticks.

Understanding scenarios
------------------------

Chopsticks uses **scenarios** to define test behavior. A scenario specifies:

* What operations to perform (upload, download, delete)
* How frequently to perform them (task weights)
* Wait time between operations

The ``s3_large_objects`` scenario tests large file uploads and downloads.

Running with web UI
-------------------

Start Chopsticks with the web interface:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py

Open http://localhost:8089 in your browser. You'll see the Locust web interface.

Configure the test:

* **Number of users**: 5 (concurrent clients)
* **Spawn rate**: 1 (users spawned per second)
* **Host**: Leave empty (configured in YAML)

Click "Start swarming" to begin the test.

Running headless mode
---------------------

For automated testing, use headless mode:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --headless \
     --users 10 \
     --spawn-rate 2 \
     --duration 5m

This runs 10 concurrent users for 5 minutes without the web UI.

Customizing object size
-----------------------

The default object size is 100MB. To test with different sizes, create a scenario configuration:

.. code-block:: yaml

   # config/my_scenario.yaml
   s3_large_objects:
     object_size_mb: 50
     max_keys_in_memory: 20

Run with the custom configuration:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     --scenario-config config/my_scenario.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --headless --users 10 --spawn-rate 2 --duration 5m

Stopping a test
---------------

* **Web UI**: Click the "Stop" button
* **Headless**: Press ``Ctrl+C``

The test will complete any in-progress operations before shutting down gracefully.

Next steps
----------

* :doc:`understanding-results`
* :doc:`../how-to/create-scenario`
