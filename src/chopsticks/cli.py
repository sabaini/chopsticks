"""CLI wrapper for Chopsticks load testing framework."""

import argparse
import sys
from typing import List, Optional


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands"""
    parser = argparse.ArgumentParser(
        description="Chopsticks - Ceph stress testing framework using Locust",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # 'run' command (existing behavior)
    run_parser = subparsers.add_parser("run", help="Run load tests")

    run_parser.add_argument(
        "--workload-config",
        required=True,
        type=str,
        help="Path to workload configuration file (e.g., s3_config.yaml). Required.",
    )

    run_parser.add_argument(
        "-f",
        "--locustfile",
        required=True,
        type=str,
        help="Path to Locust scenario file. Required.",
    )

    run_parser.add_argument(
        "--scenario-config",
        type=str,
        help="Path to scenario configuration file (optional).",
    )

    run_parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run in headless mode (no web UI).",
    )

    run_parser.add_argument(
        "--users", "-u", type=int, help="Number of concurrent users (headless mode)."
    )

    run_parser.add_argument(
        "--spawn-rate",
        "-r",
        type=int,
        help="Rate to spawn users at (users per second, headless mode).",
    )

    run_parser.add_argument(
        "--duration",
        "-t",
        type=str,
        help="Test duration (e.g., 300s, 20m, 3h, 1h30m).",
    )

    # 'metrics' command group
    metrics_parser = subparsers.add_parser(
        "metrics", help="Manage persistent metrics server"
    )
    metrics_sub = metrics_parser.add_subparsers(dest="metrics_command")

    # metrics start
    start_parser = metrics_sub.add_parser(
        "start", help="Start persistent metrics server"
    )
    start_parser.add_argument(
        "--config", required=True, help="Path to workload config file"
    )
    start_parser.add_argument(
        "--force",
        action="store_true",
        help="Force cleanup of stale processes and files",
    )

    # metrics stop
    stop_parser = metrics_sub.add_parser("stop", help="Stop persistent metrics server")
    stop_parser.add_argument(
        "--config", required=True, help="Path to workload config file"
    )

    # metrics status
    status_parser = metrics_sub.add_parser("status", help="Check metrics server status")
    status_parser.add_argument(
        "--config", required=True, help="Path to workload config file"
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Handle no subcommand - check if this looks like old-style invocation
    if args.command is None:
        # Try to detect old-style usage (backward compatibility)
        # If argv contains --workload-config and -f, treat as 'run'
        if argv and any("--workload-config" in arg for arg in argv):
            # Re-parse as 'run' command
            argv_with_run = ["run"] + (argv if argv else sys.argv[1:])
            args = parser.parse_args(argv_with_run)
        else:
            parser.print_help()
            return 1

    # Route to appropriate handler
    if args.command == "run":
        from chopsticks.commands.run import cmd_run

        return cmd_run(args)
    elif args.command == "metrics":
        from chopsticks.commands.metrics import (
            cmd_metrics_start,
            cmd_metrics_stop,
            cmd_metrics_status,
        )

        if args.metrics_command == "start":
            return cmd_metrics_start(args)
        elif args.metrics_command == "stop":
            return cmd_metrics_stop(args)
        elif args.metrics_command == "status":
            return cmd_metrics_status(args)
        else:
            parser.parse_args([args.command, "--help"])
            return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
