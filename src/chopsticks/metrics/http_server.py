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


"""HTTP server to expose Prometheus metrics"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Optional
import time

from .prometheus_exporter import PrometheusExporter
from .ipc import MetricsIPCServer
from .models import OperationMetric, OperationType, WorkloadType
from datetime import datetime


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint"""

    exporter: Optional[PrometheusExporter] = None

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()

            if self.exporter:
                metrics_text = self.exporter.export()
                self.wfile.write(metrics_text.encode("utf-8"))
            else:
                self.wfile.write(b"# No metrics available\n")
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = b"""
            <html>
            <head><title>Chopsticks Metrics</title></head>
            <body>
            <h1>Chopsticks Metrics Exporter</h1>
            <p><a href="/metrics">Metrics endpoint</a></p>
            </body>
            </html>
            """
            self.wfile.write(html)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


class MetricsHTTPServer:
    """HTTP server for Prometheus metrics (persistent mode with IPC)"""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9090,
        socket_path: str = "/tmp/chopsticks_metrics.sock",
    ):
        self.host = host
        self.port = port
        self.socket_path = socket_path
        self.exporter = PrometheusExporter()
        self.server: Optional[HTTPServer] = None
        self.ipc_server: Optional[MetricsIPCServer] = None
        self._ipc_thread: Optional[threading.Thread] = None
        self._running = False

    def _on_metric_received(self, metric_data: dict):
        """Callback when a metric is received via IPC"""
        try:
            # Reconstruct OperationMetric from dict
            metric_data["timestamp_start"] = datetime.fromisoformat(
                metric_data["timestamp_start"]
            )
            metric_data["timestamp_end"] = datetime.fromisoformat(
                metric_data["timestamp_end"]
            )
            metric_data["operation_type"] = OperationType(metric_data["operation_type"])
            metric_data["workload_type"] = WorkloadType(metric_data["workload_type"])

            metric = OperationMetric(**metric_data)
            self.exporter.add_operation_metric(metric)
        except Exception as e:
            print(f"Error reconstructing metric: {e}", flush=True)

    def _ipc_loop(self):
        """Background thread for handling IPC connections"""
        while self._running:
            self.ipc_server.accept_connections()
            time.sleep(0.01)

    def start(self):
        """Start the HTTP server and IPC server"""
        MetricsHandler.exporter = self.exporter

        # Start IPC server
        self.ipc_server = MetricsIPCServer(self.socket_path, self._on_metric_received)
        self.ipc_server.start()

        # Start IPC handling thread
        self._running = True
        self._ipc_thread = threading.Thread(target=self._ipc_loop, daemon=True)
        self._ipc_thread.start()

        # Start HTTP server (blocking)
        self.server = HTTPServer((self.host, self.port), MetricsHandler)
        # Allow quick reuse of the port after shutdown
        self.server.allow_reuse_address = True
        print(
            f"Metrics server listening on http://{self.host}:{self.port}/metrics",
            flush=True,
        )
        try:
            # Use poll_interval to allow signals to be processed
            self.server.serve_forever(poll_interval=0.5)
        except (KeyboardInterrupt, SystemExit):
            # Handle both Ctrl+C and sys.exit() gracefully
            pass

    def stop(self):
        """Stop the HTTP server and IPC server"""
        self._running = False

        if self.ipc_server:
            self.ipc_server.stop()

        if self.server:
            # Call shutdown in a separate thread to avoid deadlock
            # (shutdown() waits for serve_forever() to exit)
            def shutdown_server():
                self.server.shutdown()
                self.server.server_close()

            shutdown_thread = threading.Thread(target=shutdown_server, daemon=True)
            shutdown_thread.start()
            shutdown_thread.join(timeout=5)
            print("Metrics server stopped", flush=True)

    def get_exporter(self) -> PrometheusExporter:
        """Get the Prometheus exporter"""
        return self.exporter
