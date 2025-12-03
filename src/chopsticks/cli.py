"""CLI wrapper for Chopsticks load testing framework."""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Chopsticks - Ceph stress testing framework using Locust",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with web UI
  chopsticks --workload-config config/s3_config.yaml -f scenarios/s3_large_objects.py
  
  # Run headless with 10 users for 5 minutes
  chopsticks --workload-config config/s3_config.yaml -f scenarios/s3_large_objects.py \\
    --headless --users 10 --spawn-rate 2 --duration 5m
  
  # Run with custom scenario config
  chopsticks --workload-config config/s3_config.yaml --scenario-config my_scenario.yaml \\
    -f scenarios/s3_large_objects.py --headless --users 50 --spawn-rate 5 --duration 10m
        """,
    )

    # Required arguments
    parser.add_argument(
        "--workload-config",
        required=True,
        type=str,
        help="Path to workload configuration file (e.g., s3_config.yaml). Required.",
    )

    parser.add_argument(
        "-f",
        "--locustfile",
        required=True,
        type=str,
        help="Path to Locust scenario file. Required.",
    )

    # Optional arguments
    parser.add_argument(
        "--scenario-config",
        type=str,
        default=None,
        help="Path to scenario configuration file. Optional, defaults to empty config.",
    )

    # Essential Locust parameters
    parser.add_argument(
        "--headless", action="store_true", help="Run in headless mode (no web UI)."
    )

    parser.add_argument(
        "-u",
        "--users",
        type=int,
        help="Number of concurrent users. Required in headless mode.",
    )

    parser.add_argument(
        "-r",
        "--spawn-rate",
        type=int,
        help="User spawn rate (users per second). Required in headless mode.",
    )

    parser.add_argument(
        "-t",
        "--duration",
        type=str,
        help="Test duration, e.g., 300s, 20m, 3h, 1h30m. Optional.",
    )

    return parser.parse_args(args)


def validate_config_paths(args: argparse.Namespace) -> None:
    """
    Validate configuration file paths exist.

    Args:
        args: Parsed arguments

    Raises:
        FileNotFoundError: If required config files don't exist
    """
    workload_config_path = Path(args.workload_config)
    if not workload_config_path.exists():
        raise FileNotFoundError(
            f"Workload configuration file not found: {args.workload_config}"
        )

    if args.scenario_config:
        scenario_config_path = Path(args.scenario_config)
        if not scenario_config_path.exists():
            raise FileNotFoundError(
                f"Scenario configuration file not found: {args.scenario_config}"
            )

    locustfile_path = Path(args.locustfile)
    if not locustfile_path.exists():
        raise FileNotFoundError(f"Locust scenario file not found: {args.locustfile}")


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate argument combinations.

    Args:
        args: Parsed arguments

    Raises:
        ValueError: If argument combination is invalid
    """
    if args.headless:
        if args.users is None:
            raise ValueError("--users is required in headless mode")
        if args.spawn_rate is None:
            raise ValueError("--spawn-rate is required in headless mode")


def build_locust_command(args: argparse.Namespace) -> tuple[List[str], str]:
    """
    Build Locust command from parsed arguments.

    Args:
        args: Parsed arguments

    Returns:
        Tuple of (command list, run directory path)
    """
    import uuid
    from datetime import datetime

    cmd = ["locust", "-f", args.locustfile]
    run_dir = ""

    # Headless mode
    if args.headless:
        cmd.append("--headless")
        cmd.extend(["-u", str(args.users)])
        cmd.extend(["-r", str(args.spawn_rate)])

        # Create run-specific directory with abbreviated run ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = str(uuid.uuid4())[:8]
        run_dir = f"/tmp/chopsticks/{timestamp}_{run_id}"
        os.makedirs(run_dir, exist_ok=True)

        # Add HTML and CSV reports to run directory
        cmd.extend(["--html", f"{run_dir}/locust_report.html"])
        cmd.extend(["--csv", f"{run_dir}/locust"])

        # Set environment variable for metrics collector to use same directory
        os.environ["CHOPSTICKS_RUN_DIR"] = run_dir

    # Duration
    if args.duration:
        cmd.extend(["-t", args.duration])

    return cmd, run_dir


def detect_workload_type_from_locustfile(locustfile_path: str) -> str:
    """
    Detect workload type by inspecting the scenario file's base class.

    Args:
        locustfile_path: Path to the locustfile

    Returns:
        Workload type (e.g., 's3', 'rbd') in lowercase
    """
    import ast
    import re

    try:
        with open(locustfile_path, "r") as f:
            tree = ast.parse(f.read())

        # Find class definitions that inherit from a workload class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    # Check if base class name contains "Workload"
                    if isinstance(base, ast.Name) and "Workload" in base.id:
                        # Extract workload type from class name (e.g., S3Workload -> s3)
                        match = re.match(r"([A-Z][a-z0-9]+)Workload", base.id)
                        if match:
                            return match.group(1).lower()
                    # Handle attribute access like workloads.s3.S3Workload
                    elif isinstance(base, ast.Attribute) and "Workload" in base.attr:
                        match = re.match(r"([A-Z][a-z0-9]+)Workload", base.attr)
                        if match:
                            return match.group(1).lower()
    except Exception:
        pass

    # Fallback: default to s3
    return "s3"


def set_environment_variables(args: argparse.Namespace) -> None:
    """
    Set environment variables for config paths.

    Args:
        args: Parsed arguments
    """
    workload_config_path = Path(args.workload_config).resolve()

    # Set generic config path
    os.environ["CHOPSTICKS_WORKLOAD_CONFIG"] = str(workload_config_path)

    # Detect workload type from scenario file's base class
    workload_type = detect_workload_type_from_locustfile(args.locustfile).upper()

    # Set workload-specific config path (e.g., S3_CONFIG_PATH)
    os.environ[f"{workload_type}_CONFIG_PATH"] = str(workload_config_path)

    # Set scenario config path (empty string if not provided)
    if args.scenario_config:
        scenario_config_path = Path(args.scenario_config).resolve()
        os.environ["CHOPSTICKS_SCENARIO_CONFIG"] = str(scenario_config_path)
    else:
        os.environ["CHOPSTICKS_SCENARIO_CONFIG"] = ""


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code
    """
    try:
        args = parse_args(argv)

        validate_config_paths(args)
        validate_arguments(args)

        set_environment_variables(args)

        locust_cmd, run_dir = build_locust_command(args)

        print("Starting Chopsticks...")
        print(f"Workload config: {args.workload_config}")
        print(
            f"Scenario config: {args.scenario_config if args.scenario_config else '<empty default>'}"
        )
        print(f"Scenario file: {args.locustfile}")
        if args.headless:
            print(
                f"Mode: Headless ({args.users} users, spawn rate {args.spawn_rate}/s)"
            )
            if args.duration:
                print(f"Duration: {args.duration}")
            if run_dir:
                print(f"Reports: {run_dir}")
        else:
            print("Mode: Web UI (http://localhost:8089)")
        print()

        os.execvp("locust", locust_cmd)

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
