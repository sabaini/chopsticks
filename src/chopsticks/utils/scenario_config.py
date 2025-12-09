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


"""Utility functions for loading scenario configuration."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def get_default_scenario_config_path() -> Path:
    """
    Get path to default scenario config file.

    Returns:
        Path to scenario_config_default.yaml in project config directory
    """
    # Get path relative to this module
    utils_dir = Path(__file__).parent
    project_root = utils_dir.parent.parent.parent
    return project_root / "config" / "scenario_config_default.yaml"


def load_scenario_config(scenario_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Load scenario configuration.

    Priority:
    1. Custom config from CHOPSTICKS_SCENARIO_CONFIG env var (if set and non-empty)
    2. Default config from config/scenario_config_default.yaml

    Args:
        scenario_name: Optional scenario name to extract from config.
                      If provided, returns config[scenario_name].
                      If None, returns entire config.

    Returns:
        Dictionary with scenario configuration.
        Returns empty dict if no config is available.
    """
    config = {}

    # Try to load custom config from environment variable
    custom_config_path = os.environ.get("CHOPSTICKS_SCENARIO_CONFIG", "")
    if custom_config_path:  # Non-empty string
        custom_path = Path(custom_config_path)
        if custom_path.exists():
            try:
                with open(custom_path, "r") as f:
                    config = yaml.safe_load(f) or {}
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load scenario config from {custom_config_path}: {e}"
                )

    # If no custom config loaded, use default
    if not config:
        default_path = get_default_scenario_config_path()
        if default_path.exists():
            try:
                with open(default_path, "r") as f:
                    config = yaml.safe_load(f) or {}
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load default scenario config from {default_path}: {e}"
                )

    # Return specific scenario config if requested
    if scenario_name and isinstance(config, dict):
        return config.get(scenario_name, {})

    return config


def get_scenario_value(scenario_name: str, key: str, required: bool = True) -> Any:
    """
    Get a scenario configuration value.

    Args:
        scenario_name: Name of the scenario
        key: Configuration key to retrieve
        required: If True, raises error when key is not found. If False, returns None.

    Returns:
        Configuration value from scenario config

    Raises:
        RuntimeError: If required=True and key is not found in config
    """
    config = load_scenario_config(scenario_name)

    if key not in config:
        if required:
            raise RuntimeError(
                f"Required configuration '{key}' not found in scenario '{scenario_name}'. "
                f"Please provide a scenario config file or ensure the default config "
                f"(config/scenario_config_default.yaml) contains this value."
            )
        return None

    return config[key]
