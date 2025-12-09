Create a custom scenario
========================

This guide shows how to create custom test scenarios for Chopsticks.

Overview
--------

A scenario defines:

* What operations to execute
* Task weights (relative frequency)
* Wait times between operations
* Custom test logic

Basic scenario structure
------------------------

Create a new file in ``src/chopsticks/scenarios/``:

.. code-block:: python

   from locust import task, between
   from chopsticks.workloads.s3.s3_workload import S3Workload

   class MyCustomScenario(S3Workload):
       """Custom S3 test scenario."""
       
       # Wait 1-3 seconds between tasks
       wait_time = between(1, 3)
       
       @task(3)  # Weight: 3 (60% of operations)
       def upload_file(self):
           key = self.generate_key("test")
           data = self.generate_data(10 * 1024 * 1024)  # 10MB
           self.client.upload(key, data)
       
       @task(2)  # Weight: 2 (40% of operations)
       def download_file(self):
           if self.uploaded_keys:
               key = random.choice(self.uploaded_keys)
               self.client.download(key)

Configurable scenarios
----------------------

Make scenarios configurable via YAML:

.. code-block:: python

   class ConfigurableScenario(S3Workload):
       """Scenario with configurable parameters."""
       
       def on_start(self):
           """Called when user starts."""
           # Get scenario config
           config = self.scenario_config.get('configurable_scenario', {})
           
           # Read parameters with defaults
           self.object_size = config.get('object_size_mb', 100) * 1024 * 1024
           self.num_objects = config.get('num_objects', 10)
       
       @task
       def upload_configured_file(self):
           key = self.generate_key("config")
           data = self.generate_data(self.object_size)
           self.client.upload(key, data)

Configuration file (``config/my_scenario.yaml``):

.. code-block:: yaml

   configurable_scenario:
     object_size_mb: 50
     num_objects: 20

Mixed workload example
----------------------

Test with multiple object sizes:

.. code-block:: python

   class MixedWorkload(S3Workload):
       """Mix of small, medium, and large objects."""
       
       wait_time = between(0.5, 2)
       
       def on_start(self):
           self.small_size = 100 * 1024        # 100KB
           self.medium_size = 10 * 1024 * 1024 # 10MB
           self.large_size = 100 * 1024 * 1024 # 100MB
       
       @task(5)  # 50% small uploads
       def upload_small(self):
           key = self.generate_key("small")
           data = self.generate_data(self.small_size)
           self.client.upload(key, data)
       
       @task(3)  # 30% medium uploads
       def upload_medium(self):
           key = self.generate_key("medium")
           data = self.generate_data(self.medium_size)
           self.client.upload(key, data)
       
       @task(2)  # 20% large uploads
       def upload_large(self):
           key = self.generate_key("large")
           data = self.generate_data(self.large_size)
           self.client.upload(key, data)

Lifecycle hooks
---------------

Scenarios support lifecycle methods:

.. code-block:: python

   class LifecycleScenario(S3Workload):
       """Scenario with lifecycle hooks."""
       
       def on_start(self):
           """Called once per user at start."""
           # Initialize test data
           self.test_keys = []
           self.upload_count = 0
       
       def on_stop(self):
           """Called once per user at stop."""
           # Cleanup test data
           for key in self.test_keys:
               self.client.delete(key)
       
       @task
       def test_operation(self):
           # Your test logic
           pass

Running custom scenarios
------------------------

Run your scenario:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/my_custom_scenario.py \
     --headless --users 10 --spawn-rate 2 --duration 5m

With configuration:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     --scenario-config config/my_scenario.yaml \
     -f src/chopsticks/scenarios/my_custom_scenario.py \
     --headless --users 10 --spawn-rate 2 --duration 5m

Best practices
--------------

1. **Use meaningful task names** - They appear in metrics
2. **Set appropriate weights** - Reflect realistic usage patterns
3. **Configure wait times** - Balance load vs throughput
4. **Handle errors gracefully** - Operations may fail
5. **Clean up resources** - Use ``on_stop()`` to delete test data
6. **Make scenarios configurable** - Use YAML config for flexibility

See also
--------

* :doc:`../reference/workload-api`
* :doc:`../explanation/scenarios`
