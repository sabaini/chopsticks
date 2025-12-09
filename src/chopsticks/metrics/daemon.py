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


"""Persistent metrics server daemon management"""

import os
import signal
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any


class MetricsDaemon:
    """Manages persistent metrics HTTP server as a background process"""

    def __init__(self, config: dict):
        self.config = config

        persistent_config = config.get("persistent", {})
        self.pid_file = Path(
            persistent_config.get("pid_file", "/tmp/chopsticks_metrics.pid")
        )
        self.state_file = Path(
            persistent_config.get("state_file", "/tmp/chopsticks_metrics_state.json")
        )
        self.socket_path = persistent_config.get(
            "socket_path", "/tmp/chopsticks_metrics.sock"
        )

        self.host = config.get("http_host", "0.0.0.0")
        self.port = config.get("http_port", 8090)

    def start(self):
        """Start metrics server as background daemon"""
        if self.is_running():
            raise RuntimeError("Metrics server already running")

        # Start server process in background
        import sys

        cmd = [
            sys.executable,
            "-m",
            "chopsticks.metrics.server_daemon",
            "--host",
            str(self.host),
            "--port",
            str(self.port),
            "--socket-path",
            str(self.socket_path),
            "--pid-file",
            str(self.pid_file),
            "--state-file",
            str(self.state_file),
        ]

        # Start detached process
        # Note: pid_file will be written by the daemon process itself
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
        )

        # Wait for daemon to write PID file
        max_wait = 10
        for _ in range(max_wait):
            if self.pid_file.exists():
                break
            time.sleep(0.5)

        if not self.pid_file.exists():
            raise RuntimeError("Daemon failed to start - PID file not created")

        # Wait a moment and verify it started
        time.sleep(1)
        if not self.is_running():
            raise RuntimeError("Failed to start metrics server")

    def _wait_for_condition(self, condition_fn, timeout=5.0, poll_interval=0.1):
        """Wait for a condition to become true with exponential backoff

        Args:
            condition_fn: Callable that returns True when condition is met
            timeout: Maximum time to wait in seconds
            poll_interval: Initial polling interval in seconds

        Returns:
            True if condition met, False if timeout
        """
        start_time = time.time()
        interval = poll_interval

        while time.time() - start_time < timeout:
            if condition_fn():
                return True
            time.sleep(interval)
            # Exponential backoff with cap at 0.5 seconds
            interval = min(interval * 1.5, 0.5)

        return False

    def stop(self):
        """Stop the running metrics server"""
        if not self.is_running():
            raise RuntimeError("Metrics server not running")

        pid = int(self.pid_file.read_text())

        try:
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit
            def process_exited():
                try:
                    os.kill(pid, 0)
                    return False
                except OSError:
                    return True

            # Increased timeout to 10 seconds to accommodate slow systems
            self._wait_for_condition(process_exited, timeout=10.0)

            # Wait for daemon to clean up its files
            def files_cleaned():
                return not self.pid_file.exists() and not self.state_file.exists()

            self._wait_for_condition(files_cleaned, timeout=3.0)

            # If files still exist (daemon crashed or slow), clean them up
            self.pid_file.unlink(missing_ok=True)
            self.state_file.unlink(missing_ok=True)

        except OSError as e:
            raise RuntimeError(f"Failed to stop server: {e}")

    def is_running(self) -> bool:
        """Check if metrics server is currently running"""
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text())
            os.kill(pid, 0)  # Signal 0 just checks if process exists
            return True
        except (OSError, ValueError):
            # Clean up stale PID file
            self.pid_file.unlink(missing_ok=True)
            return False

    def _is_chopsticks_process(self, pid: int) -> bool:
        """Check if a given PID belongs to a chopsticks metrics server"""
        try:
            # Read the process command line
            cmdline_file = Path(f"/proc/{pid}/cmdline")
            if not cmdline_file.exists():
                return False

            cmdline = cmdline_file.read_text()
            # Command line args are null-separated in /proc/*/cmdline
            args = cmdline.split("\0")

            # Check if this is a chopsticks.metrics.server_daemon process
            return "chopsticks.metrics.server_daemon" in " ".join(args)
        except (OSError, ValueError):
            return False

    def cleanup_stale_files(self):
        """Clean up stale PID, state, and socket files"""
        from pathlib import Path

        # Remove PID file if it exists and process is not running
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text())
                try:
                    os.kill(pid, 0)
                    # Process exists, verify it's actually a chopsticks process
                    if not self._is_chopsticks_process(pid):
                        # PID file points to non-chopsticks process, clean up stale file
                        self.pid_file.unlink(missing_ok=True)
                    else:
                        # Valid chopsticks process running, don't clean
                        return
                except OSError:
                    # Process doesn't exist, clean up
                    self.pid_file.unlink(missing_ok=True)
            except (ValueError, OSError):
                self.pid_file.unlink(missing_ok=True)

        # If port is in use, check if it's by an orphaned chopsticks process
        # Only attempt cleanup if we can verify it's a chopsticks process
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{self.port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = [int(p) for p in result.stdout.strip().split("\n")]
                for pid in pids:
                    # Only kill if it's confirmed to be a chopsticks process
                    if self._is_chopsticks_process(pid):
                        try:
                            os.kill(pid, signal.SIGTERM)
                            time.sleep(0.5)
                        except ProcessLookupError:
                            pass
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            # lsof not available, timeout, or invalid PID - skip port cleanup
            pass

        # Remove state file
        self.state_file.unlink(missing_ok=True)

        # Remove socket file
        socket_path = Path(self.socket_path)
        socket_path.unlink(missing_ok=True)

    def get_status(self) -> Dict[str, Any]:
        """Get current server status"""
        if not self.is_running():
            return {"running": False}

        if self.state_file.exists():
            try:
                state = json.loads(self.state_file.read_text())
                state["running"] = True
                return state
            except (json.JSONDecodeError, OSError):
                pass

        # Fallback if state file missing or corrupted
        return {
            "running": True,
            "pid": int(self.pid_file.read_text()),
            "host": self.host,
            "port": self.port,
        }
