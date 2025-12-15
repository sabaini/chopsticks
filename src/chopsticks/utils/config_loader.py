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
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


RUNTIME_CONFIG_PATH = Path("/etc/chopsticks/runtime.yaml")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load YAML configuration file

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_config_path(workload: str, config_name: str | None = None) -> Path:
    """
    Get configuration file path

    Args:
        workload: Workload name (e.g., 's3', 'rbd')
        config_name: Optional config name, defaults to <workload>_config.yaml

    Returns:
        Path to configuration file
    """
    if config_name is None:
        config_name = f"{workload}_config.yaml"

    # Try multiple paths
    paths = [
        Path.cwd() / "config" / config_name,
        Path(__file__).parent.parent / "config" / config_name,
        Path.home() / ".chopsticks" / config_name,
    ]

    for path in paths:
        if path.exists():
            return path

    # Return default path (will fail later if not exists)
    return paths[0]


def load_runtime_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load runtime configuration (leader address, etc.)

    Args:
        config_path: Optional path to runtime config, defaults to /etc/chopsticks/runtime.yaml

    Returns:
        Runtime configuration dictionary (empty dict if file doesn't exist)
    """
    path = config_path or RUNTIME_CONFIG_PATH
    if not path.exists():
        return {}

    with open(path, "r") as f:
        config = yaml.safe_load(f) or {}
    return config


def save_runtime_config(config: Dict[str, Any], config_path: Optional[Path] = None) -> None:
    """
    Save runtime configuration

    Args:
        config: Runtime configuration dictionary
        config_path: Optional path to runtime config, defaults to /etc/chopsticks/runtime.yaml
    """
    path = config_path or RUNTIME_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        yaml.safe_dump(config, f)


def get_leader_host() -> Optional[str]:
    """
    Get leader host from runtime config or environment variable

    Returns:
        Leader host address or None if not configured
    """
    # Environment variable takes precedence
    leader_host = os.environ.get("CHOPSTICKS_LEADER_HOST")
    if leader_host:
        return leader_host

    # Fall back to runtime config
    runtime_config = load_runtime_config()
    return runtime_config.get("leader_host")


def get_runtime_param(key: str, env_var: Optional[str] = None) -> Optional[str]:
    """
    Get a runtime parameter from environment or config file

    Args:
        key: Runtime config key to retrieve
        env_var: Optional environment variable name (takes precedence)

    Returns:
        Parameter value or None if not configured
    """
    # Environment variable takes precedence if provided
    if env_var:
        value = os.environ.get(env_var)
        if value:
            return value

    # Fall back to runtime config
    runtime_config = load_runtime_config()
    return runtime_config.get(key)
