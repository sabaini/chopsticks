#!/usr/bin/env python3
"""Chopsticks Charm - Distributed Ceph stress testing with Locust."""

import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import ops
import yaml

logger = logging.getLogger(__name__)

REPO_DIR = Path("/opt/chopsticks/src")
VENV_DIR = Path("/opt/chopsticks/venv")
CONFIG_DIR = Path("/etc/chopsticks")
DATA_DIR = Path("/var/lib/chopsticks")
S3_CONFIG_PATH = CONFIG_DIR / "s3_config.yaml"
SYSTEMD_DIR = Path("/etc/systemd/system")

LEADER_SERVICE = "chopsticks-leader"
LEADER_WEBUI_SERVICE = "chopsticks-leader-webui"
WORKER_SERVICE = "chopsticks-worker"


class ChopsticksCharm(ops.CharmBase):
    """Charm for distributed Ceph stress testing using Locust."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.remove, self._on_remove)
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(self.on.leader_elected, self._on_leader_elected)

        self.framework.observe(self.on.cluster_relation_joined, self._on_cluster_changed)
        self.framework.observe(self.on.cluster_relation_changed, self._on_cluster_changed)
        self.framework.observe(self.on.cluster_relation_departed, self._on_cluster_changed)

        self.framework.observe(self.on.start_test_action, self._on_start_test_action)
        self.framework.observe(self.on.stop_test_action, self._on_stop_test_action)
        self.framework.observe(self.on.test_status_action, self._on_test_status_action)
        self.framework.observe(self.on.fetch_metrics_action, self._on_fetch_metrics_action)

    @property
    def _peer_relation(self) -> ops.Relation | None:
        return self.model.get_relation("cluster")

    def _get_peer_data(self, key: str, default: str = "") -> str:
        """Get data from peer relation app databag."""
        rel = self._peer_relation
        if not rel:
            logger.debug(
                "_get_peer_data(%s): no peer relation, returning default=%s", key, default
            )
            return default
        value = rel.data[self.app].get(key, default)
        logger.debug("_get_peer_data(%s) = %s", key, value)
        return value

    def _set_peer_data(self, key: str, value: str) -> None:
        """Set data in peer relation app databag (leader only)."""
        if not self.unit.is_leader():
            logger.debug("_set_peer_data(%s): skipping, not leader", key)
            return
        rel = self._peer_relation
        if rel:
            logger.debug("_set_peer_data(%s, %s)", key, value)
            rel.data[self.app][key] = value
        else:
            logger.debug("_set_peer_data(%s): no peer relation available", key)

    # Lifecycle event handlers

    def _on_install(self, event: ops.InstallEvent) -> None:
        """Install dependencies and clone repository."""
        logger.debug("_on_install: starting installation")
        self.unit.status = ops.MaintenanceStatus("Installing dependencies...")

        try:
            logger.debug("_on_install: installing system packages")
            self._install_system_packages()
            logger.debug("_on_install: cloning repo")
            self._clone_repo()
            logger.debug("_on_install: setting up venv")
            self._setup_venv()
            logger.debug("_on_install: installing s5cmd")
            self._install_s5cmd()
            logger.debug("_on_install: creating directories")
            self._create_directories()
            logger.debug("_on_install: installing systemd units")
            self._install_systemd_units()
            logger.debug("_on_install: completed successfully")
            self.unit.status = ops.ActiveStatus("Installed")
        except subprocess.CalledProcessError as e:
            logger.error("Installation failed: %s", e)
            self.unit.status = ops.BlockedStatus(f"Install failed: {e}")

    def _on_config_changed(self, event: ops.ConfigChangedEvent) -> None:
        """Handle configuration changes."""
        logger.debug("_on_config_changed: starting, is_leader=%s", self.unit.is_leader())
        self.unit.status = ops.MaintenanceStatus("Applying configuration...")

        try:
            logger.debug("_on_config_changed: updating repo")
            self._update_repo()
            logger.debug("_on_config_changed: rendering S3 config")
            self._render_s3_config()
            logger.debug("_on_config_changed: updating systemd units")
            self._update_systemd_units()

            if self.unit.is_leader():
                logger.debug("_on_config_changed: publishing leader address")
                self._publish_leader_address()

            if not self._is_config_valid():
                logger.debug("_on_config_changed: config not valid, setting blocked status")
                self.unit.status = ops.BlockedStatus("Missing S3 configuration")
                return

            if not self.unit.is_leader() and self.config.get("autostart-workers"):
                logger.debug("_on_config_changed: attempting to start worker (non-leader)")
                self._maybe_start_worker()

            logger.debug("_on_config_changed: setting ready status")
            self._set_ready_status()
        except Exception as e:
            logger.exception("Config change failed")
            self.unit.status = ops.BlockedStatus(f"Config error: {e}")

    def _on_start(self, event: ops.StartEvent) -> None:
        """Handle start event."""
        logger.debug("_on_start: setting ready status")
        self._set_ready_status()

    def _on_update_status(self, event: ops.UpdateStatusEvent) -> None:
        """Periodically refresh status (e.g., if services crash)."""
        logger.debug("_on_update_status: refreshing status")

        if self.unit.is_leader():
            test_state = self._get_peer_data("test_state", "idle")
            if test_state == "running":
                leader_running = self._is_service_running(LEADER_SERVICE)
                if not leader_running:
                    logger.warning(
                        "_on_update_status: test_state is 'running' but leader service "
                        "is not running; marking test as failed"
                    )
                    self._set_peer_data("test_state", "failed")

        self._set_ready_status()

    def _on_stop(self, event: ops.StopEvent) -> None:
        """Handle stop event - cleanup services."""
        logger.debug("_on_stop: stopping all services")
        self._stop_all_services()

    def _on_remove(self, event: ops.RemoveEvent) -> None:
        """Handle remove event - cleanup all artifacts."""
        logger.debug("_on_remove: starting cleanup")
        self._stop_all_services()

        if REPO_DIR.exists():
            shutil.rmtree(REPO_DIR, ignore_errors=True)
            logger.info("Removed repository: %s", REPO_DIR)

        if VENV_DIR.exists():
            shutil.rmtree(VENV_DIR, ignore_errors=True)
            logger.info("Removed venv: %s", VENV_DIR)

        if CONFIG_DIR.exists():
            shutil.rmtree(CONFIG_DIR, ignore_errors=True)
            logger.info("Removed config: %s", CONFIG_DIR)

        if DATA_DIR.exists():
            shutil.rmtree(DATA_DIR, ignore_errors=True)
            logger.info("Removed data: %s", DATA_DIR)

        for service in [LEADER_SERVICE, LEADER_WEBUI_SERVICE, WORKER_SERVICE]:
            service_path = SYSTEMD_DIR / f"{service}.service"
            if service_path.exists():
                service_path.unlink()
        subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
        logger.info("Removed systemd units")

    def _on_leader_elected(self, event: ops.LeaderElectedEvent) -> None:
        """Handle leader election.

        If a test was running when the previous leader failed, mark it as
        failed. Workers connected to the old leader are now orphaned and their
        results are suspect, so we treat any in-progress test as failed.
        """
        logger.info("_on_leader_elected: this unit is now the leader (Locust coordinator)")
        logger.debug("_on_leader_elected: stopping all services")
        self._stop_all_services()
        logger.debug("_on_leader_elected: publishing leader address")
        self._publish_leader_address()

        previous_state = self._get_peer_data("test_state", "idle")
        logger.debug("_on_leader_elected: previous test_state=%s", previous_state)
        if previous_state == "running":
            self._set_peer_data("test_state", "failed")
            logger.warning(
                "Previous leader failed during test run; marking test as failed "
                "(workers connected to old leader, results suspect)"
            )
        else:
            self._set_peer_data("test_state", "idle")

        logger.debug("_on_leader_elected: setting ready status")
        self._set_ready_status()

    def _on_cluster_changed(self, event: ops.RelationEvent) -> None:
        """Handle peer relation changes.

        When leader address changes (leader failover), workers must stop to
        avoid running with a stale leader address. Any running test is already
        marked as failed by _on_leader_elected on the new leader.
        """
        logger.debug(
            "_on_cluster_changed: event=%s, is_leader=%s",
            type(event).__name__,
            self.unit.is_leader(),
        )
        if self.unit.is_leader():
            logger.debug("_on_cluster_changed: publishing leader address")
            self._publish_leader_address()
        else:
            new_leader = self._get_peer_data("leader_address", "")
            if self._is_service_running(WORKER_SERVICE):
                self._stop_service(WORKER_SERVICE)
                logger.info(
                    "_on_cluster_changed: stopped worker due to leader change (new leader: %s)",
                    new_leader or "unknown",
                )
            if self.config.get("autostart-workers") and new_leader:
                logger.debug("_on_cluster_changed: attempting to start worker (non-leader)")
                self._maybe_start_worker()

        self._set_ready_status()

    def _on_start_test_action(self, event: ops.ActionEvent) -> None:
        """Start a distributed Locust test."""
        logger.debug("_on_start_test_action: starting, is_leader=%s", self.unit.is_leader())
        if not self.unit.is_leader():
            logger.debug("_on_start_test_action: failing - not leader")
            event.fail("start-test must be run on the leader unit")
            return

        if not self._is_config_valid():
            logger.debug("_on_start_test_action: failing - config not valid")
            event.fail("S3 configuration is incomplete")
            return

        current_state = self._get_peer_data("test_state", "idle")
        logger.debug("_on_start_test_action: current test_state=%s", current_state)
        if current_state == "running":
            logger.debug("_on_start_test_action: failing - test already running")
            event.fail("A test is already running")
            return

        test_run_id = str(uuid.uuid4())
        users = event.params.get("users") or self.config.get("locust-users")
        spawn_rate = event.params.get("spawn-rate") or self.config.get("locust-spawn-rate")
        duration = event.params.get("duration") or self.config.get("locust-duration")
        scenario = event.params.get("scenario-file") or self.config.get("scenario-file")
        headless = event.params.get("headless", True)

        logger.debug(
            "_on_start_test_action: params - users=%s, spawn_rate=%s, duration=%s, "
            "scenario=%s, headless=%s, test_run_id=%s",
            users,
            spawn_rate,
            duration,
            scenario,
            headless,
            test_run_id,
        )

        try:
            users = int(users)
            spawn_rate = float(spawn_rate)
        except (TypeError, ValueError):
            logger.debug("_on_start_test_action: failing - invalid numeric params")
            event.fail("Invalid users or spawn-rate; must be numeric")
            return

        scenario_path = REPO_DIR / scenario
        if not scenario_path.is_file():
            logger.debug("_on_start_test_action: failing - scenario not found: %s", scenario_path)
            event.fail(f"Scenario file not found: {scenario_path}")
            return

        metrics_dir = DATA_DIR / test_run_id
        metrics_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("_on_start_test_action: created metrics dir: %s", metrics_dir)

        try:
            logger.debug("_on_start_test_action: stopping existing leader services")
            self._stop_service(LEADER_SERVICE)
            self._stop_service(LEADER_WEBUI_SERVICE)

            if headless:
                logger.debug("_on_start_test_action: rendering and starting headless leader")
                self._render_leader_service(
                    test_run_id=test_run_id,
                    scenario_file=scenario,
                    users=users,
                    spawn_rate=spawn_rate,
                    duration=duration,
                )
                self._start_service(LEADER_SERVICE)
            else:
                logger.debug("_on_start_test_action: rendering and starting webui leader")
                self._render_leader_webui_service(scenario_file=scenario)
                self._start_service(LEADER_WEBUI_SERVICE)

            logger.debug("_on_start_test_action: updating peer data for test run")
            self._set_peer_data("test_state", "running")
            self._set_peer_data("test_run_id", test_run_id)
            self._set_peer_data("scenario_file", scenario)

            leader_ip = self._get_private_ip()
            web_port = self.config.get("locust-web-port")

            result = {
                "test-run-id": test_run_id,
                "status": "started",
                "users": users,
                "spawn-rate": spawn_rate,
                "duration": duration,
                "scenario": scenario,
                "headless": headless,
                "metrics-dir": str(metrics_dir),
            }

            if not headless:
                result["web-ui"] = f"http://{leader_ip}:{web_port}"

            logger.info("_on_start_test_action: test started successfully, id=%s", test_run_id)
            event.set_results(result)

        except subprocess.CalledProcessError as e:
            logger.error("_on_start_test_action: failed to start test: %s", e)
            self._set_peer_data("test_state", "failed")
            event.fail(f"Failed to start test: {e}")

    def _on_stop_test_action(self, event: ops.ActionEvent) -> None:
        """Stop the current test."""
        logger.debug("_on_stop_test_action: starting, is_leader=%s", self.unit.is_leader())
        if not self.unit.is_leader():
            logger.debug("_on_stop_test_action: failing - not leader")
            event.fail("stop-test must be run on the leader unit")
            return

        test_run_id = self._get_peer_data("test_run_id", "unknown")
        logger.debug("_on_stop_test_action: stopping test_run_id=%s", test_run_id)

        try:
            logger.debug("_on_stop_test_action: stopping leader services")
            self._stop_service(LEADER_SERVICE)
            self._stop_service(LEADER_WEBUI_SERVICE)

            self._set_peer_data("test_state", "stopped")
            logger.info("_on_stop_test_action: test stopped successfully")

            event.set_results(
                {
                    "status": "stopped",
                    "test-run-id": test_run_id,
                }
            )
        except subprocess.CalledProcessError as e:
            logger.error("_on_stop_test_action: failed to stop test: %s", e)
            event.fail(f"Failed to stop test: {e}")

    def _on_test_status_action(self, event: ops.ActionEvent) -> None:
        """Report test status."""
        logger.debug("_on_test_status_action: gathering status info")
        test_state = self._get_peer_data("test_state", "idle")
        test_run_id = self._get_peer_data("test_run_id", "")
        leader_address = self._get_peer_data("leader_address", "")

        leader_running = self._is_service_running(LEADER_SERVICE)
        leader_webui_running = self._is_service_running(LEADER_WEBUI_SERVICE)
        worker_running = self._is_service_running(WORKER_SERVICE)

        worker_count = self._count_peer_units()

        logger.debug(
            "_on_test_status_action: test_state=%s, leader_running=%s, "
            "leader_webui_running=%s, worker_running=%s, worker_count=%d",
            test_state,
            leader_running,
            leader_webui_running,
            worker_running,
            worker_count,
        )

        result = {
            "test-state": test_state,
            "test-run-id": test_run_id,
            "leader-address": leader_address,
            "is-leader": self.unit.is_leader(),
            "leader-running": leader_running or leader_webui_running,
            "worker-running": worker_running,
            "worker-count": worker_count,
        }

        event.set_results(result)

    def _on_fetch_metrics_action(self, event: ops.ActionEvent) -> None:
        """Fetch metrics from the last test run."""
        import tarfile

        logger.debug("_on_fetch_metrics_action: starting, is_leader=%s", self.unit.is_leader())
        if not self.unit.is_leader():
            logger.debug("_on_fetch_metrics_action: failing - not leader")
            event.fail("fetch-metrics must be run on the leader unit")
            return

        test_run_id = self._get_peer_data("test_run_id", "")
        if not test_run_id:
            logger.debug("_on_fetch_metrics_action: failing - no test run found")
            event.fail("No test run found")
            return

        metrics_dir = DATA_DIR / test_run_id
        logger.debug("_on_fetch_metrics_action: metrics_dir=%s", metrics_dir)
        if not metrics_dir.exists():
            logger.debug("_on_fetch_metrics_action: failing - metrics dir not found")
            event.fail(f"Metrics directory not found: {metrics_dir}")
            return

        test_state = self._get_peer_data("test_state", "idle")
        output_format = event.params.get("format", "summary")

        files = list(metrics_dir.glob("*"))
        file_list = [str(f) for f in files]
        logger.debug("_on_fetch_metrics_action: found %d files: %s", len(files), file_list)

        archive_name = f"testrun-{test_run_id}.tar.gz"
        archive_path = Path("/tmp") / archive_name
        with tarfile.open(archive_path, "w:gz") as tar:
            for f in files:
                tar.add(f, arcname=f.name)
        logger.debug("_on_fetch_metrics_action: created archive %s", archive_path)

        scp_command = f"juju scp {self.unit.name}:{archive_path} ."

        result = {
            "test-run-id": test_run_id,
            "metrics-dir": str(metrics_dir),
            "files": ", ".join(file_list),
            "test-state": test_state,
            "archive": str(archive_path),
            "scp-command": scp_command,
        }

        if test_state == "running":
            result["warning"] = "Test is still running; metrics may be incomplete"

        if output_format == "summary":
            stats_file = metrics_dir / "metrics_stats.csv"
            if stats_file.exists():
                logger.debug(
                    "_on_fetch_metrics_action: including stats preview from %s", stats_file
                )
                result["stats-preview"] = stats_file.read_text()[:2000]

        event.set_results(result)

    def _install_system_packages(self) -> None:
        """Install required system packages."""
        packages = ["git", "python3", "python3-venv", "python3-pip", "curl"]
        env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
        subprocess.run(
            ["apt-get", "update"],
            check=True,
            capture_output=True,
            env=env,
        )
        subprocess.run(
            ["apt-get", "install", "-y"] + packages,
            check=True,
            capture_output=True,
            env=env,
        )

    def _clone_repo(self) -> None:
        """Clone the Chopsticks repository."""
        repo_url = self.config.get("repo-url")
        branch = self.config.get("repo-branch")

        if REPO_DIR.exists():
            shutil.rmtree(REPO_DIR)

        REPO_DIR.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["git", "clone", "-b", branch, repo_url, str(REPO_DIR)],
            check=True,
            capture_output=True,
        )
        logger.info("Cloned %s branch %s to %s", repo_url, branch, REPO_DIR)

    def _update_repo(self) -> None:
        """Update the repository if config changed."""
        if not REPO_DIR.exists():
            self._clone_repo()
            return

        branch = self.config.get("repo-branch")
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "fetch", "origin"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "checkout", branch],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(REPO_DIR), "pull", "origin", branch],
            check=True,
            capture_output=True,
        )

    def _setup_venv(self) -> None:
        """Create virtual environment and install dependencies."""
        if VENV_DIR.exists():
            shutil.rmtree(VENV_DIR)

        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["python3", "-m", "venv", str(VENV_DIR)],
            check=True,
            capture_output=True,
        )

        pip = VENV_DIR / "bin" / "pip"
        subprocess.run(
            [str(pip), "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [str(pip), "install", "-e", str(REPO_DIR)],
            check=True,
            capture_output=True,
        )
        logger.info("Set up venv at %s", VENV_DIR)

    def _install_s5cmd(self) -> None:
        """Install s5cmd binary."""
        install_script = REPO_DIR / "scripts" / "install_s5cmd.sh"
        if install_script.exists():
            subprocess.run(
                ["bash", str(install_script)],
                check=True,
                capture_output=True,
                cwd=str(REPO_DIR),
                env={**os.environ, "INSTALL_DIR": "/usr/local/bin"},
            )
            logger.info("Installed s5cmd")

    def _create_directories(self) -> None:
        """Create required directories."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _render_s3_config(self) -> None:
        """Render S3 configuration file from charm config."""
        config = {
            "endpoint": self.config.get("s3-endpoint"),
            "access_key": self.config.get("s3-access-key"),
            "secret_key": self.config.get("s3-secret-key"),
            "bucket": self.config.get("s3-bucket"),
            "region": self.config.get("s3-region"),
            "driver": self.config.get("s3-driver"),
        }

        extra_yaml = self.config.get("s3-driver-config-yaml")
        if extra_yaml:
            try:
                config["driver_config"] = yaml.safe_load(extra_yaml)
            except yaml.YAMLError as e:
                logger.warning("Invalid driver config YAML: %s", e)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(CONFIG_DIR, 0o700)

        with open(S3_CONFIG_PATH, "w") as f:
            yaml.safe_dump(config, f)
        os.chmod(S3_CONFIG_PATH, 0o600)

        logger.info("Rendered S3 config to %s", S3_CONFIG_PATH)

    def _is_config_valid(self) -> bool:
        """Check if required S3 configuration is present."""
        required = ["s3-endpoint", "s3-access-key", "s3-secret-key"]
        return all(self.config.get(key) for key in required)

    def _publish_leader_address(self) -> None:
        """Publish leader address to peer relation."""
        if not self.unit.is_leader():
            return

        leader_ip = self._get_private_ip()
        if leader_ip:
            self._set_peer_data("leader_address", leader_ip)
            self._set_peer_data("leader_unit", self.unit.name)
            logger.info("Published leader address: %s", leader_ip)

    def _get_private_ip(self) -> str:
        """Get this unit's private IP address."""
        try:
            binding = self.model.get_binding("cluster")
            if binding and binding.network.ingress_address:
                return str(binding.network.ingress_address)
        except Exception:
            pass

        addr = self.model.get_binding("juju-info")
        if addr and addr.network.ingress_address:
            return str(addr.network.ingress_address)

        return ""

    def _maybe_start_worker(self) -> None:
        """Start worker service if leader address is known."""
        logger.debug("_maybe_start_worker: checking if we should start worker")
        if self.unit.is_leader():
            logger.debug("_maybe_start_worker: skipping - this is the leader")
            return

        if self._is_service_running(WORKER_SERVICE):
            logger.debug("_maybe_start_worker: worker already running, skipping")
            return

        if not self._is_config_valid():
            logger.debug("_maybe_start_worker: config not valid, not starting worker")
            return

        leader_address = self._get_peer_data("leader_address", "")
        if not leader_address:
            logger.debug("_maybe_start_worker: leader address not yet known")
            return

        logger.debug("_maybe_start_worker: rendering worker service for leader=%s", leader_address)
        self._render_worker_service(leader_address)
        self._start_service(WORKER_SERVICE)
        logger.info(
            "_maybe_start_worker: started worker connecting to leader at %s", leader_address
        )

    def _count_peer_units(self) -> int:
        """Count the number of peer units (excluding self)."""
        rel = self._peer_relation
        if not rel:
            logger.debug("_count_peer_units: no peer relation, returning 0")
            return 0
        count = len(rel.units)
        logger.debug("_count_peer_units: %d peer units", count)
        return count

    def _set_ready_status(self) -> None:
        """Set appropriate ready status based on role."""
        logger.debug("_set_ready_status: is_leader=%s", self.unit.is_leader())
        if not self._is_config_valid():
            logger.debug("_set_ready_status: config not valid, setting blocked")
            self.unit.status = ops.BlockedStatus("Missing S3 configuration")
            return

        test_state = self._get_peer_data("test_state", "idle")

        if self.unit.is_leader():
            worker_count = self._count_peer_units()
            status_msg = f"Leader ready ({worker_count} workers, test: {test_state})"
            logger.debug("_set_ready_status: leader status=%s", status_msg)
            self.unit.status = ops.ActiveStatus(status_msg)
        else:
            leader_address = self._get_peer_data("leader_address", "")
            if leader_address:
                worker_running = self._is_service_running(WORKER_SERVICE)
                status = "connected" if worker_running else "ready"
                status_msg = f"Worker {status} -> {leader_address}"
                logger.debug("_set_ready_status: worker status=%s", status_msg)
                self.unit.status = ops.ActiveStatus(status_msg)
            else:
                logger.debug("_set_ready_status: waiting for leader address")
                self.unit.status = ops.WaitingStatus("Waiting for leader address")

    def _leader_service_content(
        self,
        test_run_id: str,
        scenario_file: str,
        users: int,
        spawn_rate: float,
        duration: str,
    ) -> str:
        """Generate systemd unit content for the headless leader service."""
        leader_port = self.config.get("locust-master-port")
        loglevel = self.config.get("locust-loglevel") or "INFO"
        scenario_path = REPO_DIR / scenario_file

        return f"""[Unit]
Description=Chopsticks Locust Leader
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={REPO_DIR}
Environment=S3_CONFIG_PATH={S3_CONFIG_PATH}
Environment=PATH={VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={VENV_DIR}/bin/python -m locust \\
    -f {scenario_path} \\
    --master \\
    --master-bind-port={leader_port} \\
    --loglevel={loglevel} \\
    --headless \\
    --users={users} \\
    --spawn-rate={spawn_rate} \\
    --run-time={duration} \\
    --csv={DATA_DIR}/{test_run_id}/metrics \\
    --html={DATA_DIR}/{test_run_id}/report.html
Restart=no
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    def _leader_webui_service_content(self, scenario_file: str) -> str:
        """Generate systemd unit content for leader with web UI."""
        leader_port = self.config.get("locust-master-port")
        web_port = self.config.get("locust-web-port")
        loglevel = self.config.get("locust-loglevel") or "INFO"
        scenario_path = REPO_DIR / scenario_file

        return f"""[Unit]
