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


from typing import Optional, Dict, Any
from .base import BaseS3Driver


class DummyDriver(BaseS3Driver):
    """Dummy S3 driver for testing that simulates failures"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.fail_mode = config.get("driver_config", {}).get("fail_mode", "all")

    def upload(
        self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Always fails upload operations"""
        return False

    def download(self, key: str) -> Optional[bytes]:
        """Always fails download operations"""
        return None

    def delete(self, key: str) -> bool:
        """Always fails delete operations"""
        return False

    def list_objects(self, prefix: Optional[str] = None, max_keys: int = 1000) -> list:
        """Returns empty list"""
        return []

    def head_object(self, key: str) -> Optional[Dict[str, Any]]:
        """Always fails head_object operations"""
        return None
