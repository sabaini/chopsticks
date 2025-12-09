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


"""S3 Large Object Stress Test with optional metrics collection"""

import random
from datetime import datetime
from locust import task, between

from chopsticks.workloads.s3.s3_workload import S3Workload
from chopsticks.utils.scenario_config import get_scenario_value
from chopsticks.metrics import OperationType


class S3LargeObjectTest(S3Workload):
    """
    S3 Large Object Stress Test with optional metrics collection.

    Tests upload, download, and delete of large objects to simulate
    real-world large file workloads.

    Configuration:
        Requires scenario config file with 's3_large_objects' section.
        Uses default config (config/scenario_config_default.yaml) if no custom config provided.

        Required fields:
        - object_size_mb: Size of objects in MB
        - max_keys_in_memory: Maximum keys to keep in memory

    Metrics Collection:
        Metrics collection is OPTIONAL and controlled by environment variable:
        - Set CHOPSTICKS_ENABLE_METRICS=true to enable detailed metrics
        - Metrics are automatically collected by the S3Workload base class
        - Override _record_metric() to customize metric collection behavior

    Environment Variables:
        CHOPSTICKS_ENABLE_METRICS: Enable metrics collection (default: false)
        CHOPSTICKS_METRICS_PORT: Prometheus endpoint port (default: 8090)
        CHOPSTICKS_METRICS_WINDOW: Aggregation window in seconds (default: 10)
    """

    wait_time = between(1, 3)

    def on_start(self):
        """Initialize test parameters"""
        self.object_size_mb = get_scenario_value("s3_large_objects", "object_size_mb")
        self.object_size_bytes = self.object_size_mb * 1024 * 1024
        self.max_keys = get_scenario_value("s3_large_objects", "max_keys_in_memory")
        self.uploaded_keys = []

    @task(3)
    def upload_large_object(self):
        """Upload a large object"""
        key = self.generate_key(prefix=f"large-objects/{self.object_size_mb}mb")
        data = self.generate_data(self.object_size_bytes)

        start_time = datetime.utcnow()
        try:
            success = self.client.upload(key, data)
            end_time = datetime.utcnow()

            # Record metric (no-op if metrics disabled)
            self._record_metric(
                operation_type=OperationType.UPLOAD,
                key=key,
                size_bytes=self.object_size_bytes,
                start_time=start_time,
                end_time=end_time,
                success=success,
            )

            if success:
                self.uploaded_keys.append(key)
                # Keep only configured number of keys to avoid memory issues
                if len(self.uploaded_keys) > self.max_keys:
                    self.uploaded_keys.pop(0)
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                operation_type=OperationType.UPLOAD,
                key=key,
                size_bytes=self.object_size_bytes,
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_code=type(e).__name__,
                error_msg=str(e),
            )
            raise

    @task(2)
    def download_large_object(self):
        """Download a previously uploaded large object"""
        if not self.uploaded_keys:
            return

        key = random.choice(self.uploaded_keys)
        data = None

        start_time = datetime.utcnow()
        try:
            data = self.client.download(key)
            end_time = datetime.utcnow()

            # Verify download was successful
            if data is None:
                self._record_metric(
                    operation_type=OperationType.DOWNLOAD,
                    key=key,
                    size_bytes=0,
                    start_time=start_time,
                    end_time=end_time,
                    success=False,
                    error_code="DownloadFailed",
                    error_msg="Download returned None",
                )
                raise Exception(f"Download failed for key: {key}")

            # Verify size
            if len(data) != self.object_size_bytes:
                self._record_metric(
                    operation_type=OperationType.DOWNLOAD,
                    key=key,
                    size_bytes=len(data),
                    start_time=start_time,
                    end_time=end_time,
                    success=False,
                    error_code="SizeMismatch",
                    error_msg=f"Expected {self.object_size_bytes}, got {len(data)}",
                )
                raise Exception(
                    f"Downloaded object size mismatch: expected {self.object_size_bytes}, "
                    f"got {len(data)}"
                )

            # Success
            self._record_metric(
                operation_type=OperationType.DOWNLOAD,
                key=key,
                size_bytes=len(data),
                start_time=start_time,
                end_time=end_time,
                success=True,
            )
        except Exception as e:
            end_time = datetime.utcnow()
            # Only record if not already recorded
            if data is not None or "Download failed" not in str(e):
                self._record_metric(
                    operation_type=OperationType.DOWNLOAD,
                    key=key,
                    size_bytes=0,
                    start_time=start_time,
                    end_time=end_time,
                    success=False,
                    error_code=type(e).__name__,
                    error_msg=str(e),
                )
            raise

    @task(1)
    def delete_large_object(self):
        """Delete a large object"""
        if not self.uploaded_keys:
            return

        key = self.uploaded_keys.pop(0)

        start_time = datetime.utcnow()
        try:
            success = self.client.delete(key)
            end_time = datetime.utcnow()

            self._record_metric(
                operation_type=OperationType.DELETE,
                key=key,
                size_bytes=0,
                start_time=start_time,
                end_time=end_time,
                success=success,
            )
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                operation_type=OperationType.DELETE,
                key=key,
                size_bytes=0,
                start_time=start_time,
                end_time=end_time,
                success=False,
                error_code=type(e).__name__,
                error_msg=str(e),
            )
            raise