Description=Chopsticks Locust Leader with Web UI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={REPO_DIR}
Environment=S3_CONFIG_PATH={S3_CONFIG_PATH}
Environment=PATH={VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={VENV_DIR}/bin/python -m locust \\
    -f {scenario_path} \\
    --master \\
    --master-bind-port={leader_port} \\
    --loglevel={loglevel} \\
    --web-port={web_port}
Restart=no
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    def _worker_service_content(self, leader_host: str) -> str:
        """Generate systemd unit content for the worker service."""
        leader_port = self.config.get("locust-master-port")
        loglevel = self.config.get("locust-loglevel") or "INFO"
        scenario_file = self._get_peer_data("scenario_file") or self.config.get("scenario-file")
        scenario_path = REPO_DIR / scenario_file

        return f"""[Unit]
Description=Chopsticks Locust Worker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={REPO_DIR}
Environment=S3_CONFIG_PATH={S3_CONFIG_PATH}
Environment=PATH={VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={VENV_DIR}/bin/python -m locust \\
    -f {scenario_path} \\
    --worker \\
    --master-host={leader_host} \\
    --master-port={leader_port} \\
    --loglevel={loglevel}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    def _install_systemd_units(self) -> None:
        """Reload systemd daemon (units are rendered dynamically)."""
        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)

    def _update_systemd_units(self) -> None:
        """Update systemd units with current configuration."""
        if not self.unit.is_leader():
            leader_address = self._get_peer_data("leader_address", "")
            if leader_address:
                self._render_worker_service(leader_address)

    def _render_leader_service(
        self,
        test_run_id: str,
        scenario_file: str,
        users: int,
        spawn_rate: float,
        duration: str,
    ) -> None:
        """Render and install the leader systemd service file."""
        content = self._leader_service_content(
            test_run_id=test_run_id,
            scenario_file=scenario_file,
            users=users,
            spawn_rate=spawn_rate,
            duration=duration,
        )
        service_path = SYSTEMD_DIR / f"{LEADER_SERVICE}.service"
        service_path.write_text(content)
        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)

    def _render_leader_webui_service(self, scenario_file: str) -> None:
        """Render and install the leader with web UI systemd service file."""
        content = self._leader_webui_service_content(scenario_file=scenario_file)
        service_path = SYSTEMD_DIR / f"{LEADER_WEBUI_SERVICE}.service"
        service_path.write_text(content)
        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)

    def _render_worker_service(self, leader_host: str) -> None:
        """Render and install the worker systemd service file."""
        content = self._worker_service_content(leader_host=leader_host)
        service_path = SYSTEMD_DIR / f"{WORKER_SERVICE}.service"
        service_path.write_text(content)
        subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)

    def _start_service(self, service: str) -> None:
        """Start a systemd service."""
        logger.debug("_start_service: starting %s", service)
        subprocess.run(
            ["systemctl", "start", f"{service}.service"],
            check=True,
            capture_output=True,
        )
        logger.info("_start_service: started %s", service)

    def _stop_service(self, service: str) -> None:
        """Stop a systemd service (ignore if not running)."""
        logger.debug("_stop_service: stopping %s", service)
        subprocess.run(
            ["systemctl", "stop", f"{service}.service"],
            capture_output=True,
        )
        logger.debug("_stop_service: stopped %s", service)

    def _is_service_running(self, service: str) -> bool:
        """Check if a systemd service is running."""
        result = subprocess.run(
            ["systemctl", "is-active", f"{service}.service"],
            capture_output=True,
            text=True,
        )
        is_running = result.returncode == 0
        logger.debug("_is_service_running(%s) = %s", service, is_running)
        return is_running

    def _stop_all_services(self) -> None:
        """Stop all Chopsticks services."""
        logger.debug("_stop_all_services: stopping all services")
        for service in [LEADER_SERVICE, LEADER_WEBUI_SERVICE, WORKER_SERVICE]:
            self._stop_service(service)


if __name__ == "__main__":
    ops.main(ChopsticksCharm)
