Customize drivers
=================

This guide shows how to customize existing drivers or add new driver implementations.

Understanding drivers
---------------------

Drivers implement the actual client operations for each workload type:

* **S3 drivers**: Handle S3 API calls (upload, download, delete, list)
* **RBD drivers** (future): Handle block device I/O

Each driver must implement the base interface for its workload type.

Current S3 drivers
------------------

* **s5cmd**: CLI-based, high-performance (default)
* **mock**: Testing/development driver

Configure driver timeout
------------------------

Adjust timeout for slow networks:

.. code-block:: yaml

   endpoint: https://your-s3-endpoint.com
   access_key: YOUR_ACCESS_KEY
   secret_key: YOUR_SECRET_KEY
   bucket: test-bucket
   driver: s5cmd
   driver_config:
     s5cmd_path: s5cmd
     timeout: 60  # Increase to 60 seconds

Configure s5cmd path
--------------------

If s5cmd is not in PATH:

.. code-block:: yaml

   driver: s5cmd
   driver_config:
     s5cmd_path: /custom/path/to/s5cmd
     timeout: 30

Create a custom S3 driver
--------------------------

Step 1: Create driver file
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``src/chopsticks/drivers/s3/custom_driver.py``:

.. code-block:: python

   from .base import BaseS3Driver
   from typing import Optional, Dict, List
   
   class CustomDriver(BaseS3Driver):
       """Custom S3 driver implementation."""
       
       def __init__(self, config: dict):
           super().__init__(config)
           # Initialize your client library
           self.client = self._init_client()
       
       def _init_client(self):
           """Initialize S3 client."""
           # Your initialization logic
           pass
       
       def upload(
           self,
           key: str,
           data: bytes,
           metadata: Optional[Dict[str, str]] = None
       ) -> bool:
           """Upload object to S3."""
           try:
               # Your upload logic
               return True
           except Exception as e:
               print(f"Upload failed: {e}")
               return False
       
       def download(self, key: str) -> Optional[bytes]:
           """Download object from S3."""
           try:
               # Your download logic
               return data
           except Exception:
               return None
       
       def delete(self, key: str) -> bool:
           """Delete object from S3."""
           try:
               # Your delete logic
               return True
           except Exception:
               return False
       
       def list_objects(
           self,
           prefix: str = "",
           max_keys: int = 1000
       ) -> List[str]:
           """List objects in bucket."""
           try:
               # Your list logic
               return keys
           except Exception:
               return []
       
       def head_object(self, key: str) -> Optional[Dict]:
           """Get object metadata."""
           try:
               # Your head logic
               return metadata
           except Exception:
               return None

Step 2: Register the driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit ``src/chopsticks/workloads/s3/s3_workload.py``:

.. code-block:: python

   def _get_driver(self, driver_name: str) -> BaseS3Driver:
       """Get driver instance by name."""
       from chopsticks.drivers.s3.s5cmd_driver import S5cmdDriver
       from chopsticks.drivers.s3.custom_driver import CustomDriver  # Add import
       
       drivers = {
           's5cmd': S5cmdDriver,
           'custom': CustomDriver,  # Register driver
       }
       
       driver_class = drivers.get(driver_name)
       if not driver_class:
           raise ValueError(f"Unknown driver: {driver_name}")
       
       return driver_class(self.config)

Step 3: Configure and use
~~~~~~~~~~~~~~~~~~~~~~~~~~

Update ``config/s3_config.yaml``:

.. code-block:: yaml

   endpoint: https://your-s3-endpoint.com
   access_key: YOUR_ACCESS_KEY
   secret_key: YOUR_SECRET_KEY
   bucket: test-bucket
   driver: custom  # Use your driver
   driver_config:
     # Custom driver options
     option1: value1
     option2: value2

Run tests:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --headless --users 10 --spawn-rate 2 --duration 5m

Example: boto3 driver
---------------------

Full example using boto3:

.. code-block:: python

   from .base import BaseS3Driver
   from typing import Optional, Dict, List
   import boto3
   from botocore.exceptions import ClientError
   
   class Boto3Driver(BaseS3Driver):
       """boto3-based S3 driver."""
       
       def __init__(self, config: dict):
           super().__init__(config)
           
           # Get driver-specific config
           driver_config = config.get('driver_config', {})
           
           # Initialize boto3 client
           self.s3 = boto3.client(
               's3',
               endpoint_url=self.endpoint,
               aws_access_key_id=self.access_key,
               aws_secret_access_key=self.secret_key,
               region_name=self.region,
               config=boto3.session.Config(
                   connect_timeout=driver_config.get('timeout', 30),
                   read_timeout=driver_config.get('timeout', 30),
               )
           )
       
       def upload(
           self,
           key: str,
           data: bytes,
           metadata: Optional[Dict[str, str]] = None
       ) -> bool:
           try:
               self.s3.put_object(
                   Bucket=self.bucket,
                   Key=key,
                   Body=data,
                   Metadata=metadata or {}
               )
               return True
           except ClientError as e:
               print(f"Upload failed: {e}")
               return False
       
       def download(self, key: str) -> Optional[bytes]:
           try:
               response = self.s3.get_object(
                   Bucket=self.bucket,
                   Key=key
               )
               return response['Body'].read()
           except ClientError:
               return None
       
       def delete(self, key: str) -> bool:
           try:
               self.s3.delete_object(
                   Bucket=self.bucket,
                   Key=key
               )
               return True
           except ClientError:
               return False
       
       def list_objects(
           self,
           prefix: str = "",
           max_keys: int = 1000
       ) -> List[str]:
           try:
               response = self.s3.list_objects_v2(
                   Bucket=self.bucket,
                   Prefix=prefix,
                   MaxKeys=max_keys
               )
               return [obj['Key'] for obj in response.get('Contents', [])]
           except ClientError:
               return []
       
       def head_object(self, key: str) -> Optional[Dict]:
           try:
               response = self.s3.head_object(
                   Bucket=self.bucket,
                   Key=key
               )
               return {
                   'size': response['ContentLength'],
                   'etag': response['ETag'],
                   'last_modified': response['LastModified'],
                   'metadata': response.get('Metadata', {})
               }
           except ClientError:
               return None

Configuration for boto3:

.. code-block:: yaml

   driver: boto3
   driver_config:
     timeout: 30

Driver best practices
---------------------

1. **Implement all interface methods** - Required by base class
2. **Handle errors gracefully** - Return False/None on errors, don't raise
3. **Log errors appropriately** - Help debugging without spamming logs
4. **Support configuration** - Read from ``driver_config`` section
5. **Clean up resources** - Close connections in destructor if needed
6. **Test thoroughly** - Verify all operations work correctly

See also
--------

* :doc:`../reference/driver-api`
* :doc:`../explanation/architecture`
