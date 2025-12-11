Run distributed tests
=====================

This guide shows how to run distributed Chopsticks tests across multiple machines.

Overview
--------

Distributed testing allows you to:

* Scale beyond a single machine's capacity
* Simulate thousands of concurrent users
* Generate massive load from multiple sources
* Test cluster performance under extreme conditions

Architecture
------------

Chopsticks uses a leader-worker architecture:

* **Leader**: Coordinates workers, aggregates metrics, hosts web UI
* **Workers**: Execute test scenarios, report metrics to leader

.. note::
   Chopsticks uses ``--leader`` and ``--worker`` flags. These map to Locust's
   native ``--master`` and ``--worker`` flags internally.

Start the leader node
---------------------

On your leader machine:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --leader

The leader:

* Starts web UI on port 8089
* Listens for worker connections on port 5557
* Does not execute tests itself

Web UI mode
~~~~~~~~~~~

Access http://leader-ip:8089 to configure and start the test.

Headless mode
~~~~~~~~~~~~~

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --leader \
     --headless \
     --users 1000 \
     --spawn-rate 50 \
     --duration 10m

Wait for workers before starting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``--expect-workers`` to wait for a specific number of workers:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --leader \
     --headless \
     --users 1000 \
     --spawn-rate 50 \
     --duration 10m \
     --expect-workers 5

Add a timeout to avoid waiting forever:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --leader \
     --headless \
     --users 1000 \
     --spawn-rate 50 \
     --duration 10m \
     --expect-workers 5 \
     --expect-workers-max-wait 120

Start worker nodes
------------------

On each worker machine:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker \
     --leader-host <leader-ip-address> \
     --headless

Each worker:

* Connects to leader on port 5557
* Executes test scenarios
* Reports metrics back to leader

Multiple workers per machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run multiple worker processes on powerful machines:

.. code-block:: bash

   # Terminal 1
   chopsticks run --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker --leader-host <leader-ip> --headless

   # Terminal 2
   chopsticks run --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker --leader-host <leader-ip> --headless

Network configuration
---------------------

Ensure these ports are open:

* **5557**: Leader-worker communication (default)
* **8089**: Web UI (leader only)

Firewall rules
~~~~~~~~~~~~~~

On leader:

.. code-block:: bash

   # Allow worker connections
   sudo ufw allow 5557/tcp

   # Allow web UI access
   sudo ufw allow 8089/tcp

Configuration distribution
---------------------------

Each worker needs access to:

* Same workload configuration
* Same scenario file
* Same s5cmd or driver binaries

Options:

1. **Git repository**: Clone on each worker
2. **Shared filesystem**: NFS/CIFS mount
3. **Configuration management**: Ansible, Salt, etc.

Example with Git
~~~~~~~~~~~~~~~~

On each worker:

.. code-block:: bash

   git clone https://github.com/canonical/chopsticks.git
   cd chopsticks
   uv sync
   ./scripts/install_s5cmd.sh

   # Copy config file
   scp leader:/path/to/s3_config.yaml config/

Monitoring distributed tests
-----------------------------

The leader web UI shows:

* Total workers connected
* Aggregate metrics across all workers
* Per-worker statistics (in advanced view)

Expected distribution
~~~~~~~~~~~~~~~~~~~~~

With ``--users 1000`` and 10 workers:

* Each worker runs ~100 users
* Load is automatically balanced

Troubleshooting
---------------

**Workers not connecting**

* Check leader IP is reachable: ``ping <leader-ip>``
* Verify port 5557 is open: ``nc -zv <leader-ip> 5557``
* Check firewall rules
* Ensure leader is running first

**Uneven load distribution**

* Workers have different capacity (CPU/network)
* Add more workers to slower machines
* Use homogeneous hardware for balanced load

**High network latency**

* Place workers close to Ceph cluster
* Use dedicated network for test traffic
* Avoid routing test traffic through VPNs

Best practices
--------------

1. **Start leader first** - Workers need leader to connect to
2. **Use homogeneous workers** - Similar hardware for even distribution
3. **Scale horizontally** - More workers instead of larger workers
4. **Monitor worker health** - Check CPU, memory, network on workers
5. **Test incrementally** - Start with few workers, add more gradually
6. **Use --expect-workers** - Ensure all workers connect before starting

Example: 10,000 concurrent users
---------------------------------

Setup:

* 1 leader node (8 CPU, 16GB RAM)
* 20 worker nodes (8 CPU, 16GB RAM each)

Leader:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --leader \
     --headless \
     --users 10000 \
     --spawn-rate 100 \
     --duration 30m \
     --expect-workers 20 \
     --expect-workers-max-wait 300

Each worker:

.. code-block:: bash

   chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker \
     --leader-host <leader-ip> \
     --headless

Result: ~500 users per worker, total 10,000 concurrent users.

CLI reference
-------------

Leader options:

* ``--leader`` - Run as leader node
* ``--expect-workers N`` - Wait for N workers before starting
* ``--expect-workers-max-wait SEC`` - Timeout for waiting (default: wait forever)

Worker options:

* ``--worker`` - Run as worker node
* ``--leader-host HOST`` - Leader IP address (default: ``127.0.0.1``)

See also
--------

* :doc:`../reference/cli` - Full CLI reference
* `Locust distributed testing docs <https://docs.locust.io/en/stable/running-distributed.html>`_
