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


"""IPC mechanism for sending metrics to persistent server"""

import socket
import json
import os
from pathlib import Path
from typing import Optional
from .models import OperationMetric


class MetricsIPCClient:
    """Client for sending metrics to persistent server via Unix socket"""

    def __init__(self, socket_path: Optional[str] = None):
        self.socket_path = socket_path or os.environ.get(
            "CHOPSTICKS_METRICS_SOCKET", "/tmp/chopsticks_metrics.sock"
        )
        self._socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Connect to the metrics server socket"""
        try:
            if not Path(self.socket_path).exists():
                return False

            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(self.socket_path)
            self._socket.settimeout(1.0)
            return True
        except (ConnectionRefusedError, FileNotFoundError, OSError):
            self._socket = None
            return False

    def send_metric(self, metric: OperationMetric) -> bool:
        """Send a metric to the persistent server"""
        if not self._socket:
            if not self.connect():
                return False

        try:
            data = metric.to_dict()
            message = json.dumps(data) + "\n"
            self._socket.sendall(message.encode("utf-8"))
            return True
        except (BrokenPipeError, ConnectionResetError, OSError):
            self._socket = None
            return False

    def close(self):
        """Close the socket connection"""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None


class MetricsIPCServer:
    """Server for receiving metrics via Unix socket"""

    def __init__(self, socket_path: str, on_metric_received):
        self.socket_path = socket_path
        self.on_metric_received = on_metric_received
        self._socket: Optional[socket.socket] = None
        self._running = False

    def start(self):
        """Start listening for metrics"""
        # Remove existing socket file if it exists
        if Path(self.socket_path).exists():
            os.unlink(self.socket_path)

        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(self.socket_path)
        self._socket.listen(5)
        self._socket.settimeout(1.0)
        self._running = True

        print(f"IPC server listening on {self.socket_path}", flush=True)

    def accept_connections(self):
        """Accept and handle client connections (non-blocking check)"""
        if not self._running or not self._socket:
            return

        try:
            conn, _ = self._socket.accept()
            conn.settimeout(1.0)
            self._handle_client(conn)
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error accepting connection: {e}", flush=True)

    def _handle_client(self, conn: socket.socket):
        """Handle a client connection"""
        buffer = ""
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break

                buffer += data.decode("utf-8")

                # Process complete messages (newline-delimited)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._process_metric(line.strip())
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error handling client: {e}", flush=True)
        finally:
            conn.close()

    def _process_metric(self, json_str: str):
        """Process a received metric"""
        try:
            data = json.loads(json_str)
            self.on_metric_received(data)
        except Exception as e:
            print(f"Error processing metric: {e}", flush=True)

    def stop(self):
        """Stop the server"""
        self._running = False
        if self._socket:
            self._socket.close()
            self._socket = None

        if Path(self.socket_path).exists():
            os.unlink(self.socket_path)
