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


"""Unit tests for daemon cleanup functionality"""

import os
import signal
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from chopsticks.metrics.daemon import MetricsDaemon


class TestDaemonCleanup:
    """Test daemon cleanup and process management"""

    @pytest.fixture
    def temp_files(self):
        """Create temporary PID and state files"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix="_test.pid"
        ) as pid_f:
            pid_file = Path(pid_f.name)

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix="_test_state.json"
        ) as state_f:
            state_file = Path(state_f.name)

        socket_path = tempfile.mktemp(suffix="_test.sock")

        yield {
            "pid_file": pid_file,
            "state_file": state_file,
            "socket_path": socket_path,
        }

        # Cleanup
        pid_file.unlink(missing_ok=True)
        state_file.unlink(missing_ok=True)
        Path(socket_path).unlink(missing_ok=True)

    def test_cleanup_stale_files_removes_files_when_process_not_running(
        self, temp_files
    ):
        """Test that cleanup removes files when process doesn't exist"""
        config = {
            "http_host": "0.0.0.0",
            "http_port": 8091,
            "persistent": {
                "pid_file": str(temp_files["pid_file"]),
                "state_file": str(temp_files["state_file"]),
                "socket_path": temp_files["socket_path"],
            },
        }

        # Write a non-existent PID
        temp_files["pid_file"].write_text("99999")
        temp_files["state_file"].write_text('{"test": "data"}')
        Path(temp_files["socket_path"]).touch()

        daemon = MetricsDaemon(config)
        daemon.cleanup_stale_files()

        # Files should be removed
        assert not temp_files["pid_file"].exists()
        assert not temp_files["state_file"].exists()
        assert not Path(temp_files["socket_path"]).exists()

    def test_cleanup_stale_files_preserves_files_for_running_process(self, temp_files):
        """Test that cleanup preserves files when process is running"""
        config = {
            "http_host": "0.0.0.0",
            "http_port": 8091,
            "persistent": {
                "pid_file": str(temp_files["pid_file"]),
                "state_file": str(temp_files["state_file"]),
                "socket_path": temp_files["socket_path"],
            },
        }

        # Write current process PID
        temp_files["pid_file"].write_text(str(os.getpid()))

        daemon = MetricsDaemon(config)
        with patch.object(
            daemon, "_is_chopsticks_process", return_value=True
        ) as mock_check:
            daemon.cleanup_stale_files()

        # Files should still exist
        assert temp_files["pid_file"].exists()
        mock_check.assert_called_once_with(os.getpid())

    def test_is_chopsticks_process_identifies_correct_process(self):
        """Test that _is_chopsticks_process correctly identifies chopsticks processes"""
        config = {
            "http_host": "0.0.0.0",
            "http_port": 8091,
            "persistent": {},
        }
        daemon = MetricsDaemon(config)

        # Mock reading /proc/PID/cmdline
        mock_cmdline = "python3\0-m\0chopsticks.metrics.server_daemon\0--host\00.0.0.0"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_cmdline):
                assert daemon._is_chopsticks_process(12345) is True

    def test_is_chopsticks_process_rejects_non_chopsticks_process(self):
        """Test that _is_chopsticks_process rejects non-chopsticks processes"""
        config = {
            "http_host": "0.0.0.0",
            "http_port": 8091,
            "persistent": {},
        }
        daemon = MetricsDaemon(config)

        # Mock reading /proc/PID/cmdline for a different process
        mock_cmdline = "python3\0-m\0some.other.module\0--arg\0value"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_cmdline):
                assert daemon._is_chopsticks_process(12345) is False

    def test_is_chopsticks_process_handles_missing_proc_file(self):
        """Test that _is_chopsticks_process handles missing /proc file gracefully"""
        config = {
            "http_host": "0.0.0.0",
            "http_port": 8091,
            "persistent": {},
        }
        daemon = MetricsDaemon(config)

        with patch("pathlib.Path.exists", return_value=False):
            assert daemon._is_chopsticks_process(12345) is False

    def test_cleanup_kills_orphaned_chopsticks_processes(self, temp_files):
        """Test that cleanup kills orphaned chopsticks processes on the port"""
        config = {
            "http_host": "0.0.0.0",
            "http_port": 8091,
            "persistent": {
                "pid_file": str(temp_files["pid_file"]),
                "state_file": str(temp_files["state_file"]),
                "socket_path": temp_files["socket_path"],
            },
        }

        daemon = MetricsDaemon(config)

        # Mock lsof finding a process on the port
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "12345"

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(daemon, "_is_chopsticks_process", return_value=True):
                with patch("os.kill") as mock_kill:
                    daemon.cleanup_stale_files()

                    # Should have tried to kill the orphaned process
                    mock_kill.assert_called_with(12345, signal.SIGTERM)

    def test_cleanup_does_not_kill_non_chopsticks_processes(self, temp_files):
        """Test that cleanup doesn't kill non-chopsticks processes on the port"""
        config = {
            "http_host": "0.0.0.0",
            "http_port": 8091,
            "persistent": {
                "pid_file": str(temp_files["pid_file"]),
                "state_file": str(temp_files["state_file"]),
                "socket_path": temp_files["socket_path"],
            },
        }

        daemon = MetricsDaemon(config)

        # Mock lsof finding a process on the port
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "12345"

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(daemon, "_is_chopsticks_process", return_value=False):
                with patch("os.kill") as mock_kill:
                    daemon.cleanup_stale_files()

                    # Should NOT have tried to kill the non-chopsticks process
                    mock_kill.assert_not_called()

    def test_stop_waits_for_process_to_exit(self, temp_files):
        """Test that stop() waits for process to exit gracefully"""
        config = {
            "http_host": "0.0.0.0",
            "http_port": 8091,
            "persistent": {
                "pid_file": str(temp_files["pid_file"]),
                "state_file": str(temp_files["state_file"]),
                "socket_path": temp_files["socket_path"],
            },
        }

        # Write current process PID (we can't kill ourselves, so we'll mock it)
        temp_files["pid_file"].write_text("12345")

        daemon = MetricsDaemon(config)

        # Mock the kill calls
        kill_attempts = [None, None, OSError()]  # Success, success, then process gone

        with patch("os.kill", side_effect=kill_attempts):
            with patch("time.sleep"):
                daemon.stop()

        # Files should be cleaned up
        assert not temp_files["pid_file"].exists()
        assert not temp_files["state_file"].exists()
