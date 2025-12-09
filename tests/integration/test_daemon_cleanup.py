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


"""Integration tests for daemon cleanup and resource management"""

import os
import subprocess
import tempfile
import time
import yaml
import pytest
import signal
from pathlib import Path


@pytest.mark.integration
def test_daemon_cleans_up_on_sigterm():
    """Test that daemon properly cleans up PID and state files on SIGTERM"""
    config = {
        "endpoint": "http://localhost:9999",
        "access_key": "test",
        "secret_key": "test",
        "region": "default",
        "bucket": "test",
        "driver": "dummy",
        "metrics": {
            "enabled": True,
            "http_host": "0.0.0.0",
            "http_port": 8092,
            "persistent": {
                "enabled": True,
                "pid_file": "/tmp/chopsticks_cleanup_test.pid",
                "state_file": "/tmp/chopsticks_cleanup_test_state.json",
                "socket_path": "/tmp/chopsticks_cleanup_test.sock",
            },
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_config.yaml", delete=False
    ) as f:
        yaml.dump(config, f)
        config_path = f.name

    try:
        # Start daemon
        result = subprocess.run(
            ["uv", "run", "chopsticks", "metrics", "start", "--config", config_path],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0, f"Failed to start: {result.stderr}"

        time.sleep(2)

        # Verify PID file exists
        pid_file = Path("/tmp/chopsticks_cleanup_test.pid")
        assert pid_file.exists(), "PID file should exist after startup"

        pid = int(pid_file.read_text().strip())

        # Send SIGTERM
        os.kill(pid, signal.SIGTERM)

        # Wait for process to exit and clean up (with proper polling)
        # Daemon needs time to: handle signal, stop HTTP server (5s timeout), cleanup files
        max_wait = 15  # seconds
        poll_interval = 0.1
        elapsed = 0

        while elapsed < max_wait:
            if not pid_file.exists():
                break
            time.sleep(poll_interval)
            elapsed += poll_interval

        # Verify files are cleaned up
        assert not pid_file.exists(), "PID file should be removed after SIGTERM"
        assert not Path(
            "/tmp/chopsticks_cleanup_test_state.json"
        ).exists(), "State file should be removed"
        assert not Path(
            "/tmp/chopsticks_cleanup_test.sock"
        ).exists(), "Socket file should be removed"

        # Wait for process to fully exit (files are removed first, then process exits)
        max_process_wait = 5
        process_exited = False
        for _ in range(max_process_wait * 10):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                process_exited = True
                break

        # Verify process is gone
        assert process_exited, f"Process {pid} should have exited after cleanup"

    finally:
        # Cleanup
        if os.path.exists(config_path):
            os.unlink(config_path)
        for f in [
            "/tmp/chopsticks_cleanup_test.pid",
            "/tmp/chopsticks_cleanup_test_state.json",
            "/tmp/chopsticks_cleanup_test.sock",
        ]:
            if os.path.exists(f):
                os.unlink(f)


@pytest.mark.integration
def test_stop_command_cleans_up_resources():
    """Test that 'metrics stop' command properly cleans up all resources"""
    config = {
        "endpoint": "http://localhost:9999",
        "access_key": "test",
        "secret_key": "test",
        "region": "default",
        "bucket": "test",
        "driver": "dummy",
        "metrics": {
            "enabled": True,
            "http_host": "0.0.0.0",
            "http_port": 8093,
            "persistent": {
                "enabled": True,
                "pid_file": "/tmp/chopsticks_stop_test.pid",
                "state_file": "/tmp/chopsticks_stop_test_state.json",
                "socket_path": "/tmp/chopsticks_stop_test.sock",
            },
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_config.yaml", delete=False
    ) as f:
        yaml.dump(config, f)
        config_path = f.name

    pid = None
    try:
        # Start daemon
        result = subprocess.run(
            ["uv", "run", "chopsticks", "metrics", "start", "--config", config_path],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0

        time.sleep(2)

        pid_file = Path("/tmp/chopsticks_stop_test.pid")
        assert pid_file.exists()
        pid = int(pid_file.read_text().strip())

        # Stop daemon using CLI
        result = subprocess.run(
            ["uv", "run", "chopsticks", "metrics", "stop", "--config", config_path],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0

        # Wait for cleanup with polling
        max_wait = 10
        poll_interval = 0.1
        elapsed = 0

        while elapsed < max_wait:
            if not pid_file.exists():
                break
            time.sleep(poll_interval)
            elapsed += poll_interval

        # Verify all resources cleaned up
        assert not pid_file.exists(), "PID file should be removed"
        assert not Path("/tmp/chopsticks_stop_test_state.json").exists()
        assert not Path("/tmp/chopsticks_stop_test.sock").exists()

        # Wait for process to fully exit
        process_exited = False
        for _ in range(50):  # 5 seconds
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                process_exited = True
                break

        # Verify process is gone
        assert process_exited, f"Process {pid} should have exited"

    finally:
        # Cleanup
        if pid:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        if os.path.exists(config_path):
            os.unlink(config_path)
        for f in [
            "/tmp/chopsticks_stop_test.pid",
            "/tmp/chopsticks_stop_test_state.json",
            "/tmp/chopsticks_stop_test.sock",
        ]:
            if os.path.exists(f):
                os.unlink(f)


@pytest.mark.integration
def test_force_flag_cleans_orphaned_processes():
    """Test that --force flag cleans up orphaned processes"""
    config = {
        "endpoint": "http://localhost:9999",
        "access_key": "test",
        "secret_key": "test",
        "region": "default",
        "bucket": "test",
        "driver": "dummy",
        "metrics": {
            "enabled": True,
            "http_host": "0.0.0.0",
            "http_port": 8094,
            "persistent": {
                "enabled": True,
                "pid_file": "/tmp/chopsticks_force_test.pid",
                "state_file": "/tmp/chopsticks_force_test_state.json",
                "socket_path": "/tmp/chopsticks_force_test.sock",
            },
        },
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_config.yaml", delete=False
    ) as f:
        yaml.dump(config, f)
        config_path = f.name

    first_pid = None
    try:
        # Start first daemon
        result = subprocess.run(
            ["uv", "run", "chopsticks", "metrics", "start", "--config", config_path],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0

        time.sleep(2)

        pid_file = Path("/tmp/chopsticks_force_test.pid")
        first_pid = int(pid_file.read_text().strip())

        # Start second daemon with --force (should kill first and start new)
        result = subprocess.run(
            [
                "uv",
                "run",
                "chopsticks",
                "metrics",
                "start",
                "--config",
                config_path,
                "--force",
            ],
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0

        time.sleep(2)

        # Verify first process was killed
        try:
            os.kill(first_pid, 0)
            pytest.fail("First process should have been killed by --force")
        except ProcessLookupError:
            pass  # Expected

        # Verify new process is running
        second_pid = int(pid_file.read_text().strip())
        assert second_pid != first_pid

        try:
            os.kill(second_pid, 0)  # Should not raise
        except ProcessLookupError:
            pytest.fail("Second process should be running")

        # Clean up second process
        result = subprocess.run(
            ["uv", "run", "chopsticks", "metrics", "stop", "--config", config_path],
            capture_output=True,
            timeout=10,
        )
        time.sleep(2)

    finally:
        # Cleanup
        if first_pid:
            try:
                os.kill(first_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        if os.path.exists(config_path):
            os.unlink(config_path)
        for f in [
            "/tmp/chopsticks_force_test.pid",
            "/tmp/chopsticks_force_test_state.json",
            "/tmp/chopsticks_force_test.sock",
        ]:
            if os.path.exists(f):
                os.unlink(f)
