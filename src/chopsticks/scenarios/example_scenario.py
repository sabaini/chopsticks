# Copyright (C) 2024 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""
Example S3 Scenario Template

This is a template for creating new S3 test scenarios.
Copy this file and modify to create your own tests.
"""

import os
from locust import task, between
from chopsticks.workloads.s3.s3_workload import S3Workload


class ExampleS3Scenario(S3Workload):
    """
    Example S3 test scenario

    Demonstrates how to create a custom S3 stress test.

    Environment Variables:
        OBJECT_SIZE: Size of test objects in KB (default: 1024)
        TEST_PREFIX: Prefix for test object keys (default: example)
    """

    # Wait time between tasks (in seconds)
    wait_time = between(1, 2)

    def on_start(self):
        """
        Called when a simulated user starts.
        Initialize test parameters and state here.
        """
        self.object_size_kb = int(os.environ.get("OBJECT_SIZE", "1024"))
        self.object_size_bytes = self.object_size_kb * 1024
        self.test_prefix = os.environ.get("TEST_PREFIX", "example")
        self.uploaded_keys = []

    @task(3)  # Weight: 3 (runs 3x more often than weight 1)
    def upload_object(self):
        """Upload a test object"""
        # Generate unique key
        key = self.generate_key(prefix=self.test_prefix)

        # Generate random data
        data = self.generate_data(self.object_size_bytes)

        # Upload (automatically tracked by Locust)
        success = self.client.upload(key, data)

        if success:
            # Store key for later download/delete
            self.uploaded_keys.append(key)

    @task(2)  # Weight: 2
    def download_object(self):
        """Download a previously uploaded object"""
        if not self.uploaded_keys:
            # Skip if no objects uploaded yet
            return

        # Select a random uploaded key
        import random

        key = random.choice(self.uploaded_keys)

        # Download (automatically tracked by Locust)
        data = self.client.download(key)

        # Verify download was successful
        if data is None:
            raise Exception(f"Download failed for key: {key}")

        # Verify download size
        if len(data) != self.object_size_bytes:
            raise Exception(
                f"Size mismatch: expected {self.object_size_bytes}, got {len(data)}"
            )

    @task(1)  # Weight: 1
    def list_objects(self):
        """List objects with our prefix"""
        self.client.list_objects(prefix=self.test_prefix, max_keys=100)
        # Keys are now listed (tracked by Locust)

    def on_stop(self):
        """
        Called when a simulated user stops.
        Cleanup resources here.
        """
        # Optional: Delete uploaded objects
        for key in self.uploaded_keys:
            try:
                self.client.delete(key)
            except Exception:
                pass  # Ignore cleanup errors
