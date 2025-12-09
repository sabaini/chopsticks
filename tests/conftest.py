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


"""Pytest configuration and shared fixtures."""

import pytest
from datetime import datetime, timedelta
from chopsticks.metrics import (
    TestConfiguration,
    WorkloadType,
)


@pytest.fixture
def sample_test_config():
    """Provide sample test configuration for testing."""
    return TestConfiguration(
        test_run_id="test-run-123",
        test_name="Unit Test Run",
        start_time=datetime.utcnow(),
        scenario="s3_large_objects",
        workload_type=WorkloadType.S3,
        driver="s5cmd",
        test_config={
            "endpoint": "http://localhost:80",
            "bucket": "test-bucket",
        },
    )


@pytest.fixture
def sample_metric_data():
    """Provide sample metric data for testing."""
    start = datetime.utcnow()
    end = start + timedelta(seconds=1)

    return {
        "start": start,
        "end": end,
        "duration_ms": 1000.0,
    }


@pytest.fixture
def sample_s3_config():
    """Provide sample S3 configuration for testing."""
    return {
        "endpoint": "http://localhost:80",
        "access_key": "test-access-key",
        "secret_key": "test-secret-key",
        "bucket": "test-bucket",
        "region": "default",
        "driver": "s5cmd",
        "driver_config": {
            "s5cmd_path": "/usr/local/bin/s5cmd",
        },
    }
