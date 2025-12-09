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

Locust uses a controller-worker architecture:

* **Controller**: Coordinates workers, aggregates metrics, hosts web UI
* **Workers**: Execute test scenarios, report metrics to controller

.. note::
   The Locust CLI uses ``--master`` for the controller node and ``--master-host`` 
   to specify the controller's address. These are Locust's native flags.

Start the controller node
--------------------------

On your controller machine:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --master

The controller:

* Starts web UI on port 8089
* Listens for worker connections on port 5557
* Does not execute tests itself

Web UI mode
~~~~~~~~~~~

Access http://controller-ip:8089 to configure and start the test.

Headless mode
~~~~~~~~~~~~~

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --master \
     --headless \
     --users 1000 \
     --spawn-rate 50 \
     --duration 10m

Start worker nodes
------------------

On each worker machine:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker \
     --master-host=<controller-ip-address>

Each worker:

* Connects to controller on port 5557
* Executes test scenarios
* Reports metrics back to controller

Multiple workers per machine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run multiple worker processes on powerful machines:

.. code-block:: bash

   # Terminal 1
   uv run chopsticks run --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker --master-host=<controller-ip>
   
   # Terminal 2
   uv run chopsticks run --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker --master-host=<controller-ip>

Custom worker ports
~~~~~~~~~~~~~~~~~~~

If running multiple workers on one machine with different configs:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker \
     --master-host=<controller-ip> \
     --master-port=5557

Network configuration
---------------------

Ensure these ports are open:

* **5557**: Controller-worker communication
* **8089**: Web UI (controller only)

Firewall rules
~~~~~~~~~~~~~~

On controller:

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
   scp controller:/path/to/s3_config.yaml config/

Monitoring distributed tests
-----------------------------

The controller web UI shows:

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

* Check controller IP is reachable: ``ping <controller-ip>``
* Verify port 5557 is open: ``nc -zv <controller-ip> 5557``
* Check firewall rules
* Ensure controller is running first

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

1. **Start controller first** - Workers need controller to connect to
2. **Use homogeneous workers** - Similar hardware for even distribution
3. **Scale horizontally** - More workers instead of larger workers
4. **Monitor worker health** - Check CPU, memory, network on workers
5. **Test incrementally** - Start with few workers, add more gradually

Example: 10,000 concurrent users
---------------------------------

Setup:

* 1 controller node (8 CPU, 16GB RAM)
* 20 worker nodes (8 CPU, 16GB RAM each)

Controller:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --master \
     --headless \
     --users 10000 \
     --spawn-rate 100 \
     --duration 30m

Each worker:

.. code-block:: bash

   uv run chopsticks run \
     --workload-config config/s3_config.yaml \
     -f src/chopsticks/scenarios/s3_large_objects.py \
     --worker \
     --master-host=<controller-ip>

Result: ~500 users per worker, total 10,000 concurrent users.

See also
--------

* `Locust distributed testing docs <https://docs.locust.io/en/stable/running-distributed.html>`_
* :doc:`../explanation/architecture`
