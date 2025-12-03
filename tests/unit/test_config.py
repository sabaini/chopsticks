"""Unit tests for config loader utility."""

import yaml
import pytest
from pathlib import Path

from chopsticks.utils.config_loader import load_config


class TestLoadConfig:
    """Test load_config utility method."""

    def test_load_config_returns_valid_dict(self, tmp_path):
        """Validate load_config utility continues to function properly."""
        config_data = {
            "endpoint": "http://localhost:80",
            "access_key": "test-key",
            "secret_key": "test-secret",
            "bucket": "test-bucket",
            "region": "default",
        }

        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = load_config(str(config_file))

        assert isinstance(result, dict)
        assert result["endpoint"] == config_data["endpoint"]
        assert result["access_key"] == config_data["access_key"]
        assert result["secret_key"] == config_data["secret_key"]
        assert result["bucket"] == config_data["bucket"]
        assert result["region"] == config_data["region"]

    def test_load_config_file_not_found(self, tmp_path):
        """Validate load_config raises FileNotFoundError for missing files."""
        non_existent = tmp_path / "missing.yaml"

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(str(non_existent))
