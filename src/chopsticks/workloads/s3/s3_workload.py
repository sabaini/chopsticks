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


import os
import time
from locust import User, events
from typing import Optional, Dict

from chopsticks.drivers.s3.base import BaseS3Driver
from chopsticks.drivers.s3.s5cmd_driver import S5cmdDriver
from chopsticks.drivers.s3.dummy_driver import DummyDriver
from chopsticks.utils.config_loader import load_config, get_config_path
from chopsticks.workloads.base_metrics_workload import BaseMetricsWorkload
from chopsticks.metrics import WorkloadType


class S3Client:
    """Wrapper for S3 driver to integrate with Locust"""

    def __init__(self, driver: BaseS3Driver):
        self.driver = driver

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
                exception=exception,
                context={},
            )

        return success

    def download(self, key: str):
        """Download with timing for Locust"""
        start_time = time.time()
        data = None
        exception = None

        try:
            data = self.driver.download(key)
            if data is None:
                exception = Exception("Download failed")
        except Exception as e:
            exception = e
        finally:
            total_time = int((time.time() - start_time) * 1000)

            events.request.fire(
                request_type="S3",
                name="download",
                response_time=total_time,
                response_length=len(data) if data else 0,
                exception=exception,
                context={},
            )

        return data

    def delete(self, key: str):
        """Delete with timing for Locust"""
        start_time = time.time()
        success = False
        exception = None

        try:
            success = self.driver.delete(key)
            if not success:
                exception = Exception("Delete failed")
        except Exception as e:
            exception = e
        finally:
            total_time = int((time.time() - start_time) * 1000)

            events.request.fire(
                request_type="S3",
                name="delete",
                response_time=total_time,
                response_length=0,
                exception=exception,
                context={},
            )

        return success

    def list_objects(self, prefix: Optional[str] = None, max_keys: int = 1000):
        """List objects with timing for Locust"""
        start_time = time.time()
        keys = []
        exception = None

        try:
            keys = self.driver.list_objects(prefix, max_keys)
        except Exception as e:
            exception = e
        finally:
            total_time = int((time.time() - start_time) * 1000)

            events.request.fire(
                request_type="S3",
                name="list",
                response_time=total_time,
                response_length=len(keys),
                exception=exception,
                context={},
            )

        return keys

    def head_object(self, key: str):
        """Head object with timing for Locust"""
        start_time = time.time()
        metadata = None
        exception = None

        try:
            metadata = self.driver.head_object(key)
            if metadata is None:
                exception = Exception("Head object failed")
        except Exception as e:
            exception = e
        finally:
            total_time = int((time.time() - start_time) * 1000)

            events.request.fire(
                request_type="S3",
                name="head",
                response_time=total_time,
                response_length=0,
                exception=exception,
                context={},
            )

        return metadata


class S3Workload(User, BaseMetricsWorkload):
    """Base S3 workload for Locust tests with optional metrics collection"""

    abstract = True
    workload_type = WorkloadType.S3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load configuration
        config_path = os.environ.get("S3_CONFIG_PATH")
        if config_path:
            self.config = load_config(config_path)
        else:
            config_path = get_config_path("s3")
            if config_path.exists():
                self.config = load_config(str(config_path))
            else:
                raise RuntimeError(
                    "S3 configuration not found. Set S3_CONFIG_PATH environment variable "
                    "or create config/s3_config.yaml"
                )

        # Initialize driver
        self.driver_name = self.config.get("driver", "s5cmd")
        driver = self._get_driver(self.driver_name)

        # Create client
        self.client = S3Client(driver)
        self.bucket = self.config.get("bucket")

    def _get_driver(self, driver_name: str) -> BaseS3Driver:
        """Get driver instance by name"""
        drivers = {
            "s5cmd": S5cmdDriver,
            "dummy": DummyDriver,
        }

        driver_class = drivers.get(driver_name)
        if not driver_class:
            raise ValueError(f"Unknown driver: {driver_name}")

        return driver_class(self.config)

    def generate_key(self, prefix: str = "test") -> str:
        """Generate unique object key"""
        import uuid

        return f"{prefix}/{uuid.uuid4()}"

    def generate_data(self, size_bytes: int) -> bytes:
        """Generate random data of specified size"""
        return os.urandom(size_bytes)
