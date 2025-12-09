# Copyright 2025 Ubuntu
# See LICENSE file for licensing details.

"""Unit tests for the Chopsticks charm."""

import pytest
from ops import testing

from charm import ChopsticksCharm


@pytest.fixture
def valid_s3_config() -> dict:
    """Return valid S3 configuration."""
    return {
        "s3-endpoint": "http://10.0.0.1:80",
        "s3-access-key": "test-access-key",
        "s3-secret-key": "test-secret-key",
        "s3-bucket": "test-bucket",
        "s3-region": "us-east-1",
    }


@pytest.fixture
def harness() -> testing.Harness:
    """Return a testing harness for the charm."""
    harness = testing.Harness(ChopsticksCharm)
    harness.set_model_name("test-model")
    yield harness
    harness.cleanup()


def test_start_without_config_sets_blocked_status(harness: testing.Harness):
    """Test that start without S3 config sets BlockedStatus."""
    harness.begin()
    harness.charm.on.start.emit()
    assert harness.charm.unit.status.name == "blocked"
    assert "Missing S3 configuration" in harness.charm.unit.status.message


def test_start_with_valid_config_sets_waiting_status(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test that start with valid config sets WaitingStatus (no leader yet)."""
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()
    harness.charm.on.start.emit()
    assert harness.charm.unit.status.name == "waiting"
    assert "Waiting for leader address" in harness.charm.unit.status.message


def test_start_as_leader_sets_active_status(harness: testing.Harness, valid_s3_config: dict):
    """Test that start as leader with valid config sets ActiveStatus."""
    harness.set_leader(True)
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()
    harness.charm.on.start.emit()
    assert harness.charm.unit.status.name == "active"
    assert "Leader ready" in harness.charm.unit.status.message


def test_is_config_valid_with_all_required_fields(harness: testing.Harness, valid_s3_config: dict):
    """Test _is_config_valid returns True when all required fields present."""
    harness.update_config(valid_s3_config)
    harness.begin()
    assert harness.charm._is_config_valid() is True


def test_is_config_valid_missing_endpoint(harness: testing.Harness, valid_s3_config: dict):
    """Test _is_config_valid returns False when endpoint missing."""
    del valid_s3_config["s3-endpoint"]
    harness.update_config(valid_s3_config)
    harness.begin()
    assert harness.charm._is_config_valid() is False


def test_is_config_valid_missing_access_key(harness: testing.Harness, valid_s3_config: dict):
    """Test _is_config_valid returns False when access key missing."""
    del valid_s3_config["s3-access-key"]
    harness.update_config(valid_s3_config)
    harness.begin()
    assert harness.charm._is_config_valid() is False


def test_is_config_valid_missing_secret_key(harness: testing.Harness, valid_s3_config: dict):
    """Test _is_config_valid returns False when secret key missing."""
    del valid_s3_config["s3-secret-key"]
    harness.update_config(valid_s3_config)
    harness.begin()
    assert harness.charm._is_config_valid() is False


def test_is_config_valid_empty_endpoint(harness: testing.Harness, valid_s3_config: dict):
    """Test _is_config_valid returns False when endpoint is empty string."""
    valid_s3_config["s3-endpoint"] = ""
    harness.update_config(valid_s3_config)
    harness.begin()
    assert harness.charm._is_config_valid() is False


def test_start_test_action_fails_on_non_leader(harness: testing.Harness, valid_s3_config: dict):
    """Test start-test action fails when not run on leader."""
    harness.set_leader(False)
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()

    with pytest.raises(testing.ActionFailed) as exc_info:
        harness.run_action("start-test")
    assert "leader" in str(exc_info.value).lower()


def test_start_test_action_fails_without_s3_config(harness: testing.Harness):
    """Test start-test action fails when S3 config is incomplete."""
    harness.set_leader(True)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()

    with pytest.raises(testing.ActionFailed) as exc_info:
        harness.run_action("start-test")
    assert "S3 configuration" in str(exc_info.value)


def test_start_test_action_fails_when_test_already_running(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test start-test action fails when a test is already running."""
    harness.set_leader(True)
    harness.update_config(valid_s3_config)
    rel_id = harness.add_relation("cluster", "chopsticks")
    harness.begin()

    harness.update_relation_data(rel_id, harness.charm.app.name, {"test_state": "running"})

    with pytest.raises(testing.ActionFailed) as exc_info:
        harness.run_action("start-test")
    assert "already running" in str(exc_info.value)


def test_start_test_action_fails_with_invalid_users(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test start-test action fails when users param is not numeric."""
    harness.set_leader(True)
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()

    with pytest.raises(testing.ActionFailed) as exc_info:
        harness.run_action("start-test", {"users": "not-a-number"})
    assert "numeric" in str(exc_info.value)


def test_stop_test_action_fails_on_non_leader(harness: testing.Harness, valid_s3_config: dict):
    """Test stop-test action fails when not run on leader."""
    harness.set_leader(False)
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()

    with pytest.raises(testing.ActionFailed) as exc_info:
        harness.run_action("stop-test")
    assert "leader" in str(exc_info.value).lower()


def test_fetch_metrics_action_fails_on_non_leader(harness: testing.Harness, valid_s3_config: dict):
    """Test fetch-metrics action fails when not run on leader."""
    harness.set_leader(False)
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()

    with pytest.raises(testing.ActionFailed) as exc_info:
        harness.run_action("fetch-metrics")
    assert "leader" in str(exc_info.value).lower()


def test_fetch_metrics_action_fails_without_test_run(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test fetch-metrics action fails when no test run exists."""
    harness.set_leader(True)
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()

    with pytest.raises(testing.ActionFailed) as exc_info:
        harness.run_action("fetch-metrics")
    assert "No test run" in str(exc_info.value)


def test_test_status_action_returns_status(harness: testing.Harness, valid_s3_config: dict):
    """Test test-status action returns current status."""
    harness.set_leader(True)
    harness.update_config(valid_s3_config)
    rel_id = harness.add_relation("cluster", "chopsticks")
    harness.begin()

    harness.update_relation_data(
        rel_id,
        harness.charm.app.name,
        {"test_state": "idle", "leader_address": "10.0.0.1"},
    )

    result = harness.run_action("test-status")
    assert result.results["test-state"] == "idle"
    assert result.results["leader-address"] == "10.0.0.1"
    assert result.results["is-leader"] is True


def test_maybe_start_worker_skipped_on_leader(harness: testing.Harness, valid_s3_config: dict):
    """Test _maybe_start_worker does nothing when unit is leader."""
    harness.set_leader(True)
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()
    harness.charm._maybe_start_worker()


def test_maybe_start_worker_skipped_without_valid_config(harness: testing.Harness):
    """Test _maybe_start_worker does nothing without valid S3 config."""
    harness.set_leader(False)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()
    harness.charm._maybe_start_worker()


def test_maybe_start_worker_skipped_without_leader_address(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test _maybe_start_worker does nothing when leader address not set."""
    harness.set_leader(False)
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()
    harness.charm._maybe_start_worker()


def test_leader_service_content_generates_valid_unit(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test _leader_service_content generates valid systemd unit."""
    valid_s3_config["locust-master-port"] = 5557
    harness.update_config(valid_s3_config)
    harness.begin()

    content = harness.charm._leader_service_content(
        test_run_id="test-123",
        scenario_file="scenarios/test.py",
        users=10,
        spawn_rate=2.0,
        duration="5m",
    )
    assert "[Unit]" in content
    assert "[Service]" in content
    assert "[Install]" in content
    assert "--master" in content
    assert "--headless" in content
    assert "--users=10" in content
    assert "--spawn-rate=2.0" in content
    assert "--run-time=5m" in content
    assert "test-123" in content


def test_leader_webui_service_content_generates_valid_unit(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test _leader_webui_service_content generates valid systemd unit."""
    valid_s3_config["locust-master-port"] = 5557
    valid_s3_config["locust-web-port"] = 8089
    harness.update_config(valid_s3_config)
    harness.begin()

    content = harness.charm._leader_webui_service_content(
        scenario_file="scenarios/test.py",
    )
    assert "[Unit]" in content
    assert "[Service]" in content
    assert "--master" in content
    assert "--web-port=8089" in content
    assert "--headless" not in content


def test_worker_service_content_generates_valid_unit(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test _worker_service_content generates valid systemd unit."""
    valid_s3_config["locust-master-port"] = 5557
    valid_s3_config["scenario-file"] = "scenarios/default.py"
    harness.update_config(valid_s3_config)
    harness.add_relation("cluster", "chopsticks")
    harness.begin()

    content = harness.charm._worker_service_content(leader_host="10.0.0.1")
    assert "[Unit]" in content
    assert "[Service]" in content
    assert "--worker" in content
    assert "--master-host=10.0.0.1" in content
    assert "--master-port=5557" in content


def test_worker_service_content_uses_peer_data_scenario(
    harness: testing.Harness, valid_s3_config: dict
):
    """Test _worker_service_content prefers scenario from peer data."""
    valid_s3_config["locust-master-port"] = 5557
    valid_s3_config["scenario-file"] = "scenarios/default.py"
    harness.update_config(valid_s3_config)
    rel_id = harness.add_relation("cluster", "chopsticks")
    harness.begin()

    harness.update_relation_data(
        rel_id,
        harness.charm.app.name,
        {"scenario_file": "scenarios/override.py"},
    )

    content = harness.charm._worker_service_content(leader_host="10.0.0.1")
    assert "scenarios/override.py" in content
    assert "scenarios/default.py" not in content
