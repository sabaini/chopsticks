Installation
============

This guide walks you through installing Chopsticks and its dependencies.

Prerequisites
-------------

* Python 3.12 or higher
* A Ceph cluster with S3 (RGW) endpoint
* S3 credentials (access key and secret key)

Step 1: Install uv
------------------

Chopsticks uses ``uv`` for fast dependency management:

.. code-block:: bash

   curl -LsSf https://astral.sh/uv/install.sh | sh

Step 2: Clone the repository
-----------------------------

.. code-block:: bash

   git clone https://github.com/canonical/chopsticks.git
   cd chopsticks

Step 3: Install dependencies
-----------------------------

.. code-block:: bash

   uv sync

This creates a virtual environment and installs all Python dependencies.

Step 4: Install s5cmd driver
-----------------------------

The S3 workload uses s5cmd as the default driver:

.. code-block:: bash

   ./scripts/install_s5cmd.sh

This installs s5cmd to ``~/.local/bin/s5cmd``.

Step 5: Configure S3 credentials
---------------------------------

Copy the example configuration:

.. code-block:: bash

   cp config/s3_config.yaml.example config/s3_config.yaml

Edit ``config/s3_config.yaml`` with your S3 endpoint details:

.. code-block:: yaml

   endpoint: https://your-s3-endpoint.com
   access_key: YOUR_ACCESS_KEY
   secret_key: YOUR_SECRET_KEY
   bucket: test-bucket
   region: us-east-1
   driver: s5cmd

Verification
------------

Verify the installation:

.. code-block:: bash

   # Check uv installation
   uv --version
   
   # Check s5cmd installation
   s5cmd version
   
   # Verify Python environment
   uv run python --version

You're now ready to run your first test!

Next steps
----------

* :doc:`first-test`
