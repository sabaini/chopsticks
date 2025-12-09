Error handling
==============

Understanding how Chopsticks handles and reports errors.

Error detection layers
----------------------

Chopsticks detects errors at multiple levels:

Driver level
~~~~~~~~~~~~

Drivers detect operation failures through:

* Return code checking (non-zero = failure)
* stderr content analysis (looking for "ERROR" strings)
* Timeout detection (operations exceeding timeout)
* Exception catching (unexpected errors)

Example from s5cmd driver:

.. code-block:: python

   def _run_command(self, args, input_data=None, timeout=30):
       try:
           result = subprocess.run(cmd, timeout=timeout, ...)
           
           # Check return code
           if result.returncode != 0:
               return False, stdout, stderr
           
           # Check stderr for errors
           if "ERROR" in stderr or "error" in stderr:
               return False, stdout, stderr
           
           return True, stdout, stderr
       
       except subprocess.TimeoutExpired:
           return False, "", f"Timeout after {timeout}s"
       except Exception as e:
           return False, "", str(e)

Client level
~~~~~~~~~~~~

Client wrappers convert failures to Locust events:

.. code-block:: python

   def upload(self, key, data, metadata=None):
       start_time = time.time()
       success = False
       exception = None
       
       try:
           success = self.driver.upload(key, data, metadata)
           if not success:
               exception = Exception("Upload failed")
       except Exception as e:
           exception = e
       finally:
           total_time = int((time.time() - start_time) * 1000)
           
           # Fire Locust event with exception if failed
           events.request.fire(
               request_type="S3",
               name="upload",
               response_time=total_time,
               response_length=len(data),
               exception=exception,  # Reports failure
               context={},
           )
       
       return success

Locust level
~~~~~~~~~~~~

Locust tracks failures through events:

* Increments failure counter
* Updates failure rate percentage
* Displays failures in UI/reports
* Includes failed operations in statistics

Error scenarios
---------------

Invalid endpoint
~~~~~~~~~~~~~~~~

**Symptom:** Connection refused or DNS lookup failure

**Error flow:**

1. s5cmd attempts connection
2. stderr: ``ERROR: dial tcp: lookup invalid-endpoint: no such host``
3. Driver returns ``False``
4. Client fires event with exception
5. Locust reports 100% failure rate

**Resolution:** Verify endpoint URL is correct and reachable.

Invalid credentials
~~~~~~~~~~~~~~~~~~~

**Symptom:** Authentication errors

**Error flow:**

1. s5cmd connects but authentication fails
2. stderr: ``ERROR: AccessDenied``
3. Driver returns ``False``
4. Client fires event with exception
5. Locust reports authentication failures

**Resolution:** Verify access key and secret key are correct.

Nonexistent bucket
~~~~~~~~~~~~~~~~~~

**Symptom:** Bucket not found errors

**Error flow:**

1. s5cmd connects successfully
2. stderr: ``ERROR: NoSuchBucket``
3. Driver returns ``False``
4. Client fires event with exception
5. Locust reports bucket errors

**Resolution:** Create bucket or update configuration.

Network timeout
~~~~~~~~~~~~~~~

**Symptom:** Operations stall and timeout

**Error flow:**

1. Command times out (default 30 seconds)
2. ``TimeoutExpired`` exception caught
3. Driver returns ``False`` with timeout message
4. Client fires event with exception
5. Locust reports timeout failures

**Resolution:** Increase timeout or investigate network issues.

Expected behavior with bad configuration
-----------------------------------------

When running with completely invalid configuration:

**Expected results:**

* 100% failure rate in Locust UI
* All operations show failures
* Failure metrics properly recorded
* No operations succeed

**Example output:**

.. code-block:: text

   Type     Name                # reqs  # fails |   Avg   Min   Max Median | req/s
   ---------|------------------|--------|--------|------|------|------|--------|------
   S3       upload                 10 10(100%) |   100    95   110    100 |  0.30
   S3       download                0   0(0%)  |     0     0     0      0 |  0.00
   ---------|------------------|--------|--------|------|------|------|--------|------
            Aggregated             10 10(100%) |   100    95   110    100 |  0.30

This confirms error handling is working correctly.

Error reporting in metrics
---------------------------

Operation metrics include error details:

.. code-block:: json

   {
     "operation_id": "uuid",
     "operation_type": "upload",
     "success": false,
     "error_code": "NoSuchBucket",
     "error_message": "The specified bucket does not exist",
     "retry_count": 0
   }

Aggregated metrics track failure rates:

.. code-block:: json

   {
     "operations": {
       "total": 100,
       "successful": 95,
       "failed": 5,
       "success_rate": 95.0
     }
   }

Debugging failures
------------------

Identify failure types
~~~~~~~~~~~~~~~~~~~~~~

Check Locust UI or metrics for error patterns:

* All uploads fail: Likely authentication or permissions
* All operations fail: Likely connection or endpoint issue
* Random failures: Likely cluster capacity or network issues
* Specific keys fail: Likely object-specific issues

Check driver logs
~~~~~~~~~~~~~~~~~

Drivers log errors to stdout/stderr:

.. code-block:: bash

   uv run chopsticks run ... 2>&1 | grep -i error

Enable debug logging in driver:

.. code-block:: python

   def upload(self, key, data, metadata=None):
       print(f"DEBUG: Attempting upload of {key}, size {len(data)}")
       result = self._run_command(["cp", ...])
       print(f"DEBUG: Upload result: {result}")
       return result

Test with single operation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Isolate issues by testing one operation:

.. code-block:: bash

   # Test upload
   s5cmd --endpoint-url=https://endpoint \
     cp /tmp/testfile s3://bucket/testkey
   
   # Test download
   s5cmd --endpoint-url=https://endpoint \
     cp s3://bucket/testkey /tmp/downloaded
   
   # Test delete
   s5cmd --endpoint-url=https://endpoint \
     rm s3://bucket/testkey

Verify cluster health
~~~~~~~~~~~~~~~~~~~~~

Check Ceph cluster status:

.. code-block:: bash

   ceph status
   ceph health detail
   ceph osd status
   radosgw-admin bucket stats --bucket=test-bucket

Graceful degradation
--------------------

Chopsticks is designed to continue despite errors:

**Non-blocking failures**
   Failed operations don't crash the test.

**Partial failures**
   Some operations can succeed while others fail.

**Error isolation**
   Errors in one user don't affect other users.

**Metrics preservation**
   Failed operations still recorded in metrics.

**Test continuation**
   Tests run to completion even with failures.

Error handling best practices
------------------------------

For driver developers:

1. **Return False/None on errors** - Don't raise exceptions
2. **Log errors appropriately** - Help debugging
3. **Include context** - Operation details in error messages
4. **Handle all error types** - Timeouts, network, authentication, etc.
5. **Test error paths** - Verify failures are reported correctly

For scenario developers:

1. **Check return values** - Handle operation failures
2. **Graceful degradation** - Continue despite errors
3. **Log failures** - Help debugging in production
4. **Clean up on errors** - Don't leave orphaned resources
5. **Test error scenarios** - Verify behavior with bad config

Example error-aware scenario:

.. code-block:: python

   @task
   def upload_with_handling(self):
       """Upload with error handling."""
       key = self.generate_key()
       data = self.generate_data(1024 * 1024)
       
       success = self.client.upload(key, data)
       
       if success:
           self.uploaded_keys.append(key)
       else:
           # Log but don't crash
           print(f"Upload failed for key: {key}")
           # Continue with test

See also
--------

* :doc:`../reference/driver-api`
* :doc:`architecture`
