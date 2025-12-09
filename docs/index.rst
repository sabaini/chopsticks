Chopsticks Documentation
========================

Chopsticks is a flexible, extensible stress testing framework for Ceph storage. 
Built on Locust, it provides a pluggable architecture for testing S3, RBD, and 
other Ceph storage protocols with comprehensive metrics collection.

**Features:**

- Extensible workload architecture (S3, RBD)
- Multiple client drivers (s5cmd, boto3, librbd)
- Scenario-based testing with Locust
- Distributed load generation
- Comprehensive metrics with Prometheus export
- Configuration-driven design

---------

In this documentation
---------------------

.. grid:: 1 1 2 2
   :padding: 0

   .. grid-item-card:: :ref:`Tutorial <tutorial>`

      **Get started** - hands-on introduction for new users

   .. grid-item-card:: :ref:`How-to guides <how-to>`

      **Step-by-step guides** covering key operations

.. grid:: 1 1 2 2
   :padding: 0
   :margin: 0
   
   .. grid-item-card:: :ref:`Explanation <explanation>`

      **Discussion and clarification** of key topics

   .. grid-item-card:: :ref:`Reference <reference>`

      **Technical information** - APIs, CLIs, configuration

---------

Project and community
---------------------

Chopsticks is an open source project by Canonical. Contributions and feedback are welcome!

* `GitHub repository <https://github.com/canonical/chopsticks>`_
* `Issue tracker <https://github.com/canonical/chopsticks/issues>`_

---------

.. toctree::
   :hidden:
   :maxdepth: 2

   tutorial/index
   how-to/index
   reference/index
   explanation/index
