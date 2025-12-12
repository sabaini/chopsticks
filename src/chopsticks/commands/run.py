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
    leader = getattr(args, "leader", False)
    worker = getattr(args, "worker", False)
    expect_workers = getattr(args, "expect_workers", None)

    if leader and worker:
        raise ValueError("Cannot specify both --leader and --worker")

    if args.headless and not worker:
        if args.users is None:
            raise ValueError("--users is required in headless mode (unless --worker)")
        if args.spawn_rate is None:
            raise ValueError(
                "--spawn-rate is required in headless mode (unless --worker)"
            )

    if expect_workers and not leader:
        raise ValueError("--expect-workers can only be used with --leader")


def build_locust_command(args) -> tuple[List[str], str]:
    """Build Locust command from parsed arguments."""
    import uuid
    from datetime import datetime

    cmd = ["locust", "-f", args.locustfile]
    run_dir = ""

    leader = getattr(args, "leader", False)
    worker = getattr(args, "worker", False)

    # Distributed mode: leader (locust calls this "master")
    if leader:
        cmd.append("--master")
        cmd.extend(["--master-bind-host", "0.0.0.0"])
        expect_workers = getattr(args, "expect_workers", None)
        if expect_workers:
            cmd.extend(["--expect-workers", str(expect_workers)])
        expect_workers_max_wait = getattr(args, "expect_workers_max_wait", None)
        if expect_workers_max_wait:
            cmd.extend(["--expect-workers-max-wait", str(expect_workers_max_wait)])

    # Distributed mode: worker
    if worker:
        cmd.append("--worker")
        leader_host = getattr(args, "leader_host", "127.0.0.1")
        cmd.extend(["--master-host", leader_host])

    # Headless mode
    if args.headless:
        cmd.append("--headless")

        # Users and spawn rate only for leader or standalone (not workers)
        if not worker:
            cmd.extend(["-u", str(args.users)])
            cmd.extend(["-r", str(args.spawn_rate)])

        # Create run-specific directory with abbreviated run ID (leader or standalone)
        if not worker:
            # Check if CHOPSTICKS_RUN_DIR is already set (e.g., by charm)
            run_dir = os.environ.get("CHOPSTICKS_RUN_DIR", "")
            if not run_dir:
                # Create our own directory if not pre-configured
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                run_id = str(uuid.uuid4())[:8]
                run_dir = f"/tmp/chopsticks/{timestamp}_{run_id}"
                os.environ["CHOPSTICKS_RUN_DIR"] = run_dir

            os.makedirs(run_dir, exist_ok=True)

            cmd.extend(["--html", f"{run_dir}/locust_report.html"])
            cmd.extend(["--csv", f"{run_dir}/locust"])

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
