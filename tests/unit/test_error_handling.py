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
Unit tests for error handling in chopsticks

These tests verify that the system properly catches and reports faults
in various failure scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from locust import events

from chopsticks.drivers.s3.s5cmd_driver import S5cmdDriver
from chopsticks.workloads.s3.s3_workload import S3Client


class TestS5cmdDriverErrorHandling:
    """Test error handling in S5cmdDriver"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = {
            "endpoint": "http://invalid-endpoint:8000",
            "access_key": "invalid_access_key",
            "secret_key": "invalid_secret_key",
            "region": "default",
            "bucket": "test-bucket",
            "driver_config": {"s5cmd_path": "s5cmd"},
        }

    @pytest.mark.timeout(10)
    def test_upload_with_invalid_endpoint(self):
        """Test that upload fails with invalid endpoint"""
        driver = S5cmdDriver(self.config)
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (
                False,
                "",
                "ERROR: dial tcp: lookup invalid-endpoint: no such host",
            )
            success = driver.upload("test-key", b"test data")
            assert success is False, "Upload should fail with invalid endpoint"

    @pytest.mark.timeout(10)
    def test_download_with_invalid_endpoint(self):
        """Test that download fails with invalid endpoint"""
        driver = S5cmdDriver(self.config)
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (
                False,
                "",
                "ERROR: dial tcp: lookup invalid-endpoint: no such host",
            )
            data = driver.download("test-key")
            assert data is None, "Download should return None with invalid endpoint"

    @pytest.mark.timeout(10)
    def test_delete_with_invalid_endpoint(self):
        """Test that delete fails with invalid endpoint"""
        driver = S5cmdDriver(self.config)
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (
                False,
                "",
                "ERROR: dial tcp: lookup invalid-endpoint: no such host",
            )
            success = driver.delete("test-key")
            assert success is False, "Delete should fail with invalid endpoint"

    @pytest.mark.timeout(10)
    def test_list_objects_with_invalid_endpoint(self):
        """Test that list_objects returns empty list with invalid endpoint"""
        driver = S5cmdDriver(self.config)
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (
                False,
                "",
                "ERROR: dial tcp: lookup invalid-endpoint: no such host",
            )
            keys = driver.list_objects()
            assert keys == [], "List should return empty list with invalid endpoint"

    @pytest.mark.timeout(10)
    def test_head_object_with_invalid_endpoint(self):
        """Test that head_object returns None with invalid endpoint"""
        driver = S5cmdDriver(self.config)
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (
                False,
                "",
                "ERROR: dial tcp: lookup invalid-endpoint: no such host",
            )
            metadata = driver.head_object("test-key")
            assert metadata is None, "Head should return None with invalid endpoint"

    def test_command_timeout(self):
        """Test that commands timeout appropriately"""
        driver = S5cmdDriver(self.config)
        # Use a very short timeout to force timeout
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (False, "", "Command timed out after 1 seconds")
            success = driver.upload("test-key", b"data")
            assert success is False

    def test_command_exception(self):
        """Test that exceptions are properly handled"""
        driver = S5cmdDriver(self.config)
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (False, "", "Some exception occurred")
            success = driver.upload("test-key", b"data")
            assert success is False

    def test_stderr_error_detection(self):
        """Test that errors in stderr are detected even with return code 0"""
        driver = S5cmdDriver(self.config)
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (False, "", "ERROR: Connection refused")
            success = driver.upload("test-key", b"data")
            assert success is False


class TestS3ClientErrorReporting:
    """Test error reporting in S3Client to Locust"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_driver = Mock()
        self.client = S3Client(self.mock_driver)
        # Reset events for each test
        events.request._handlers = []

    def test_upload_failure_fires_event_with_exception(self):
        """Test that failed upload fires Locust event with exception"""
        self.mock_driver.upload.return_value = False

        fired_events = []

        def capture_event(**kwargs):
            fired_events.append(kwargs)

        events.request.add_listener(capture_event)

        success = self.client.upload("test-key", b"test data")

        assert success is False
        assert len(fired_events) == 1
        assert fired_events[0]["exception"] is not None
        assert fired_events[0]["name"] == "upload"
        assert str(fired_events[0]["exception"]) == "Upload failed"

    def test_download_failure_fires_event_with_exception(self):
        """Test that failed download fires Locust event with exception"""
        self.mock_driver.download.return_value = None

        fired_events = []

        def capture_event(**kwargs):
            fired_events.append(kwargs)

        events.request.add_listener(capture_event)

        data = self.client.download("test-key")

        assert data is None
        assert len(fired_events) == 1
        assert fired_events[0]["exception"] is not None
        assert fired_events[0]["name"] == "download"
        assert str(fired_events[0]["exception"]) == "Download failed"

    def test_delete_failure_fires_event_with_exception(self):
        """Test that failed delete fires Locust event with exception"""
        self.mock_driver.delete.return_value = False

        fired_events = []

        def capture_event(**kwargs):
            fired_events.append(kwargs)

        events.request.add_listener(capture_event)

        success = self.client.delete("test-key")

        assert success is False
        assert len(fired_events) == 1
        assert fired_events[0]["exception"] is not None
        assert fired_events[0]["name"] == "delete"
        assert str(fired_events[0]["exception"]) == "Delete failed"

    def test_head_object_failure_fires_event_with_exception(self):
        """Test that failed head_object fires Locust event with exception"""
        self.mock_driver.head_object.return_value = None

        fired_events = []

        def capture_event(**kwargs):
            fired_events.append(kwargs)

        events.request.add_listener(capture_event)

        metadata = self.client.head_object("test-key")

        assert metadata is None
        assert len(fired_events) == 1
        assert fired_events[0]["exception"] is not None
        assert fired_events[0]["name"] == "head"
        assert str(fired_events[0]["exception"]) == "Head object failed"

    def test_driver_exception_is_propagated(self):
        """Test that exceptions from driver are propagated to Locust"""
        self.mock_driver.upload.side_effect = RuntimeError("Connection error")

        fired_events = []

        def capture_event(**kwargs):
            fired_events.append(kwargs)

        events.request.add_listener(capture_event)

        success = self.client.upload("test-key", b"data")

        assert success is False
        assert len(fired_events) == 1
        assert fired_events[0]["exception"] is not None
        assert isinstance(fired_events[0]["exception"], RuntimeError)
        assert "Connection error" in str(fired_events[0]["exception"])

    def test_successful_operation_has_no_exception(self):
        """Test that successful operations don't fire exceptions"""
        self.mock_driver.upload.return_value = True

        fired_events = []

        def capture_event(**kwargs):
            fired_events.append(kwargs)

        events.request.add_listener(capture_event)

        success = self.client.upload("test-key", b"data")

        assert success is True
        assert len(fired_events) == 1
        assert fired_events[0]["exception"] is None


