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


from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseS3Driver(ABC):
    """Base interface for S3 drivers"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize driver with configuration

        Args:
            config: Dictionary containing driver configuration
                   - endpoint: S3 endpoint URL
                   - access_key: Access key ID
                   - secret_key: Secret access key
                   - bucket: Bucket name
                   - region: AWS region (optional)
        """
        self.config = config
        self.endpoint = config.get("endpoint")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.bucket = config.get("bucket")
        self.region = config.get("region", "us-east-1")

    @abstractmethod
    def upload(
        self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload object to S3

        Args:
            key: Object key
            data: Object data
            metadata: Optional metadata dictionary

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def download(self, key: str) -> Optional[bytes]:
        """
        Download object from S3

        Args:
            key: Object key

        Returns:
            Object data if successful, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete object from S3

        Args:
            key: Object key

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def list_objects(self, prefix: Optional[str] = None, max_keys: int = 1000) -> list:
        """
        List objects in bucket

        Args:
            prefix: Optional prefix to filter objects
            max_keys: Maximum number of keys to return

        Returns:
            List of object keys
        """
        pass

    @abstractmethod
    def head_object(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get object metadata

        Args:
            key: Object key

        Returns:
            Metadata dictionary if successful, None otherwise
        """
        pass
