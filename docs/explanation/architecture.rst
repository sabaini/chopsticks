Architecture
============

Understanding Chopsticks' design and structure.

Design principles
-----------------

Chopsticks is built on these core principles:

**Extensibility**
   Easy to add new workloads (S3, RBD, CephFS), drivers (s5cmd, boto3, librbd), and scenarios.

**Separation of concerns**
   Clear boundaries between workloads, drivers, scenarios, and configuration.

**Configuration-driven**
   Environment-specific settings are externalized to YAML files.

**Locust integration**
   Leverages Locust's mature distributed testing capabilities.

Architectural layers
--------------------

.. code-block:: text

   ┌──────────────────────────────────────────────┐
   │          Locust Framework                     │
   │   (Distributed Load Generation & Metrics)     │
   └──────────────┬───────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
   ┌────▼────┐        ┌────▼────┐
   │   S3    │        │   RBD   │
   │Workload │        │Workload │  ← Workload Layer
   └────┬────┘        └────┬────┘
        │                   │
   ┌────▼─────────┐    ┌───▼──────────┐
   │  S3 Drivers  │    │ RBD Drivers  │  ← Driver Layer
   │  - s5cmd     │    │  - librbd    │
   │  - boto3     │    │  - rbd-cli   │
   └──────┬───────┘    └──────┬───────┘
          │                   │
   ┌──────▼───────────────────▼──────┐
   │        Ceph Storage              │  ← Storage Layer
   │  (RADOS, RGW, RBD, CephFS)       │
   └──────────────────────────────────┘

Component responsibilities
--------------------------

Workloads
~~~~~~~~~

**Purpose:** Define storage interface abstractions

**Responsibilities:**

* Load and validate configuration
* Instantiate appropriate driver
* Provide client wrapper with Locust integration
* Manage test lifecycle (on_start/on_stop)
* Track uploaded objects for download/delete operations

**Examples:**

* ``S3Workload`` - S3 object storage testing
* ``RBDWorkload`` (future) - Block device testing

Drivers
~~~~~~~

**Purpose:** Implement actual storage client operations

**Responsibilities:**

* Connect to storage endpoint
* Execute storage operations (upload, download, delete, etc.)
* Handle authentication
* Manage timeouts and retries
* Return success/failure status

**Examples:**

* ``S5cmdDriver`` - CLI-based S3 client
* ``Boto3Driver`` (future) - AWS SDK for Python
* ``LibRBDDriver`` (future) - Python bindings for librbd

Scenarios
~~~~~~~~~

**Purpose:** Define test patterns and behaviors

**Responsibilities:**

* Specify which operations to execute
* Define task weights (operation frequency)
* Configure wait times between operations
* Implement custom test logic
* Handle test initialization and cleanup

**Examples:**

* ``s3_large_objects`` - Upload/download/delete large files
* ``s3_small_objects`` (future) - Many small files
* ``mixed_workload`` (future) - Various object sizes

Configuration
~~~~~~~~~~~~~

**Purpose:** Externalize environment-specific settings

**Responsibilities:**

* Store connection endpoints
* Manage authentication credentials
* Configure driver selection and options
* Set metrics collection parameters
* Define test parameters

**File types:**

* ``s3_config.yaml`` - Workload configuration
* ``scenario_config.yaml`` - Scenario parameters

Data flow
---------

Test execution follows this flow:

1. **Initialization**
   
   * Locust loads scenario file
   * Scenario inherits from workload
   * Workload loads configuration
   * Workload instantiates driver
   * Driver connects to storage

2. **Test execution**
   
   * Locust spawns users (parallel)
   * Each user runs tasks based on weights
   * Tasks call client wrapper methods
   * Client wrapper calls driver operations
   * Driver executes against storage
   * Operations are timed and logged

3. **Metrics collection**
   
   * Client wrapper fires Locust events
   * Events include response time, size, status
   * Locust aggregates metrics across users
   * Persistent metrics server collects detailed metrics
   * Metrics exported to JSON/CSV/Prometheus

4. **Cleanup**
   
   * Users run on_stop() methods
   * Test data cleaned up (optional)
   * Metrics files written
   * Locust generates report

Scaling model
-------------

Horizontal scaling
~~~~~~~~~~~~~~~~~~

Chopsticks scales horizontally using Locust's controller-worker architecture:

* **Controller**: Coordinates workers, aggregates metrics
* **Workers**: Execute tests in parallel

With 10 workers and 1000 users:

* Each worker runs ~100 users
* Load is automatically distributed
* Metrics aggregated at controller

Vertical scaling limits
~~~~~~~~~~~~~~~~~~~~~~~

Single machine limits:

* **Network**: Typically 1-10 Gbps
* **CPU**: Needed for user coordination
* **Memory**: ~50-100MB per simulated user
* **File descriptors**: One per connection

For large-scale tests (>1000 users), use distributed mode.

Why Locust?
-----------

Chopsticks uses Locust as its foundation because:

**Mature and proven**
   Battle-tested in production by many organizations.

**Python-based**
   Easy to extend and customize test scenarios.

**Built for scale**
   Controller-worker architecture handles thousands of users.

**Flexible**
   Web UI for interactive testing, headless for automation.

**Real-time metrics**
   Live statistics and charts during tests.

**Active development**
   Regular updates and community support.

Design decisions
----------------

Why pluggable drivers?
~~~~~~~~~~~~~~~~~~~~~~

Different use cases need different clients:

* **s5cmd**: Fast CLI tool, low overhead
* **boto3**: Official AWS SDK, full API coverage
* **minio-py**: MinIO-specific optimizations
* **Custom**: Organization-specific requirements

Why scenario configuration?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Separating test logic from parameters enables:

* Same scenario with different object sizes
* Configuration management via Git
* Easy sharing of test patterns
* Environment-specific customization

Why YAML configuration?
~~~~~~~~~~~~~~~~~~~~~~~

YAML provides:

* Human-readable format
* Comments for documentation
* Complex nested structures
* Standard in DevOps tooling
* Git-friendly (text-based)

Extension points
----------------

The architecture provides clear extension points:

**New workloads**
   Implement base interfaces for new storage types (RBD, CephFS).

**New drivers**
   Add alternative clients for existing workloads.

**New scenarios**
   Create test patterns by extending workload classes.

**Custom metrics**
   Add application-specific metrics via Locust events.

See also
--------

* :doc:`metrics-architecture`
* :doc:`scenarios`
* :doc:`../reference/workload-api`
* :doc:`../reference/driver-api`
