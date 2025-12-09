# Copyright 2025 Ubuntu
# See LICENSE file for licensing details.
#
# Integration tests for the Chopsticks charm based on TESTING.md
# Uses Jubilant library: https://documentation.ubuntu.com/jubilant/

import json
import logging
import pathlib
import time

import jubilant
import pytest

logger = logging.getLogger(__name__)

# Minimal test parameters for fast integration tests
MIN_USERS = 1
MIN_SPAWN_RATE = 0.5
SHORT_DURATION = "20s"
MEDIUM_DURATION = "30s"

# Use example scenario with small 1KB objects for fast tests
TEST_SCENARIO = "src/chopsticks/scenarios/example_scenario.py"


@pytest.fixture(scope="module")
def microceph_s3(juju: jubilant.Juju) -> dict[str, str]:
    """Deploy MicroCeph and configure S3 (RGW).

    Returns S3 credentials and endpoint info.
    """
    logger.info("Deploying MicroCeph with 1 unit and storage (VM)...")
    juju.deploy(
        "microceph",
        num_units=1,
        constraints={"root-disk": "20G", "mem": "4G", "virt-type": "virtual-machine"},
        storage={"osd-standalone": "loop,2G,6"},
    )

    logger.info("Waiting for MicroCeph to become active...")
    juju.wait(lambda status: status.apps["microceph"].is_active, timeout=600)

    logger.info("Enabling RGW (S3 gateway)...")
    juju.config("microceph", values={"enable-rgw": "*"})

    logger.info("Waiting for RGW to be ready...")
    time.sleep(30)

    logger.info("Creating S3 user...")
    user_output = juju.ssh(
        "microceph/0",
        "sudo microceph.radosgw-admin user create --uid=test --display-name='Test User'",
    )
    user_data = json.loads(user_output)
    access_key = user_data["keys"][0]["access_key"]
    secret_key = user_data["keys"][0]["secret_key"]

    status = juju.status()
    microceph_ip = status.apps["microceph"].units["microceph/0"].public_address

    logger.info("Installing AWS CLI on microceph/0...")
    juju.ssh("microceph/0", "sudo snap install aws-cli --classic")

    logger.info("Creating test bucket...")
    juju.ssh(
        "microceph/0",
        f"AWS_ACCESS_KEY_ID={access_key} AWS_SECRET_ACCESS_KEY={secret_key} "
        f"/snap/bin/aws --endpoint-url http://localhost:80 --region default s3 mb s3://test-bucket",
    )

    return {
        "endpoint": f"http://{microceph_ip}:80",
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket": "test-bucket",
        "region": "default",
    }


def _get_leader_unit(juju: jubilant.Juju, app: str = "chopsticks") -> str:
    """Get the name of the current leader unit for an application."""
    for unit_name, unit in juju.status().apps[app].units.items():
        if unit.leader:
            return unit_name
    raise RuntimeError(f"No leader found for {app}")


class TestBasicDeployment:
    """TC1: Basic Deployment - Verify charm deploys and installs dependencies correctly."""

    def test_deploy_blocked_without_s3_config(
        self, charm: pathlib.Path, juju: jubilant.Juju
    ) -> None:
        """Verify charm deploys and reaches blocked status without S3 config."""
        logger.info("Deploying chopsticks charm with 3 units...")
        juju.deploy(str(charm.resolve()), app="chopsticks", num_units=3)

        logger.info("Waiting for blocked status...")
        juju.wait(
            lambda status: all(
                unit.is_blocked for unit in status.apps["chopsticks"].units.values()
            ),
            timeout=600,
        )

        status = juju.status()
        for unit_name, unit in status.apps["chopsticks"].units.items():
            assert "S3 configuration" in unit.workload_status.message, (
                f"{unit_name} should show S3 configuration message"
            )


