Driver API
==========

API reference for implementing custom drivers.

BaseS3Driver
------------

Base class for S3 drivers.

Location: ``src/chopsticks/drivers/s3/base.py``

Constructor
~~~~~~~~~~~

.. py:class:: BaseS3Driver(config: dict)

   Initialize S3 driver with configuration.

   :param config: Workload configuration dictionary
   :type config: dict

   Configuration fields:

   * ``endpoint``: S3 endpoint URL
   * ``access_key``: Access key ID
   * ``secret_key``: Secret access key
   * ``bucket``: Bucket name
   * ``region``: Region/zone name
   * ``driver_config``: Driver-specific configuration

Methods
~~~~~~~

.. py:method:: upload(key: str, data: bytes, metadata: Optional[Dict[str, str]] = None) -> bool

   Upload object to S3.

   :param key: Object key
   :param data: Object data as bytes
   :param metadata: Optional metadata dictionary
   :returns: ``True`` if successful, ``False`` otherwise

.. py:method:: download(key: str) -> Optional[bytes]

   Download object from S3.

   :param key: Object key
   :returns: Object data as bytes, or ``None`` if failed

.. py:method:: delete(key: str) -> bool

   Delete object from S3.

   :param key: Object key
   :returns: ``True`` if successful, ``False`` otherwise

.. py:method:: list_objects(prefix: str = "", max_keys: int = 1000) -> List[str]

   List objects in bucket.

   :param prefix: Key prefix filter
   :param max_keys: Maximum number of keys to return
   :returns: List of object keys, empty list if failed

.. py:method:: head_object(key: str) -> Optional[Dict]

   Get object metadata without downloading.

   :param key: Object key
   :returns: Metadata dictionary, or ``None`` if failed

   Metadata dictionary fields:

   * ``size``: Object size in bytes
   * ``etag``: ETag value
   * ``last_modified``: Last modification time
   * ``metadata``: Custom metadata

Example implementation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from .base import BaseS3Driver
   from typing import Optional, Dict, List
   
   class MyDriver(BaseS3Driver):
       """Custom S3 driver implementation."""
       
       def __init__(self, config: dict):
           super().__init__(config)
           # Initialize your client
       
       def upload(
           self,
           key: str,
           data: bytes,
           metadata: Optional[Dict[str, str]] = None
       ) -> bool:
           """Upload object."""
           try:
               # Your implementation
               return True
           except Exception as e:
               print(f"Upload failed: {e}")
               return False
       
       def download(self, key: str) -> Optional[bytes]:
           """Download object."""
           try:
               # Your implementation
               return data
           except Exception:
               return None
       
       def delete(self, key: str) -> bool:
           """Delete object."""
           try:
               # Your implementation
               return True
           except Exception:
               return False
       
       def list_objects(
           self,
           prefix: str = "",
           max_keys: int = 1000
       ) -> List[str]:
           """List objects."""
           try:
               # Your implementation
               return keys
           except Exception:
               return []
       
       def head_object(self, key: str) -> Optional[Dict]:
           """Get object metadata."""
           try:
               # Your implementation
               return {
                   'size': 12345,
                   'etag': '"abc123"',
                   'last_modified': datetime.now(),
                   'metadata': {}
               }
           except Exception:
               return None

Driver registration
-------------------

Register your driver in ``src/chopsticks/workloads/s3/s3_workload.py``:

.. code-block:: python

   def _get_driver(self, driver_name: str) -> BaseS3Driver:
       """Get driver instance by name."""
       from chopsticks.drivers.s3.s5cmd_driver import S5cmdDriver
       from chopsticks.drivers.s3.my_driver import MyDriver
       
       drivers = {
           's5cmd': S5cmdDriver,
           'my_driver': MyDriver,  # Add your driver
       }
       
       driver_class = drivers.get(driver_name)
       if not driver_class:
           raise ValueError(f"Unknown driver: {driver_name}")
       
       return driver_class(self.config)

Error handling
--------------

**Best practices:**

1. **Return False/None on errors** - Don't raise exceptions
2. **Log errors appropriately** - Use ``print()`` or logging
3. **Include context** - Log operation details for debugging
4. **Handle timeouts** - Set reasonable timeout values
5. **Clean up resources** - Close connections properly

**Example:**

.. code-block:: python

   def upload(self, key: str, data: bytes, metadata=None) -> bool:
       try:
           # Attempt upload
           result = self._do_upload(key, data, metadata)
           return result.success
       except TimeoutError as e:
           print(f"Upload timeout for key '{key}': {e}")
           return False
       except ConnectionError as e:
           print(f"Connection error uploading '{key}': {e}")
           return False
       except Exception as e:
           print(f"Unexpected error uploading '{key}': {e}")
           return False

Testing your driver
-------------------

Create unit tests in ``tests/unit/drivers/test_my_driver.py``:

.. code-block:: python

   import pytest
   from chopsticks.drivers.s3.my_driver import MyDriver
   
   @pytest.fixture
   def driver():
       config = {
           'endpoint': 'http://test-endpoint',
           'access_key': 'test_key',
           'secret_key': 'test_secret',
           'bucket': 'test-bucket',
           'region': 'us-east-1',
           'driver_config': {}
       }
       return MyDriver(config)
   
   def test_upload(driver):
       """Test upload operation."""
       data = b"test data"
       result = driver.upload("test-key", data)
       assert result is True
   
   def test_download(driver):
       """Test download operation."""
       result = driver.download("test-key")
       assert result is not None
   
   def test_delete(driver):
       """Test delete operation."""
       result = driver.delete("test-key")
       assert result is True

Run tests:

.. code-block:: bash

   uv run pytest tests/unit/drivers/test_my_driver.py -v

See also
--------

* :doc:`../how-to/customize-driver`
* :doc:`workload-api`
