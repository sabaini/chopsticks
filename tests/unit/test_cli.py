"""Unit tests for CLI wrapper."""

import pytest
from unittest.mock import patch

from chopsticks.cli import create_parser
from chopsticks.commands.run import (
    validate_config_paths,
    validate_arguments,
    build_locust_command,
    set_environment_variables,
)


def parse_args(argv):
    """Helper function to parse arguments for tests"""
    parser = create_parser()
    # Prepend 'run' command to argv for backward compatibility with tests
    return parser.parse_args(["run"] + argv)


class TestParseArgs:
    """Test argument parsing."""

    def test_parse_required_args(self):
        """Test parsing required arguments."""
        args = parse_args(
            [
                "--workload-config",
                "config/s3_config.yaml",
                "-f",
                "scenarios/s3_large_objects.py",
            ]
        )

        assert args.workload_config == "config/s3_config.yaml"
        assert args.locustfile == "scenarios/s3_large_objects.py"
        assert args.scenario_config is None
        assert args.headless is False

    def test_parse_with_scenario_config(self):
        """Test parsing with scenario config."""
        args = parse_args(
            [
                "--workload-config",
                "s3.yaml",
                "-f",
                "scenario.py",
                "--scenario-config",
                "scenario.yaml",
            ]
        )

        assert args.scenario_config == "scenario.yaml"

    def test_parse_headless_mode(self):
        """Test parsing headless mode with users and spawn rate."""
        args = parse_args(
            [
                "--workload-config",
                "s3.yaml",
                "-f",
                "scenario.py",
                "--headless",
                "--users",
                "10",
                "--spawn-rate",
                "2",
                "--duration",
                "5m",
            ]
        )

        assert args.headless is True
        assert args.users == 10
        assert args.spawn_rate == 2
        assert args.duration == "5m"

    def test_missing_required_args(self):
        """Test error when required args are missing."""
        with pytest.raises(SystemExit):
            parse_args(["--workload-config", "s3.yaml"])


class TestValidateConfigPaths:
    """Test config path validation."""

    def test_valid_paths(self, tmp_path):
        """Test validation with valid paths."""
        workload_config = tmp_path / "s3_config.yaml"
        scenario_config = tmp_path / "scenario.yaml"
        locustfile = tmp_path / "scenario.py"

        workload_config.write_text("test: config")
        scenario_config.write_text("test: scenario")
        locustfile.write_text("# test scenario")

        args = parse_args(
            [
                "--workload-config",
                str(workload_config),
                "-f",
                str(locustfile),
                "--scenario-config",
                str(scenario_config),
            ]
        )

        validate_config_paths(args)

    def test_missing_workload_config(self, tmp_path):
        """Test error when workload config is missing."""
        locustfile = tmp_path / "scenario.py"
        locustfile.write_text("# test")

        args = parse_args(
            ["--workload-config", str(tmp_path / "missing.yaml"), "-f", str(locustfile)]
        )

        with pytest.raises(
            FileNotFoundError, match="Workload configuration file not found"
        ):
            validate_config_paths(args)

    def test_missing_locustfile(self, tmp_path):
        """Test error when locustfile is missing."""
        workload_config = tmp_path / "s3_config.yaml"
        workload_config.write_text("test: config")

        args = parse_args(
            [
                "--workload-config",
                str(workload_config),
                "-f",
                str(tmp_path / "missing.py"),
            ]
        )

        with pytest.raises(FileNotFoundError, match="Locust scenario file not found"):
            validate_config_paths(args)


class TestValidateArguments:
    """Test argument validation."""

    def test_valid_headless_args(self):
        """Test valid headless arguments."""
        args = parse_args(
            [
                "--workload-config",
                "s3.yaml",
                "-f",
                "scenario.py",
                "--headless",
                "--users",
                "10",
                "--spawn-rate",
                "2",
            ]
        )

        validate_arguments(args)

    def test_headless_without_users(self):
        """Test error when headless mode lacks users."""
        args = parse_args(
            [
                "--workload-config",
                "s3.yaml",
                "-f",
                "scenario.py",
                "--headless",
                "--spawn-rate",
                "2",
            ]
        )

        with pytest.raises(ValueError, match="--users is required in headless mode"):
            validate_arguments(args)

    def test_headless_without_spawn_rate(self):
        """Test error when headless mode lacks spawn rate."""
        args = parse_args(
            [
                "--workload-config",
                "s3.yaml",
                "-f",
                "scenario.py",
                "--headless",
                "--users",
                "10",
            ]
        )

        with pytest.raises(
            ValueError, match="--spawn-rate is required in headless mode"
        ):
            validate_arguments(args)

    def test_web_ui_mode(self):
        """Test web UI mode without users/spawn rate."""
        args = parse_args(["--workload-config", "s3.yaml", "-f", "scenario.py"])

        validate_arguments(args)


