Workload API
============

API reference for workload classes.

S3Workload
----------

Base class for S3 test scenarios.

Location: ``src/chopsticks/workloads/s3/s3_workload.py``

Inheritance
~~~~~~~~~~~

.. code-block:: python

   from locust import User
   from chopsticks.workloads.s3.s3_workload import S3Workload
   
   class MyScenario(S3Workload):
       # Your scenario implementation
       pass

Attributes
~~~~~~~~~~

.. py:attribute:: config

   Workload configuration dictionary loaded from YAML.

.. py:attribute:: scenario_config

   Scenario configuration dictionary (optional).

.. py:attribute:: client

   S3 client wrapper instance (``S3Client``).

.. py:attribute:: uploaded_keys

   List of uploaded object keys (for download/delete).

.. py:attribute:: wait_time

   Wait time between tasks (Locust attribute).

Methods
~~~~~~~

.. py:method:: generate_key(prefix: str = "test") -> str

   Generate unique object key.

   :param prefix: Key prefix
   :returns: Unique key string (e.g., ``test-uuid``)

.. py:method:: generate_data(size: int) -> bytes

   Generate random data for upload.

   :param size: Data size in bytes
   :returns: Random bytes

.. py:method:: on_start()

   Called once when user starts. Override for initialization.

.. py:method:: on_stop()

   Called once when user stops. Override for cleanup.

S3Client
--------

S3 client wrapper with Locust integration.

Location: ``src/chopsticks/workloads/s3/s3_workload.py``

Methods
~~~~~~~

.. py:method:: upload(key: str, data: bytes, metadata: Optional[Dict] = None) -> bool

   Upload object with timing.

   :param key: Object key
   :param data: Object data
   :param metadata: Optional metadata
   :returns: ``True`` if successful

   Fires Locust event with operation metrics.

.. py:method:: download(key: str) -> Optional[bytes]

   Download object with timing.

   :param key: Object key
   :returns: Object data or ``None``

   Fires Locust event with operation metrics.

.. py:method:: delete(key: str) -> bool

   Delete object with timing.

   :param key: Object key
   :returns: ``True`` if successful

   Fires Locust event with operation metrics.

.. py:method:: list_objects(prefix: str = "", max_keys: int = 1000) -> List[str]

   List objects with timing.

   :param prefix: Key prefix filter
   :param max_keys: Maximum keys to return
   :returns: List of keys

   Fires Locust event with operation metrics.

.. py:method:: head_object(key: str) -> Optional[Dict]

   Get object metadata with timing.

   :param key: Object key
   :returns: Metadata dictionary or ``None``

   Fires Locust event with operation metrics.

Locust task decorators
----------------------

Tasks define operations to execute.

@task
~~~~~

.. py:decorator:: task(weight: int = 1)

   Mark method as a task.

   :param weight: Task weight (relative frequency)

   **Example:**

   .. code-block:: python

      @task(3)  # 3x more frequent than weight 1
      def upload_file(self):
          key = self.generate_key()
          data = self.generate_data(1024 * 1024)
          self.client.upload(key, data)

@tag
~~~~

.. py:decorator:: tag(*tags: str)

   Tag tasks for filtering.

   :param tags: Tag names

   **Example:**

   .. code-block:: python

      @task
      @tag('upload', 'write')
      def upload_file(self):
          # Implementation
          pass

Wait times
----------

Control pause between tasks.

between()
~~~~~~~~~

.. py:function:: between(min_wait: float, max_wait: float)

   Random wait time between min and max.

   :param min_wait: Minimum seconds
   :param max_wait: Maximum seconds

   **Example:**

   .. code-block:: python

      from locust import between
      
      class MyScenario(S3Workload):
          wait_time = between(1, 3)  # 1-3 seconds

constant()
~~~~~~~~~~

.. py:function:: constant(wait_time: float)

   Fixed wait time.

   :param wait_time: Seconds to wait

   **Example:**

   .. code-block:: python

      from locust import constant
      
      class MyScenario(S3Workload):
          wait_time = constant(2)  # Always 2 seconds

constant_pacing()
~~~~~~~~~~~~~~~~~

.. py:function:: constant_pacing(wait_time: float)

   Maintain constant request rate.

   :param wait_time: Target seconds per iteration

   **Example:**

   .. code-block:: python

      from locust import constant_pacing
      
      class MyScenario(S3Workload):
          wait_time = constant_pacing(1)  # 1 request/second per user

Example scenario
----------------

Complete example:

.. code-block:: python

   from locust import task, between
   from chopsticks.workloads.s3.s3_workload import S3Workload
   import random
   
   class MyScenario(S3Workload):
       """Custom S3 test scenario."""
       
       # Wait 1-3 seconds between tasks
       wait_time = between(1, 3)
       
       def on_start(self):
           """Initialize on user start."""
           self.my_keys = []
       
       @task(3)  # 60% of operations
       def upload_file(self):
           """Upload random file."""
           key = self.generate_key("upload")
           data = self.generate_data(10 * 1024 * 1024)  # 10MB
           
           if self.client.upload(key, data):
               self.my_keys.append(key)
       
       @task(2)  # 40% of operations
       def download_file(self):
           """Download previously uploaded file."""
           if self.my_keys:
               key = random.choice(self.my_keys)
               self.client.download(key)
       
       def on_stop(self):
           """Cleanup on user stop."""
           for key in self.my_keys:
               self.client.delete(key)

See also
--------

* :doc:`../how-to/create-scenario`
* :doc:`driver-api`
* `Locust documentation <https://docs.locust.io/>`_
