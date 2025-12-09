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


"""Standalone metrics HTTP server that runs as a daemon"""

import argparse
import signal
import sys
from pathlib import Path
from chopsticks.metrics.http_server import MetricsHTTPServer


def main():
    parser = argparse.ArgumentParser(
        description="Run Chopsticks metrics HTTP server as a daemon"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8090, help="Port to bind to")
    parser.add_argument(
        "--socket-path",
        default="/tmp/chopsticks_metrics.sock",
        help="Unix socket path for IPC",
    )
    parser.add_argument("--pid-file", type=Path, help="Path to PID file (optional)")
    parser.add_argument(
        "--state-file", type=Path, required=True, help="Path to state file"
    )
    args = parser.parse_args()

    # Write our own PID to file if specified
    if args.pid_file:
        import os

        args.pid_file.write_text(str(os.getpid()))

    # Create and start server
    server = MetricsHTTPServer(
        host=args.host, port=args.port, socket_path=args.socket_path
    )

    def cleanup():
        """Clean up PID and state files on exit"""
        if args.pid_file and args.pid_file.exists():
            args.pid_file.unlink(missing_ok=True)
        if args.state_file and args.state_file.exists():
            args.state_file.unlink(missing_ok=True)

    # Handle shutdown signals
    shutdown_requested = False

    def signal_handler(sig, frame):
        nonlocal shutdown_requested
        shutdown_requested = True
        server.stop()

    # Register signal handlers before starting server
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Ensure signals aren't blocked
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    try:
        # Start server (this blocks)
        server.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr, flush=True)
    finally:
        cleanup()
        if shutdown_requested:
            print("Shutdown complete", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
