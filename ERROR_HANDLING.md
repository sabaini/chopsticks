# Error Handling in Chopsticks

## Overview

Chopsticks properly catches and reports errors at all levels of the stack. This document explains how error handling works and how failures are reported to Locust.

## Error Detection Flow

### 1. Driver Level (S5cmdDriver)

The `S5cmdDriver` class implements error detection in the `_run_command` method:

```python
def _run_command(self, args: list, input_data: Optional[bytes] = None, timeout: int = 10):
    """Run s5cmd command with error handling"""
    try:
        result = subprocess.run(cmd, input=input_data, capture_output=True, timeout=timeout)
        success = result.returncode == 0
        stdout = result.stdout.decode() if result.stdout else ""
        stderr = result.stderr.decode() if result.stderr else ""
        
        # Check for errors in stderr even if return code is 0
        if not success or "ERROR" in stderr or "error" in stderr:
            return False, stdout, stderr if stderr else "Command failed"
        
        return success, stdout, stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out after {} seconds".format(timeout)
    except Exception as e:
        return False, "", str(e)
```

**Error Detection Methods:**
- Return code checking (non-zero = failure)
- stderr content analysis (looks for "ERROR" or "error")
- Timeout handling
- Exception catching

All driver operations (`upload`, `download`, `delete`, `list_objects`, `head_object`) return:
- `False` for boolean operations on failure
- `None` for data-returning operations on failure
- `[]` for list operations on failure

### 2. Client Level (S3Client)

The `S3Client` wrapper integrates with Locust's event system:

```python
def upload(self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None):
    """Upload with timing for Locust"""
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
        
        events.request.fire(
            request_type="S3",
            name="upload",
            response_time=total_time,
            response_length=len(data),
            exception=exception,  # This reports the failure to Locust
            context={},
        )
    
    return success
```

**Key Points:**
- All operations are timed
- Failures are converted to exceptions
- Exceptions are passed to `events.request.fire()`
- Locust uses the `exception` parameter to track failures

### 3. Locust Reporting

When `events.request.fire()` is called with an `exception` parameter:
- Locust increments the failure counter
- The failure is displayed in the UI
- Failure metrics are included in reports
- The failure rate is calculated

## Failure Scenarios

### Invalid Endpoint

**Example:** `http://invalid-endpoint:9999`

**Behavior:**
- s5cmd fails to connect
- stderr contains: `ERROR: dial tcp: lookup invalid-endpoint: no such host`
- Driver returns `False`
- Client fires event with exception
- Locust reports failure

### Invalid Credentials

**Example:** Wrong access key or secret key

**Behavior:**
- s5cmd connects but gets authentication error
- stderr contains: `ERROR: AccessDenied`
- Driver returns `False`
- Client fires event with exception
- Locust reports failure

### Nonexistent Bucket

**Example:** Bucket that doesn't exist

**Behavior:**
- s5cmd connects but bucket doesn't exist
- stderr contains: `ERROR: NoSuchBucket`
- Driver returns `False`
- Client fires event with exception
- Locust reports failure

### Network Timeout

**Example:** Endpoint that doesn't respond

**Behavior:**
- Command times out (default 10 seconds)
- TimeoutExpired exception caught
- Driver returns `False` with timeout message
- Client fires event with exception
- Locust reports failure

## Expected Behavior with Bad Configuration

When running Chopsticks with completely invalid configuration (bad endpoint, credentials, bucket):

**Expected Results:**
- **100% failure rate** in Locust UI
- All operations show failures
- Failure metrics are properly recorded
- No operations succeed

## Testing Error Handling

### Unit Tests

The `tests/unit/test_error_handling.py` file contains comprehensive tests:

1. **TestS5cmdDriverErrorHandling** - Tests driver-level error detection
2. **TestS3ClientErrorReporting** - Tests Locust event firing
3. **TestEndToEndErrorHandling** - Tests 100% failure rate with bad config

Run tests:
```bash
uv run pytest tests/unit/test_error_handling.py -v
```

### Integration Tests

The `tests/integration/test_error_reporting.py` file tests end-to-end:

- Creates invalid configuration
- Runs Locust in headless mode
- Verifies failures are reported in output

Run integration test:
```bash
uv run pytest tests/integration/test_error_reporting.py -v
```

## Verifying Error Handling

To verify error handling is working:

1. **Create invalid configuration:**
```yaml
endpoint: "http://invalid-endpoint:9999"
access_key: "invalid_key"
secret_key: "invalid_secret"
region: "default"
bucket: "nonexistent-bucket"
driver: "s5cmd"
```

2. **Run Locust:**
```bash
export S3_CONFIG_PATH=invalid_config.yaml
locust -f src/chopsticks/scenarios/s3_large_objects.py --headless --users 2 --run-time 30s
```

3. **Expected Output:**
```
Type     Name                      # reqs      # fails  |   Avg     Min     Max  Median  |   req/s failures/s
--------|----------------------|-------|-------------|-------|-------|-------|--------|--------|----------
 S3      upload                      10   10(100%)  |   100      95     110     100  |    0.30       0.30
 S3      download                     0        0(0%)  |     0       0       0       0  |    0.00       0.00
--------|----------------------|-------|-------------|-------|-------|-------|--------|--------|----------
         Aggregated                  10   10(100%)  |   100      95     110     100  |    0.30       0.30
```

## Debugging Tips

If errors are not being reported:

1. **Check driver error detection:**
   - Verify `_run_command` is properly checking return codes
   - Ensure stderr is being analyzed for error strings
   - Confirm exceptions are being caught

2. **Check client event firing:**
   - Verify `events.request.fire()` is called in `finally` blocks
   - Ensure `exception` parameter is set for failures
   - Check that failures create Exception objects

3. **Check Locust configuration:**
   - Ensure Locust is properly installed
   - Verify events system is working
   - Check Locust logs for event processing

## Summary

Chopsticks implements comprehensive error handling at all levels:

- **Driver level**: Detects command failures through return codes, stderr analysis, and exception handling
- **Client level**: Converts failures to exceptions and reports them to Locust
- **Locust level**: Tracks failures and displays them in UI and reports

With properly implemented error handling, bad configurations result in 100% failure rates, ensuring accurate performance metrics and debugging information.
