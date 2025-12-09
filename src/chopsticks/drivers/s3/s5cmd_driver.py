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
import subprocess
import tempfile
from typing import Optional, Dict, Any
from .base import BaseS3Driver


class S5cmdDriver(BaseS3Driver):
    """S3 driver using s5cmd CLI tool"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.s5cmd_path = config.get("driver_config", {}).get("s5cmd_path", "s5cmd")
        self._setup_credentials()

    def _setup_credentials(self):
        """Setup environment variables for s5cmd authentication"""
        os.environ["S3_ENDPOINT_URL"] = self.endpoint
        os.environ["AWS_ACCESS_KEY_ID"] = self.access_key
        os.environ["AWS_SECRET_ACCESS_KEY"] = self.secret_key
        os.environ["AWS_REGION"] = self.region

    def _run_command(
        self, args: list, input_data: Optional[bytes] = None, timeout: int = 10
    ) -> tuple[bool, str, str]:
        """
        Run s5cmd command

        Args:
            args: Command arguments
            input_data: Optional input data for stdin
            timeout: Command timeout in seconds (default: 10)

        Returns:
            Tuple of (success, stdout, stderr)
        """
        cmd = [self.s5cmd_path] + args
        try:
            result = subprocess.run(
                cmd, input=input_data, capture_output=True, timeout=timeout
            )
            success = result.returncode == 0
            stdout = result.stdout.decode() if result.stdout else ""
            stderr = result.stderr.decode() if result.stderr else ""

            # Check for errors in stderr even if return code is 0
            if not success or "ERROR" in stderr or "error" in stderr:
                return False, stdout, stderr if stderr else "Command failed"

            return success, stdout, stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out after {} seconds".format(timeout)
        except Exception as e:
            return False, "", str(e)

    def upload(
        self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Upload object using s5cmd"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data)
            tmp.flush()
            tmp_path = tmp.name

        try:
            s3_uri = f"s3://{self.bucket}/{key}"
            success, stdout, stderr = self._run_command(["cp", tmp_path, s3_uri])
            return success
        finally:
            os.unlink(tmp_path)

    def download(self, key: str) -> Optional[bytes]:
        """Download object using s5cmd"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            s3_uri = f"s3://{self.bucket}/{key}"
            success, stdout, stderr = self._run_command(["cp", s3_uri, tmp_path])

            if success:
                with open(tmp_path, "rb") as f:
                    return f.read()
            return None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def delete(self, key: str) -> bool:
        """Delete object using s5cmd"""
        s3_uri = f"s3://{self.bucket}/{key}"
        success, stdout, stderr = self._run_command(["rm", s3_uri])
        return success

    def list_objects(self, prefix: Optional[str] = None, max_keys: int = 1000) -> list:
        """List objects using s5cmd"""
        s3_uri = f"s3://{self.bucket}/"
        if prefix:
            s3_uri += prefix

        success, stdout, stderr = self._run_command(["ls", s3_uri])

        if not success:
            return []

        keys = []
        for line in stdout.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 4:
                    key = " ".join(parts[3:])
                    keys.append(key)
                    if len(keys) >= max_keys:
                        break

        return keys

    def head_object(self, key: str) -> Optional[Dict[str, Any]]:
        """Get object metadata using s5cmd"""
        s3_uri = f"s3://{self.bucket}/{key}"
        success, stdout, stderr = self._run_command(["ls", s3_uri])

        if not success:
            return None

        for line in stdout.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 4:
                    return {
                        "size": int(parts[2]) if parts[2].isdigit() else 0,
                        "last_modified": f"{parts[0]} {parts[1]}",
                        "key": key,
                    }

        return None
