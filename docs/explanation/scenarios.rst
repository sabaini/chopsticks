Scenarios
=========

Understanding test scenarios in Chopsticks.

What are scenarios?
-------------------

Scenarios define **what** your test does:

* Which operations to execute
* How frequently to execute them
* Wait times between operations
* Custom test logic and patterns

Scenarios are Python classes that inherit from workload base classes.

Scenario lifecycle
------------------

A scenario follows this lifecycle:

**1. Class definition**
   Define scenario class inheriting from workload.

**2. User spawn**
   Locust spawns user instances based on ``--users`` parameter.

**3. on_start() hook**
   Called once per user at start for initialization.

**4. Task execution**
   User executes tasks based on weights in a loop.

**5. Wait time**
   User pauses between tasks according to ``wait_time``.

**6. on_stop() hook**
   Called once per user at end for cleanup.

Task selection
--------------

Locust selects tasks based on weights:

.. code-block:: python

   class MyScenario(S3Workload):
       @task(3)  # Weight: 3
       def task_a(self):
           pass
       
       @task(2)  # Weight: 2
       def task_b(self):
           pass
       
       @task(1)  # Weight: 1
       def task_c(self):
           pass

**Selection probability:**

* ``task_a``: 3/(3+2+1) = 50%
* ``task_b``: 2/(3+2+1) = 33%
* ``task_c``: 1/(3+2+1) = 17%

Wait time strategies
--------------------

between()
~~~~~~~~~

Random wait between min and max:

.. code-block:: python

   from locust import between
   
   class MyScenario(S3Workload):
       wait_time = between(1, 3)  # 1-3 seconds

**Use case:** Simulate variable user behavior.

constant()
~~~~~~~~~~

Fixed wait time:

.. code-block:: python

   from locust import constant
   
   class MyScenario(S3Workload):
       wait_time = constant(2)  # Always 2 seconds

**Use case:** Consistent request rate per user.

constant_pacing()
~~~~~~~~~~~~~~~~~

Maintain target iteration rate:

.. code-block:: python

   from locust import constant_pacing
   
   class MyScenario(S3Workload):
       wait_time = constant_pacing(1)  # 1 iteration/second per user

**Use case:** Precise throughput control.

Custom wait time:

.. code-block:: python

   def my_wait():
       return random.choice([1, 2, 5])
   
   class MyScenario(S3Workload):
       wait_time = my_wait

Scenario patterns
-----------------

Upload-heavy workload
~~~~~~~~~~~~~~~~~~~~~

Simulate backup or data ingestion:

.. code-block:: python

   class UploadHeavy(S3Workload):
       wait_time = between(0.5, 1.5)
       
       @task(8)  # 80%
       def upload(self):
           key = self.generate_key()
           data = self.generate_data(100 * 1024 * 1024)
           self.client.upload(key, data)
       
       @task(2)  # 20%
       def verify_upload(self):
           if self.uploaded_keys:
               key = random.choice(self.uploaded_keys)
               self.client.head_object(key)

Download-heavy workload
~~~~~~~~~~~~~~~~~~~~~~~

Simulate content delivery or retrieval:

.. code-block:: python

   class DownloadHeavy(S3Workload):
       wait_time = between(0.1, 0.5)
       
       def on_start(self):
           # Pre-populate objects
           for i in range(100):
               key = f"content-{i}"
               data = self.generate_data(10 * 1024 * 1024)
               self.client.upload(key, data)
       
       @task(9)  # 90%
       def download(self):
           key = f"content-{random.randint(0, 99)}"
           self.client.download(key)
       
       @task(1)  # 10%
       def list_content(self):
           self.client.list_objects(max_keys=10)

Mixed object sizes
~~~~~~~~~~~~~~~~~~

Realistic workload with varied sizes:

.. code-block:: python

   class MixedSizes(S3Workload):
       wait_time = between(1, 2)
       
       def on_start(self):
           self.small = 100 * 1024        # 100KB
           self.medium = 10 * 1024 * 1024 # 10MB
           self.large = 100 * 1024 * 1024 # 100MB
       
       @task(5)  # 50% - small files
       def small_upload(self):
           key = self.generate_key("small")
           data = self.generate_data(self.small)
           self.client.upload(key, data)
       
       @task(3)  # 30% - medium files
       def medium_upload(self):
           key = self.generate_key("medium")
           data = self.generate_data(self.medium)
           self.client.upload(key, data)
       
       @task(2)  # 20% - large files
       def large_upload(self):
           key = self.generate_key("large")
           data = self.generate_data(self.large)
           self.client.upload(key, data)

CRUD operations
~~~~~~~~~~~~~~~

Full create-read-update-delete cycle:

.. code-block:: python

   class CRUDWorkload(S3Workload):
       wait_time = between(1, 3)
       
       @task(4)  # Create
       def create(self):
           key = self.generate_key()
           data = self.generate_data(1024 * 1024)
           self.client.upload(key, data)
       
       @task(3)  # Read
       def read(self):
           if self.uploaded_keys:
               key = random.choice(self.uploaded_keys)
               self.client.download(key)
       
       @task(2)  # Update
       def update(self):
           if self.uploaded_keys:
               key = random.choice(self.uploaded_keys)
               data = self.generate_data(1024 * 1024)
               self.client.upload(key, data)  # Overwrite
       
       @task(1)  # Delete
       def delete(self):
           if self.uploaded_keys:
               key = self.uploaded_keys.pop()
               self.client.delete(key)

Configuration-driven scenarios
-------------------------------

Make scenarios flexible with configuration:

.. code-block:: python

   class ConfigurableScenario(S3Workload):
       """Scenario with external configuration."""
       
       def on_start(self):
           # Load scenario-specific config
           config = self.scenario_config.get('configurable', {})
           
           # Parse configuration with defaults
           self.object_size = config.get('object_size_mb', 10) * 1024 * 1024
           self.num_prefill = config.get('prefill_objects', 10)
           self.upload_weight = config.get('upload_weight', 3)
           self.download_weight = config.get('download_weight', 7)
           
           # Initialize based on config
           self.prefill_objects()
       
       def prefill_objects(self):
           """Pre-populate test objects."""
           for i in range(self.num_prefill):
               key = f"prefill-{i}"
               data = self.generate_data(self.object_size)
               self.client.upload(key, data)
       
       @task
       def dynamic_task(self):
           """Dynamically choose upload or download."""
           if random.randint(1, 10) <= self.upload_weight:
               self.do_upload()
           else:
               self.do_download()

Configuration file:

.. code-block:: yaml

   configurable:
     object_size_mb: 50
     prefill_objects: 20
     upload_weight: 3
     download_weight: 7

Best practices
--------------

**Realistic weights**
   Base task weights on actual usage patterns.

**Appropriate wait times**
   Balance load generation with cluster capacity.

**Resource cleanup**
   Use ``on_stop()`` to clean up test data.

**Error handling**
   Tasks should handle failures gracefully.

**Logging**
   Log important events for debugging.

**Configuration**
   Make scenarios configurable for flexibility.

**Documentation**
   Add docstrings explaining scenario purpose.

Debugging scenarios
-------------------

Run with single user for debugging:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/my_scenario.py \
     --users 1 --spawn-rate 1

Add debug logging:

.. code-block:: python

   @task
   def my_task(self):
       print(f"Starting task: {datetime.now()}")
       key = self.generate_key()
       print(f"Generated key: {key}")
       # ... rest of task

See also
--------

* :doc:`../how-to/create-scenario`
* :doc:`../reference/workload-api`
* :doc:`architecture`
