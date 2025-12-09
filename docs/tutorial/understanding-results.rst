Understanding test results
==========================

This guide explains how to interpret Chopsticks test results.

Web UI metrics
--------------

The Locust web interface shows real-time metrics:

Statistics table
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Column
     - Description
   * - Type
     - Request type (e.g., "S3")
   * - Name
     - Operation name (upload, download, delete)
   * - # requests
     - Total completed requests
   * - # fails
     - Number of failed requests
   * - Median
     - 50th percentile response time (ms)
   * - 95%ile
     - 95th percentile response time (ms)
   * - Average
     - Mean response time (ms)
   * - Min/Max
     - Fastest and slowest requests (ms)
   * - RPS
     - Requests per second

Charts
~~~~~~

* **Total Requests per Second**: Overall throughput
* **Response Times**: Median and 95th percentile over time
* **Number of Users**: Concurrent users during the test

Headless mode output
--------------------

Headless mode prints periodic summaries:

.. code-block:: text

   Type     Name                # reqs  # fails |   Avg   Min   Max Median | req/s
   ---------|------------------|--------|--------|------|------|------|--------|------
   S3       upload                 150        0 |   112    95   145    110 |  5.0
   S3       download               100        0 |    44    38    58     42 |  3.3
   S3       delete                  50        0 |    32    28    41     31 |  1.7
   ---------|------------------|--------|--------|------|------|------|--------|------
            Aggregated             300        0 |    86    28   145     85 | 10.0

Interpreting the results
------------------------

**Success rate**: Percentage of successful operations

* 100% = All operations succeeded
* <100% = Some operations failed (check error logs)

**Response times**: Operation latency

* Lower is better
* 95th percentile shows performance under load
* Large gap between median and 95th percentile indicates variance

**Throughput**: Operations per second

* Higher is better
* Limited by network, disk I/O, and cluster capacity

**Upload vs Download**: Typical patterns

* Downloads are usually 2-3x faster than uploads
* This is normal for Ceph due to how data is written vs read

Next steps
----------

* :doc:`../how-to/collect-metrics`
* :doc:`../explanation/architecture`
