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


import os
import tempfile
from pathlib import Path

from chopsticks.utils.config_loader import (
    load_runtime_config,
    save_runtime_config,
    get_leader_host,
)


class TestRuntimeConfig:
    """Test runtime configuration handling"""

    def test_save_and_load_runtime_config(self):
        """Test saving and loading runtime configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "runtime.yaml"
            config = {"leader_host": "192.168.1.100", "other_param": "value"}

            save_runtime_config(config, config_path)
            loaded = load_runtime_config(config_path)

            assert loaded == config

    def test_load_nonexistent_runtime_config(self):
        """Test loading runtime config when file doesn't exist returns empty dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yaml"
            loaded = load_runtime_config(config_path)
            assert loaded == {}

    def test_get_leader_host_from_env(self):
        """Test getting leader host from environment variable"""
        os.environ["CHOPSTICKS_LEADER_HOST"] = "10.0.0.1"
        try:
            leader_host = get_leader_host()
            assert leader_host == "10.0.0.1"
        finally:
            del os.environ["CHOPSTICKS_LEADER_HOST"]

    def test_get_leader_host_from_config(self, monkeypatch):
        """Test getting leader host from config file when env not set"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "runtime.yaml"
            config = {"leader_host": "192.168.1.100"}
            save_runtime_config(config, config_path)

            # Patch the default config path
            monkeypatch.setattr(
                "chopsticks.utils.config_loader.RUNTIME_CONFIG_PATH", config_path
            )

            # Ensure env var is not set
            monkeypatch.delenv("CHOPSTICKS_LEADER_HOST", raising=False)

            leader_host = get_leader_host()
            assert leader_host == "192.168.1.100"

    def test_get_leader_host_returns_none_when_not_configured(self, monkeypatch):
        """Test getting leader host returns None when not configured"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "runtime.yaml"

            # Patch the default config path
            monkeypatch.setattr(
                "chopsticks.utils.config_loader.RUNTIME_CONFIG_PATH", config_path
            )

            # Ensure env var is not set
            monkeypatch.delenv("CHOPSTICKS_LEADER_HOST", raising=False)

            leader_host = get_leader_host()
            assert leader_host is None

    def test_env_takes_precedence_over_config(self, monkeypatch):
        """Test environment variable takes precedence over config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "runtime.yaml"
            config = {"leader_host": "192.168.1.100"}
            save_runtime_config(config, config_path)

            # Patch the default config path
            monkeypatch.setattr(
                "chopsticks.utils.config_loader.RUNTIME_CONFIG_PATH", config_path
            )

            # Set env var to different value
            monkeypatch.setenv("CHOPSTICKS_LEADER_HOST", "10.0.0.1")

            leader_host = get_leader_host()
            assert leader_host == "10.0.0.1"


class TestRuntimeParam:
    """Test generic runtime parameter handling"""

    def test_get_runtime_param_from_env(self, monkeypatch):
        """Test getting parameter from environment variable"""
        monkeypatch.setenv("TEST_VAR", "test_value")
        from chopsticks.utils.config_loader import get_runtime_param

        value = get_runtime_param("any_key", "TEST_VAR")
        assert value == "test_value"

    def test_get_runtime_param_from_config(self, monkeypatch):
        """Test getting parameter from runtime config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "runtime.yaml"
            config = {"scenario_file": "scenarios/test.py"}
            save_runtime_config(config, config_path)

            monkeypatch.setattr(
                "chopsticks.utils.config_loader.RUNTIME_CONFIG_PATH", config_path
            )

            from chopsticks.utils.config_loader import get_runtime_param

            value = get_runtime_param("scenario_file")
            assert value == "scenarios/test.py"

    def test_get_runtime_param_env_takes_precedence(self, monkeypatch):
        """Test env var takes precedence over config for generic params"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "runtime.yaml"
            config = {"scenario_file": "scenarios/config.py"}
            save_runtime_config(config, config_path)

            monkeypatch.setattr(
                "chopsticks.utils.config_loader.RUNTIME_CONFIG_PATH", config_path
            )
            monkeypatch.setenv("CHOPSTICKS_SCENARIO_FILE", "scenarios/env.py")

            from chopsticks.utils.config_loader import get_runtime_param

            value = get_runtime_param("scenario_file", "CHOPSTICKS_SCENARIO_FILE")
            assert value == "scenarios/env.py"