class TestLeaderElection:
    """TC2: Leader Election and Peer Discovery."""

    def test_leader_election_and_peer_discovery(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Verify leader is elected and workers discover leader address."""
        if "chopsticks" not in juju.status().apps:
            juju.deploy(str(charm.resolve()), app="chopsticks", num_units=3)
            juju.wait(
                lambda status: "chopsticks" in status.apps,
                timeout=600,
            )

        logger.info("Configuring S3 credentials...")
        juju.config(
            "chopsticks",
            values={
                "s3-endpoint": microceph_s3["endpoint"],
                "s3-access-key": microceph_s3["access_key"],
                "s3-secret-key": microceph_s3["secret_key"],
                "s3-bucket": microceph_s3["bucket"],
                "s3-region": microceph_s3["region"],
                "scenario-file": TEST_SCENARIO,
                "locust-loglevel": "DEBUG",
            },
        )

        logger.info("Waiting for active status...")
        juju.wait(jubilant.all_active, timeout=300)

        logger.info("Verifying leader status via test-status action...")
        leader = _get_leader_unit(juju)
        result = juju.run(leader, "test-status")
        assert result.results["is-leader"] == "True"

        status = juju.status()
        leader_unit = None
        for unit_name, unit in status.apps["chopsticks"].units.items():
            if "Leader ready" in unit.workload_status.message:
                leader_unit = unit_name
                break

        assert leader_unit is not None, "Should have a leader with 'Leader ready' status"

        for unit_name, unit in status.apps["chopsticks"].units.items():
            if unit_name != leader_unit:
                assert "Worker" in unit.workload_status.message, (
                    f"{unit_name} should show Worker status"
                )


class TestStartTest:
    """TC3: Start Test Action."""

    def test_start_test_action(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Verify distributed test execution starts correctly."""
        self._ensure_deployed_and_configured(charm, juju, microceph_s3)

        logger.info("Starting test...")
        leader = _get_leader_unit(juju)
        result = juju.run(
            leader,
            "start-test",
            params={"users": MIN_USERS, "spawn-rate": MIN_SPAWN_RATE, "duration": SHORT_DURATION},
        )

        assert result.results["status"] == "started"
        assert result.results.get("test-run-id"), "Should have a test-run-id"

        logger.info("Verifying test state via status action...")
        status_result = juju.run(leader, "test-status")
        assert status_result.results["test-state"] == "running"
        assert status_result.results["leader-running"] == "True"

        logger.info("Waiting for test to complete...")
        time.sleep(25)

    def _ensure_deployed_and_configured(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Ensure chopsticks is deployed and configured."""
        if "chopsticks" not in juju.status().apps:
            juju.deploy(str(charm.resolve()), app="chopsticks", num_units=3)

        juju.config(
            "chopsticks",
            values={
                "s3-endpoint": microceph_s3["endpoint"],
                "s3-access-key": microceph_s3["access_key"],
                "s3-secret-key": microceph_s3["secret_key"],
                "s3-bucket": microceph_s3["bucket"],
                "s3-region": microceph_s3["region"],
                "scenario-file": TEST_SCENARIO,
                "locust-loglevel": "DEBUG",
            },
        )
        juju.wait(jubilant.all_active, timeout=300)


class TestStopTest:
    """TC4: Stop Test Action."""

    def test_stop_test_action(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Verify test can be stopped cleanly."""
        self._ensure_running_test(charm, juju, microceph_s3)

        logger.info("Stopping test...")
        leader = _get_leader_unit(juju)
        result = juju.run(leader, "stop-test")
        assert result.results["status"] == "stopped"

        logger.info("Verifying test state...")
        status_result = juju.run(leader, "test-status")
        assert status_result.results["test-state"] == "stopped"
        assert status_result.results["leader-running"] == "False"

    def _ensure_running_test(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Ensure a test is running."""
        if "chopsticks" not in juju.status().apps:
            juju.deploy(str(charm.resolve()), app="chopsticks", num_units=3)

        juju.config(
            "chopsticks",
            values={
                "s3-endpoint": microceph_s3["endpoint"],
                "s3-access-key": microceph_s3["access_key"],
                "s3-secret-key": microceph_s3["secret_key"],
                "s3-bucket": microceph_s3["bucket"],
                "s3-region": microceph_s3["region"],
                "scenario-file": TEST_SCENARIO,
                "locust-loglevel": "DEBUG",
            },
        )
        juju.wait(jubilant.all_active, timeout=300)

        leader = _get_leader_unit(juju)
        status_result = juju.run(leader, "test-status")
        if status_result.results["test-state"] != "running":
            juju.run(
                leader,
                "start-test",
                params={
                    "users": MIN_USERS,
                    "spawn-rate": MIN_SPAWN_RATE,
                    "duration": MEDIUM_DURATION,
                },
            )


class TestFetchMetrics:
    """TC5: Fetch Metrics Action."""

    def test_fetch_metrics_action(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Verify metrics are collected and retrievable."""
        self._ensure_deployed_and_configured(charm, juju, microceph_s3)

        logger.info("Running a short test...")
        leader = _get_leader_unit(juju)
        juju.run(
            leader,
            "start-test",
            params={"users": MIN_USERS, "spawn-rate": MIN_SPAWN_RATE, "duration": SHORT_DURATION},
        )
        time.sleep(25)

        logger.info("Fetching metrics...")
        result = juju.run(leader, "fetch-metrics", params={"format": "summary"})

        assert result.results.get("files"), "Should have files listed"
        files = result.results["files"]
        assert "metrics" in files.lower() or "report" in files.lower(), (
            "Should have metrics or report files"
        )

    def _ensure_deployed_and_configured(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Ensure chopsticks is deployed and configured."""
        if "chopsticks" not in juju.status().apps:
            juju.deploy(str(charm.resolve()), app="chopsticks", num_units=3)

        juju.config(
            "chopsticks",
            values={
                "s3-endpoint": microceph_s3["endpoint"],
                "s3-access-key": microceph_s3["access_key"],
                "s3-secret-key": microceph_s3["secret_key"],
                "s3-bucket": microceph_s3["bucket"],
                "s3-region": microceph_s3["region"],
                "scenario-file": TEST_SCENARIO,
                "locust-loglevel": "DEBUG",
            },
        )
        juju.wait(jubilant.all_active, timeout=300)


class TestDynamicScaling:
    """TC6: Dynamic Scaling."""

    def test_dynamic_scaling(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Verify adding units increases worker count."""
        self._ensure_deployed_and_configured(charm, juju, microceph_s3)

        logger.info("Getting initial worker count...")
        leader = _get_leader_unit(juju)
        initial_result = juju.run(leader, "test-status")
        initial_count = int(initial_result.results["worker-count"])

        logger.info("Adding 2 more units...")
        juju.add_unit("chopsticks", num_units=2)

        logger.info("Waiting for new units to be ready...")
        juju.wait(jubilant.all_active, timeout=600)

        logger.info("Verifying worker count increased...")
        new_result = juju.run(leader, "test-status")
        new_count = int(new_result.results["worker-count"])

        assert new_count == initial_count + 2, (
            f"Worker count should increase by 2: was {initial_count}, now {new_count}"
        )

        status = juju.status()
        for unit_name, unit in status.apps["chopsticks"].units.items():
            if "Worker" in unit.workload_status.message:
                assert (
                    "connected" in unit.workload_status.message.lower()
                    or "ready" in unit.workload_status.message.lower()
                ), f"{unit_name} should show connected or ready status"

    def _ensure_deployed_and_configured(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Ensure chopsticks is deployed and configured."""
        if "chopsticks" not in juju.status().apps:
            juju.deploy(str(charm.resolve()), app="chopsticks", num_units=3)

        juju.config(
            "chopsticks",
            values={
                "s3-endpoint": microceph_s3["endpoint"],
                "s3-access-key": microceph_s3["access_key"],
                "s3-secret-key": microceph_s3["secret_key"],
                "s3-bucket": microceph_s3["bucket"],
                "s3-region": microceph_s3["region"],
                "scenario-file": TEST_SCENARIO,
                "locust-loglevel": "DEBUG",
            },
        )
        juju.wait(jubilant.all_active, timeout=300)


class TestPreventDuplicateTests:
    """TC7: Prevent Duplicate Tests."""

    def test_prevent_duplicate_tests(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Verify only one test can run at a time."""
        self._ensure_deployed_and_configured(charm, juju, microceph_s3)

        logger.info("Starting first test...")
        leader = _get_leader_unit(juju)
        juju.run(
            leader,
            "start-test",
            params={"users": MIN_USERS, "spawn-rate": MIN_SPAWN_RATE, "duration": MEDIUM_DURATION},
        )

        logger.info("Attempting to start second test (should fail)...")
        with pytest.raises(jubilant.TaskError) as exc_info:
            juju.run(
                leader,
                "start-test",
                params={
                    "users": MIN_USERS,
                    "spawn-rate": MIN_SPAWN_RATE,
                    "duration": SHORT_DURATION,
                },
            )

        assert "already running" in str(exc_info.value).lower()

        logger.info("Stopping the test...")
        juju.run(leader, "stop-test")

    def _ensure_deployed_and_configured(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Ensure chopsticks is deployed and configured."""
        if "chopsticks" not in juju.status().apps:
            juju.deploy(str(charm.resolve()), app="chopsticks", num_units=3)

        juju.config(
            "chopsticks",
            values={
                "s3-endpoint": microceph_s3["endpoint"],
                "s3-access-key": microceph_s3["access_key"],
                "s3-secret-key": microceph_s3["secret_key"],
                "s3-bucket": microceph_s3["bucket"],
                "s3-region": microceph_s3["region"],
                "scenario-file": TEST_SCENARIO,
                "locust-loglevel": "DEBUG",
            },
        )
        juju.wait(jubilant.all_active, timeout=300)

        leader = _get_leader_unit(juju)
        status_result = juju.run(leader, "test-status")
        if status_result.results["test-state"] == "running":
            juju.run(leader, "stop-test")


class TestActionRestrictions:
    """TC8: Action Restrictions."""

    def test_action_restrictions(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Verify actions are restricted to appropriate units."""
        self._ensure_deployed_and_configured(charm, juju, microceph_s3)

        status = juju.status()
        non_leader_unit = None
        for unit_name, unit in status.apps["chopsticks"].units.items():
            if "Worker" in unit.workload_status.message:
                non_leader_unit = unit_name
                break

        assert non_leader_unit is not None, "No non-leader units available for testing"

        logger.info("Testing start-test on non-leader %s (should fail)...", non_leader_unit)
        with pytest.raises(jubilant.TaskError) as exc_info:
            juju.run(non_leader_unit, "start-test", params={"users": MIN_USERS})
        assert "leader" in str(exc_info.value).lower()

        logger.info("Testing stop-test on non-leader %s (should fail)...", non_leader_unit)
        with pytest.raises(jubilant.TaskError) as exc_info:
            juju.run(non_leader_unit, "stop-test")
        assert "leader" in str(exc_info.value).lower()

        logger.info("Testing test-status on non-leader %s (should work)...", non_leader_unit)
        result = juju.run(non_leader_unit, "test-status")
        assert result.results["is-leader"] == "False"

    def _ensure_deployed_and_configured(
        self,
        charm: pathlib.Path,
        juju: jubilant.Juju,
        microceph_s3: dict[str, str],
    ) -> None:
        """Ensure chopsticks is deployed and configured."""
        if "chopsticks" not in juju.status().apps:
            juju.deploy(str(charm.resolve()), app="chopsticks", num_units=3)

        juju.config(
            "chopsticks",
            values={
                "s3-endpoint": microceph_s3["endpoint"],
                "s3-access-key": microceph_s3["access_key"],
                "s3-secret-key": microceph_s3["secret_key"],
                "s3-bucket": microceph_s3["bucket"],
                "s3-region": microceph_s3["region"],
                "scenario-file": TEST_SCENARIO,
                "locust-loglevel": "DEBUG",
            },
        )
        juju.wait(jubilant.all_active, timeout=300)
