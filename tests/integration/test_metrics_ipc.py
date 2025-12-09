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
Integration test to verify metrics IPC communication.

This test starts a persistent metrics server, runs a workload,
and verifies that metrics are received via IPC.
"""

import tempfile
import os
import yaml
import subprocess
import pytest
import time
import requests
import signal


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_metrics_ipc_with_persistent_server():
    """Test that workload sends metrics to persistent server via IPC"""

    # Create a temporary config file with metrics enabled
    config = {
        "endpoint": "http://localhost:9999",
        "access_key": "test_access_key",
        "secret_key": "test_secret_key",
        "region": "default",
        "bucket": "test-bucket",
        "driver": "dummy",
        "metrics": {
            "enabled": True,
            "http_host": "0.0.0.0",
            "http_port": 8090,
            "aggregation_window_seconds": 5,
            "export_dir": "/tmp/chopsticks_test_metrics",
            "persistent": {
                "enabled": True,
                "pid_file": "/tmp/chopsticks_test_metrics.pid",
                "state_file": "/tmp/chopsticks_test_metrics_state.json",
                "socket_path": "/tmp/chopsticks_metrics.sock",
            },
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_config.yaml", delete=False
    ) as f:
        yaml.dump(config, f)
        config_path = f.name

    metrics_server_process = None
    socket_path = "/tmp/chopsticks_metrics.sock"

    try:
        # Remove existing socket if present
        if os.path.exists(socket_path):
            os.unlink(socket_path)

        # Start persistent metrics server
        metrics_cmd = [
            "uv",
            "run",
            "chopsticks",
            "metrics",
            "start",
            "--config",
            config_path,
            "--force",  # Clean up any stale files/processes
        ]

        result = subprocess.run(
            metrics_cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )

        print(f"Metrics start output: {result.stdout}")
        print(f"Metrics start stderr: {result.stderr}")

        assert (
            result.returncode == 0
        ), f"Failed to start metrics server: {result.stderr}"

        # Give daemon a moment to fork and write PID file
        time.sleep(2)

        # Wait for metrics server to start (it runs as daemon)
        max_wait = 20
        server_ready = False

        pid_file = "/tmp/chopsticks_test_metrics.pid"
        for i in range(max_wait):
            # Check if PID file exists and process is running
            if os.path.exists(pid_file):
                print(f"Attempt {i}: PID file exists")
                try:
                    with open(pid_file) as f:
                        pid = int(f.read().strip())
                    print(f"Attempt {i}: PID = {pid}")
                    # Check if process exists
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    print(f"Attempt {i}: Process exists")

                    # Check if HTTP endpoint is responding
                    response = requests.get("http://localhost:8090/metrics", timeout=1)
                    print(f"Attempt {i}: HTTP response = {response.status_code}")
                    if response.status_code == 200:
                        server_ready = True
                        metrics_server_process = pid
                        break
                except (
                    FileNotFoundError,
                    ProcessLookupError,
                    ValueError,
                    requests.RequestException,
                ) as e:
                    print(f"Attempt {i}: Exception = {e}")
            else:
                print(f"Attempt {i}: PID file not found")
            time.sleep(1)

        if not server_ready:
            assert False, "Metrics server did not start within timeout"

        # Run chopsticks workload in headless mode
        workload_cmd = [
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
            "15s",
        ]

        workload_result = subprocess.run(
            workload_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        workload_output = workload_result.stdout + workload_result.stderr

        # Verify workload ran
        assert workload_result.returncode in [0, 1], (
            f"Chopsticks workload should run.\n"
            f"Return code: {workload_result.returncode}\nOutput:\n{workload_output}"
        )

        # Check that workload connected to metrics server
        assert (
            "Connected to persistent metrics server" in workload_output
            or "Metrics Collection Enabled" in workload_output
        ), f"Expected metrics connection in output, got:\n{workload_output}"

        # Wait a bit for metrics to be sent
        time.sleep(2)

        # Fetch metrics from persistent server
        response = requests.get("http://localhost:8090/metrics", timeout=5)
        assert response.status_code == 200, "Failed to fetch metrics from server"

        metrics_text = response.text

        # Verify that metrics are present
        # Should contain Prometheus metrics for operations
        assert (
            "chopsticks_operation_total" in metrics_text
            or "operation_duration_seconds" in metrics_text
        ), f"Expected operation metrics in Prometheus output, got:\n{metrics_text}"

        print("\nMetrics successfully collected via IPC:")
        print(f"Metrics endpoint returned {len(metrics_text)} bytes")

    finally:
        # Clean up - stop metrics server using CLI
        try:
            stop_cmd = [
                "uv",
                "run",
                "chopsticks",
                "metrics",
                "stop",
                "--config",
                config_path,
            ]
            result = subprocess.run(stop_cmd, capture_output=True, timeout=10)
            # Give daemon time to clean up its own files
            time.sleep(1)
        except Exception as e:
            print(f"Warning: Failed to stop via CLI: {e}")

        # Fallback: kill by PID if CLI stop failed and we have the PID
        if metrics_server_process:
            try:
                os.kill(metrics_server_process, signal.SIGTERM)
                time.sleep(1)
            except ProcessLookupError:
                pass

        # Clean up temp files
        if os.path.exists(config_path):
            os.unlink(config_path)

        if os.path.exists(socket_path):
            os.unlink(socket_path)

        # Clean up any remaining PID/state files (shouldn't be needed if daemon works correctly)
        for f in [
            "/tmp/chopsticks_test_metrics.pid",
            "/tmp/chopsticks_test_metrics_state.json",
        ]:
            if os.path.exists(f):
                os.unlink(f)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