class TestBuildLocustCommand:
    """Test Locust command building."""

    def test_web_ui_mode_command(self):
        """Test command for web UI mode."""
        args = parse_args(
            ["--workload-config", "s3.yaml", "-f", "scenarios/s3_large_objects.py"]
        )

        cmd, run_dir = build_locust_command(args)

        assert cmd == ["locust", "-f", "scenarios/s3_large_objects.py"]
        assert run_dir == ""

    def test_headless_mode_command(self):
        """Test command for headless mode."""
        args = parse_args(
            [
                "--workload-config",
                "s3.yaml",
                "-f",
                "scenarios/s3_large_objects.py",
                "--headless",
                "--users",
                "10",
                "--spawn-rate",
                "2",
                "--duration",
                "5m",
            ]
        )

        cmd, run_dir = build_locust_command(args)

        assert cmd[0] == "locust"
        assert "-f" in cmd
        assert "scenarios/s3_large_objects.py" in cmd
        assert "--headless" in cmd
        assert "-u" in cmd and "10" in cmd
        assert "-r" in cmd and "2" in cmd
        assert "-t" in cmd and "5m" in cmd
        assert "--html" in cmd
        assert "--csv" in cmd
        assert run_dir.startswith("/tmp/chopsticks/")

    def test_headless_without_duration(self):
        """Test headless command without duration."""
        args = parse_args(
            [
                "--workload-config",
                "s3.yaml",
                "-f",
                "scenario.py",
                "--headless",
                "--users",
                "5",
                "--spawn-rate",
                "1",
            ]
        )

        cmd, run_dir = build_locust_command(args)

        assert cmd[0] == "locust"
        assert "-f" in cmd
        assert "scenario.py" in cmd
        assert "--headless" in cmd
        assert "-u" in cmd and "5" in cmd
        assert "-r" in cmd and "1" in cmd
        assert "-t" not in cmd
        assert run_dir.startswith("/tmp/chopsticks/")


class TestSetEnvironmentVariables:
    """Test environment variable setting."""

    def test_set_workload_config_env(self, tmp_path):
        """Test setting workload config environment variable."""
        workload_config = tmp_path / "s3_config.yaml"
        workload_config.write_text("test: config")
        locustfile = tmp_path / "s3_scenario.py"
        # Create a proper scenario file with S3Workload class
        locustfile.write_text(
            "from locust import User\nclass S3Workload(User):\n    pass\nclass TestScenario(S3Workload):\n    pass"
        )

        args = parse_args(
            ["--workload-config", str(workload_config), "-f", str(locustfile)]
        )

        import os

        with patch.dict(os.environ, {}, clear=True):
            set_environment_variables(args)

            assert "CHOPSTICKS_WORKLOAD_CONFIG" in os.environ
            assert "S3_CONFIG_PATH" in os.environ
            assert os.environ["CHOPSTICKS_SCENARIO_CONFIG"] == ""

    def test_set_scenario_config_env(self, tmp_path):
        """Test setting scenario config environment variable."""
        workload_config = tmp_path / "rbd_config.yaml"
        scenario_config = tmp_path / "scenario.yaml"
        locustfile = tmp_path / "rbd_scenario.py"
        workload_config.write_text("test: config")
        scenario_config.write_text("scenario: config")
        # Create a proper scenario file with RbdWorkload class
        locustfile.write_text(
            "from locust import User\nclass RbdWorkload(User):\n    pass\nclass TestScenario(RbdWorkload):\n    pass"
        )

        args = parse_args(
            [
                "--workload-config",
                str(workload_config),
                "-f",
                str(locustfile),
                "--scenario-config",
                str(scenario_config),
            ]
        )

        import os

        with patch.dict(os.environ, {}, clear=True):
            set_environment_variables(args)

            assert "CHOPSTICKS_SCENARIO_CONFIG" in os.environ
            assert os.environ["CHOPSTICKS_SCENARIO_CONFIG"] != ""
            assert "RBD_CONFIG_PATH" in os.environ

    def test_empty_scenario_config_default(self, tmp_path):
        """Test empty scenario config by default."""
        workload_config = tmp_path / "s3_config.yaml"
        workload_config.write_text("test: config")
        locustfile = tmp_path / "s3_scenario.py"
        # Create a proper scenario file with S3Workload class
        locustfile.write_text(
            "from locust import User\nclass S3Workload(User):\n    pass\nclass TestScenario(S3Workload):\n    pass"
        )

        args = parse_args(
            ["--workload-config", str(workload_config), "-f", str(locustfile)]
        )

        import os

        with patch.dict(os.environ, {}, clear=True):
            set_environment_variables(args)

            assert os.environ["CHOPSTICKS_SCENARIO_CONFIG"] == ""
