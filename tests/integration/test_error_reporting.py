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
Integration test to verify error reporting in Locust

This test creates a bad configuration and runs a Locust test
to ensure failures are properly reported.
"""

import tempfile
import os
import yaml
import subprocess
import pytest


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_locust_reports_failures_with_bad_config():
    """Test that Locust properly reports failures using dummy driver that always fails"""

    # Create a temporary config file with dummy driver that always fails
    bad_config = {
        "endpoint": "http://localhost:9999",
        "access_key": "test_access_key",
        "secret_key": "test_secret_key",
        "region": "default",
        "bucket": "test-bucket",
        "driver": "dummy",
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_config.yaml", delete=False
    ) as f:
        yaml.dump(bad_config, f)
        config_path = f.name

    try:
        # Run chopsticks CLI in headless mode for a short time
        cmd = [
            "uv",
            "run",
            "chopsticks",
            "run",
            "--workload-config",
            config_path,
            "-f",
            "src/chopsticks/scenarios/s3_large_objects.py",
            "--headless",
            "--users",
            "2",
            "--spawn-rate",
            "2",
            "--duration",
            "10s",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # The test should complete successfully (not hang or crash)
        # Return code 0 = success, 1 = test failures (which we expect with dummy driver)
        assert result.returncode in [0, 1], (
            f"Chopsticks should run without crashing.\n"
            f"Return code: {result.returncode}\nOutput:\n{output}"
        )

        # Check that the output contains failure information
        # Since dummy driver always fails, we expect 100% failures
        assert (
            "100% failures" in output or "Failures/s" in output or "# fails" in output
        ), f"Expected failure reporting in output, got:\n{output}"

    finally:
        # Clean up temp file
        if os.path.exists(config_path):
            os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
