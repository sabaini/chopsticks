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


"""Tests for download error handling in scenarios"""

import pytest
from unittest.mock import Mock


class TestDownloadErrorHandling:
    """Test that scenarios properly handle download failures"""

    def test_large_objects_with_metrics_handles_none_download(self):
        """Test that s3_large_objects scenario handles None from download with metrics recording"""
        from chopsticks.scenarios.s3_large_objects import S3LargeObjectTest

        # Create a mock environment
        mock_env = Mock()
        mock_env.parsed_options = Mock()

        # Create scenario instance
        scenario = S3LargeObjectTest(mock_env)
        scenario.uploaded_keys = ["test-key"]
        scenario.object_size_bytes = 1024

        # Mock the client to return None on download
        scenario.client = Mock()
        scenario.client.download = Mock(return_value=None)

        # Mock _record_metric to track calls
        scenario._record_metric = Mock()

        # Download should raise an exception when data is None
        with pytest.raises(Exception) as exc_info:
            scenario.download_large_object()

        assert "Download failed" in str(exc_info.value)

        # Verify metric was recorded with failure
        assert scenario._record_metric.called
        # Check keyword args for error_code
        call_kwargs = scenario._record_metric.call_args[1]
        assert "error_code" in call_kwargs
        assert call_kwargs["success"] is False

    def test_large_objects_handles_none_download(self):
        """Test that s3_large_objects handles None from download"""
        from chopsticks.scenarios.s3_large_objects import S3LargeObjectTest

        # Create a mock environment
        mock_env = Mock()
        mock_env.parsed_options = Mock()

        # Create scenario instance
        scenario = S3LargeObjectTest(mock_env)
        scenario.uploaded_keys = ["test-key"]
        scenario.object_size_bytes = 1024

        # Mock the client to return None on download
        scenario.client = Mock()
        scenario.client.download = Mock(return_value=None)

        # Download should raise an exception when data is None
        with pytest.raises(Exception) as exc_info:
            scenario.download_large_object()

        assert "Download failed" in str(exc_info.value)

    def test_example_scenario_handles_none_download(self):
        """Test that example_scenario handles None from download"""
        from chopsticks.scenarios.example_scenario import ExampleS3Scenario

        # Create a mock environment
        mock_env = Mock()
        mock_env.parsed_options = Mock()

        # Create scenario instance
        scenario = ExampleS3Scenario(mock_env)
        scenario.uploaded_keys = ["test-key"]
        scenario.object_size_bytes = 1024

        # Mock the client to return None on download
        scenario.client = Mock()
        scenario.client.download = Mock(return_value=None)

        # Download should raise an exception when data is None
        with pytest.raises(Exception) as exc_info:
            scenario.download_object()

        assert "Download failed" in str(exc_info.value)

    def test_successful_download_works(self):
        """Test that successful downloads still work correctly"""
        from chopsticks.scenarios.s3_large_objects import S3LargeObjectTest

        # Create a mock environment
        mock_env = Mock()
        mock_env.parsed_options = Mock()

        # Create scenario instance
        scenario = S3LargeObjectTest(mock_env)
        scenario.uploaded_keys = ["test-key"]
        scenario.object_size_bytes = 1024

        # Mock the client to return valid data
        test_data = b"x" * 1024
        scenario.client = Mock()
        scenario.client.download = Mock(return_value=test_data)

        # Download should succeed without raising
        scenario.download_large_object()

        # Verify download was called
        scenario.client.download.assert_called_once_with("test-key")
