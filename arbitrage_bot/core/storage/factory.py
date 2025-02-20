"""Storage hub factory for creating and managing storage instances."""

import logging
import json
import os
import eventlet
from typing import Dict, Any, Optional
from pathlib import Path
from ..memory.bank import MemoryBank

logger = logging.getLogger(__name__)

class StorageHub:
    """Manages storage operations and caching."""

    def __init__(self, base_path: str, memory_bank: Optional[MemoryBank] = None):
        """Initialize storage hub."""
        self.base_path = Path(base_path)
        self.memory_bank = memory_bank
        self.cache = {}
        self.initialized = False
        logger.debug("Storage hub initialized")

    def initialize(self) -> bool:
        """Initialize storage system."""
        try:
            # Create base directory if it doesn't exist
            self.base_path.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            (self.base_path / 'trades').mkdir(exist_ok=True)
            (self.base_path / 'metrics').mkdir(exist_ok=True)
            (self.base_path / 'analytics').mkdir(exist_ok=True)

            # Load cache from memory bank if available
            if self.memory_bank:
                cache_data = self.memory_bank.retrieve('storage_cache', 'cache')
                if cache_data:
                    self.cache = cache_data

            self.initialized = True
            logger.info("Storage hub initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize storage hub: {e}")
            return False

    def store_data(self, category: str, key: str, data: Any) -> bool:
        """Store data in the appropriate category."""
        try:
            # Validate category
            if category not in ['trades', 'metrics', 'analytics']:
                raise ValueError(f"Invalid category: {category}")

            # Create file path
            file_path = self.base_path / category / f"{key}.json"

            # Store data
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

            # Update cache
            self.cache[f"{category}/{key}"] = {
                'path': str(file_path),
                'timestamp': eventlet.time.time()
            }

            # Save cache to memory bank if available
            if self.memory_bank:
                self.memory_bank.store('storage_cache', self.cache, 'cache')

            logger.debug(f"Stored data: {category}/{key}")
            return True

        except Exception as e:
            logger.error(f"Failed to store data {category}/{key}: {e}")
            return False

    def load_data(self, category: str, key: str) -> Optional[Any]:
        """Load data from storage."""
        try:
            # Validate category
            if category not in ['trades', 'metrics', 'analytics']:
                raise ValueError(f"Invalid category: {category}")

            # Check cache first
            cache_key = f"{category}/{key}"
            if cache_key in self.cache:
                file_path = Path(self.cache[cache_key]['path'])
                if file_path.exists():
                    with open(file_path) as f:
                        return json.load(f)

            # If not in cache, try loading from file
            file_path = self.base_path / category / f"{key}.json"
            if file_path.exists():
                with open(file_path) as f:
                    data = json.load(f)
                    
                # Update cache
                self.cache[cache_key] = {
                    'path': str(file_path),
                    'timestamp': eventlet.time.time()
                }
                
                # Save cache to memory bank if available
                if self.memory_bank:
                    self.memory_bank.store('storage_cache', self.cache, 'cache')
                    
                return data

            return None

        except Exception as e:
            logger.error(f"Failed to load data {category}/{key}: {e}")
            return None

    def delete_data(self, category: str, key: str) -> bool:
        """Delete data from storage."""
        try:
            # Validate category
            if category not in ['trades', 'metrics', 'analytics']:
                raise ValueError(f"Invalid category: {category}")

            # Delete file if it exists
            file_path = self.base_path / category / f"{key}.json"
            if file_path.exists():
                file_path.unlink()

            # Remove from cache
            cache_key = f"{category}/{key}"
            if cache_key in self.cache:
                del self.cache[cache_key]

                # Update memory bank if available
                if self.memory_bank:
                    self.memory_bank.store('storage_cache', self.cache, 'cache')

            logger.debug(f"Deleted data: {category}/{key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete data {category}/{key}: {e}")
            return False

    def cleanup_cache(self, max_age: int = 3600) -> bool:
        """Clean up old cache entries."""
        try:
            current_time = eventlet.time.time()
            to_delete = []

            # Find old entries
            for key, data in self.cache.items():
                if current_time - data['timestamp'] > max_age:
                    to_delete.append(key)

            # Remove old entries
            for key in to_delete:
                del self.cache[key]

            # Update memory bank if available
            if self.memory_bank:
                self.memory_bank.store('storage_cache', self.cache, 'cache')

            logger.debug(f"Cleaned up {len(to_delete)} cache entries")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get storage system status."""
        try:
            status = {
                'initialized': self.initialized,
                'cache_size': len(self.cache),
                'categories': {}
            }

            # Get stats for each category
            for category in ['trades', 'metrics', 'analytics']:
                category_path = self.base_path / category
                if category_path.exists():
                    status['categories'][category] = {
                        'file_count': len(list(category_path.glob('*.json'))),
                        'size_bytes': sum(f.stat().st_size for f in category_path.glob('*.json'))
                    }

            return status

        except Exception as e:
            logger.error(f"Failed to get storage status: {e}")
            return {
                'initialized': self.initialized,
                'error': str(e)
            }


def create_storage_hub(base_path: str, memory_bank: Optional[MemoryBank] = None) -> StorageHub:
    """Create and initialize storage hub."""
    try:
        storage = StorageHub(base_path, memory_bank)
        if not storage.initialize():
            raise RuntimeError("Failed to initialize storage hub")
        logger.debug("Created storage hub")
        return storage
    except Exception as e:
        logger.error(f"Failed to create storage hub: {e}")
        raise
