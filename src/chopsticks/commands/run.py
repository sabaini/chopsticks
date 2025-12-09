"""CLI command for running load tests"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List


def validate_config_paths(args) -> None:
    """Validate configuration file paths exist."""
    workload_config_path = Path(args.workload_config)
    if not workload_config_path.exists():
        raise FileNotFoundError(
            f"Workload configuration file not found: {args.workload_config}"
        )

    if hasattr(args, "scenario_config") and args.scenario_config:
        scenario_config_path = Path(args.scenario_config)
        if not scenario_config_path.exists():
            raise FileNotFoundError(
                f"Scenario configuration file not found: {args.scenario_config}"
            )

    locustfile_path = Path(args.locustfile)
    if not locustfile_path.exists():
        raise FileNotFoundError(f"Locust scenario file not found: {args.locustfile}")


def validate_arguments(args) -> None:
    """Validate argument combinations."""
    if args.headless:
        if args.users is None:
            raise ValueError("--users is required in headless mode")
        if args.spawn_rate is None:
            raise ValueError("--spawn-rate is required in headless mode")


def build_locust_command(args) -> tuple[List[str], str]:
    """Build Locust command from parsed arguments."""
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
    """Detect workload type by inspecting the scenario file's base class."""
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


def set_environment_variables(args) -> None:
    """Set environment variables for config paths."""
    workload_config_path = Path(args.workload_config).resolve()

    # Set generic config path
    os.environ["CHOPSTICKS_WORKLOAD_CONFIG"] = str(workload_config_path)

    # Detect workload type from scenario file's base class
    workload_type = detect_workload_type_from_locustfile(args.locustfile).upper()

    # Set workload-specific config path (e.g., S3_CONFIG_PATH)
    os.environ[f"{workload_type}_CONFIG_PATH"] = str(workload_config_path)

    # Set scenario config path (empty string if not provided)
    if hasattr(args, "scenario_config") and args.scenario_config:
        scenario_config_path = Path(args.scenario_config).resolve()
        os.environ["CHOPSTICKS_SCENARIO_CONFIG"] = str(scenario_config_path)
    else:
        os.environ["CHOPSTICKS_SCENARIO_CONFIG"] = ""


def cmd_run(args) -> int:
    """Execute the run command - run load tests"""
    try:
        validate_config_paths(args)
        validate_arguments(args)

        set_environment_variables(args)

        cmd, run_dir = build_locust_command(args)

        if run_dir:
            print(f"Run directory: {run_dir}")

        print(f"Executing: {' '.join(cmd)}")

        result = subprocess.run(cmd)

        return result.returncode

    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1