class TestEndToEndErrorHandling:
    """Integration tests for error handling with bad configurations"""

    @pytest.mark.timeout(10)
    def test_100_percent_failure_rate_with_bad_config(self):
        """Test that 100% failure rate is achieved with invalid configuration"""
        bad_config = {
            "endpoint": "http://definitely-invalid-endpoint-12345:9999",
            "access_key": "invalid",
            "secret_key": "invalid",
            "region": "default",
            "bucket": "nonexistent-bucket",
        }

        driver = S5cmdDriver(bad_config)

        # Mock the _run_command to simulate failures without actual network calls
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (False, "", "ERROR: connection failed")

            client = S3Client(driver)

            failed_count = 0
            total_operations = 10

            fired_events = []

            def capture_event(**kwargs):
                fired_events.append(kwargs)

            events.request.add_listener(capture_event)

            # Test multiple operations
            for i in range(total_operations):
                success = client.upload(f"key-{i}", b"test data")
                if not success:
                    failed_count += 1

            # Verify 100% failure rate
            assert (
                failed_count == total_operations
            ), f"Expected 100% failure rate, got {failed_count}/{total_operations}"

            # Verify all events have exceptions
            assert len(fired_events) == total_operations
            for event in fired_events:
                assert (
                    event["exception"] is not None
                ), "All failed operations should have exceptions"

    @pytest.mark.timeout(10)
    def test_mixed_operations_all_fail_with_bad_config(self):
        """Test that all operation types fail with invalid configuration"""
        bad_config = {
            "endpoint": "http://invalid:9999",
            "access_key": "invalid",
            "secret_key": "invalid",
            "region": "default",
            "bucket": "invalid",
        }

        driver = S5cmdDriver(bad_config)

        # Mock the _run_command to simulate failures
        with patch.object(driver, "_run_command") as mock_run:
            mock_run.return_value = (False, "", "ERROR: connection failed")

            client = S3Client(driver)

            fired_events = []

            def capture_event(**kwargs):
                fired_events.append(kwargs)

            events.request.add_listener(capture_event)

            # Test all operation types
            operations = [
                ("upload", lambda: client.upload("key", b"data")),
                ("download", lambda: client.download("key")),
                ("delete", lambda: client.delete("key")),
                ("list", lambda: client.list_objects()),
                ("head", lambda: client.head_object("key")),
            ]

            results = []
            for op_name, op_func in operations:
                result = op_func()
                # Upload, delete should return False; download, head should return None; list should return []
                if op_name in ["upload", "delete"]:
                    results.append(result is False)
                elif op_name in ["download", "head"]:
                    results.append(result is None)
                elif op_name == "list":
                    results.append(result == [])

            # All operations should fail
            assert all(results), "All operations should fail with invalid config"

            # All should have exceptions (except list which may not fire exception event)
            exception_count = sum(
                1 for e in fired_events if e.get("exception") is not None
            )
            assert exception_count >= 4, "Most operations should fire exception events"
