"""Factory for creating storage instances."""

import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class StorageFactory:
    """Factory for creating storage instances."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize storage factory."""
        self.config = config
        self.storage_instances = {}
        self.initialized = False

    def initialize(self) -> bool:
        """Initialize storage factory."""
        try:
            # Create storage directory if it doesn't exist
            storage_path = Path(self.config.get('storage_path', 'data/storage'))
            storage_path.mkdir(parents=True, exist_ok=True)

            # Initialize storage instances
            self.storage_instances = {
                'memory': {
                    'type': 'memory',
                    'path': str(storage_path),
                    'timestamp': time.time()
                }
            }

            self.initialized = True
            logger.debug("Storage factory initialized")
            return True

        except Exception as e:
            logger.error("Failed to initialize storage factory: " + str(e))
            return False

    def get_storage(self, name: str) -> Optional[Dict[str, Any]]:
        """Get storage instance by name."""
        try:
            storage = self.storage_instances.get(name)
            if storage:
                storage['timestamp'] = time.time()
            return storage

        except Exception as e:
            logger.error("Failed to get storage instance: " + str(e))
            return None

    def cleanup(self) -> None:
        """Clean up expired storage instances."""
        try:
            current_time = time.time()
            to_delete = []

            # Find expired instances
            for name, storage in self.storage_instances.items():
                if current_time - storage['timestamp'] > self.config.get('storage_ttl', 86400):
                    to_delete.append(name)

            # Delete expired instances
            for name in to_delete:
                del self.storage_instances[name]
                logger.debug("Cleaned up storage instance: " + str(name))

        except Exception as e:
            logger.error("Failed to cleanup storage: " + str(e))

    def get_metrics(self) -> Dict[str, Any]:
        """Get storage metrics."""
        return {
            'instances': len(self.storage_instances),
            'initialized': self.initialized
        }
