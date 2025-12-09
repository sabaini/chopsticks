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


"""CLI commands for persistent metrics server management"""

from chopsticks.utils.config_loader import load_config
from chopsticks.metrics.daemon import MetricsDaemon


def cmd_metrics_start(args) -> int:
    """Start persistent metrics server

    All configuration comes from the workload config file.
    """
    try:
        # Load config
        config = load_config(args.config)
        metrics_config = config.get("metrics", {})

        # Validate metrics enabled
        if not metrics_config.get("enabled"):
            print("ERROR: Metrics not enabled in config file")
            print("       Set 'metrics.enabled: true' in your config")
            return 1

        # Validate persistent mode allowed
        persistent_config = metrics_config.get("persistent", {})
        if not persistent_config.get("enabled", False):
            print("ERROR: Persistent metrics server not enabled in config")
            print("       Set 'metrics.persistent.enabled: true' in your config")
            return 1

        # Create and start daemon
        daemon = MetricsDaemon(metrics_config)

        if daemon.is_running():
            if args.force:
                print("WARNING: Metrics server already running, stopping it (--force)")
                daemon.stop()
            else:
                print("WARNING: Metrics server already running")
                status = daemon.get_status()
                print(f"         PID: {status['pid']}")
                print(
                    f"         Endpoint: http://{status['host']}:{status['port']}/metrics"
                )
                print("         Use --force to stop and restart")
                return 0

        # Clean up stale files if --force
        if args.force:
            daemon.cleanup_stale_files()

        daemon.start()

        print("SUCCESS: Metrics server started")
        print(
            f"         Endpoint: http://{metrics_config['http_host']}:{metrics_config['http_port']}/metrics"
        )
        print(
            f"         PID file: {persistent_config.get('pid_file', '/tmp/chopsticks_metrics.pid')}"
        )
        print("")
        print("         Run tests with: chopsticks run --workload-config ...")
        print("         Stop with: chopsticks metrics stop --config ...")

        return 0

    except Exception as e:
        print(f"ERROR: Failed to start metrics server: {e}")
        import traceback

        traceback.print_exc()
        return 1


def cmd_metrics_stop(args) -> int:
    """Stop persistent metrics server"""
    try:
        config = load_config(args.config)
        metrics_config = config.get("metrics", {})

        daemon = MetricsDaemon(metrics_config)

        if not daemon.is_running():
            print("WARNING: Metrics server not running")
            return 0

        daemon.stop()
        print("SUCCESS: Metrics server stopped")
        return 0

    except Exception as e:
        print(f"ERROR: Failed to stop metrics server: {e}")
        return 1


def cmd_metrics_status(args) -> int:
    """Check metrics server status"""
    try:
        config = load_config(args.config)
        metrics_config = config.get("metrics", {})

        daemon = MetricsDaemon(metrics_config)

        if not daemon.is_running():
            print("Status: Not running")
            return 0

        status = daemon.get_status()
        print("Status: Running")
        print(f"  PID: {status['pid']}")
        print(f"  Endpoint: http://{status['host']}:{status['port']}/metrics")
        if "start_time" in status:
            print(f"  Started: {status['start_time']}")

        # Try to ping the endpoint
        try:
            import requests

            response = requests.get(
                f"http://{status['host']}:{status['port']}/metrics", timeout=2
            )
            if response.status_code == 200:
                print("  Health: Responding")
            else:
                print(f"  Health: Unexpected status {response.status_code}")
        except ImportError:
            # requests not available, skip health check
            print("  Health: Cannot check (requests library not available)")
        except Exception as e:
            print(f"  Health: Not responding ({e})")

        return 0

    except Exception as e:
        print(f"ERROR: Failed to check status: {e}")
        return 1
