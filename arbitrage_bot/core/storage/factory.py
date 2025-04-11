"""Factory for creating storage instances."""

import logging
import time
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageFactory:
    """Factory for creating storage instances."""

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, config: Dict[str, Any] = None):
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super(StorageFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize storage factory."""
        if self._initialized:
            return

        self.config = config or {}
        self.storage_instances = {}
        self._storage_lock = asyncio.Lock()
        self._initialized = True
        self.initialized = False  # This tracks if initialize() has been called

    async def initialize(self, base_path: Optional[str] = None) -> bool:
        """Initialize storage factory."""
        if self.initialized:
            return True

        async with self._lock:
            if self.initialized:  # Double-check under lock
                return True

            try:
                # Create storage directory if it doesn't exist
                storage_path = (
                    Path(base_path)
                    if base_path
                    else Path(self.config.get("storage_path", "data/storage"))
                )
                storage_path.mkdir(parents=True, exist_ok=True)

                async with self._storage_lock:
                    # Initialize storage instances
                    self.storage_instances = {
                        "memory": {
                            "type": "memory",
                            "path": str(storage_path),
                            "timestamp": time.time(),
                        }
                    }

                self.initialized = True
                logger.debug(
                    "Storage factory initialized with path: %s", str(storage_path)
                )
                return True

            except Exception as e:
                logger.error("Failed to initialize storage factory: %s", str(e))
                return False

    async def get_storage(self, name: str) -> Optional[Dict[str, Any]]:
        """Get storage instance by name."""
        try:
            async with self._storage_lock:
                storage = self.storage_instances.get(name)
                if storage:
                    storage["timestamp"] = time.time()
                return storage.copy() if storage else None

        except Exception as e:
            logger.error("Failed to get storage instance: %s", str(e))
            return None

    async def cleanup(self) -> None:
        """Clean up expired storage instances."""
        try:
            current_time = time.time()
            to_delete = []

            async with self._storage_lock:
                # Find expired instances
                for name, storage in self.storage_instances.items():
                    if current_time - storage["timestamp"] > self.config.get(
                        "storage_ttl", 86400
                    ):
                        to_delete.append(name)

                # Delete expired instances
                for name in to_delete:
                    del self.storage_instances[name]
                    logger.debug("Cleaned up storage instance: %s", name)

        except Exception as e:
            logger.error("Failed to cleanup storage: %s", str(e))

    async def get_metrics(self) -> Dict[str, Any]:
        """Get storage metrics."""
        async with self._storage_lock:
            return {
                "instances": len(self.storage_instances),
                "initialized": self.initialized,
            }


class StorageHub:
    """Central hub for managing different storage instances."""

    def __init__(
        self,
        config: Dict[str, Any] = None,
        base_path: Optional[str] = None,
        memory_bank: Any = None,
    ):
        """Initialize storage hub."""
        self.config = config or {}
        if base_path:
            self.config["storage_path"] = base_path
        self.factory = StorageFactory(self.config)
        self.memory_bank = memory_bank
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize the storage hub."""
        try:
            if await self.factory.initialize(self.config.get("storage_path")):
                self.memory_storage = await self.factory.get_storage("memory")
                self.initialized = True
                return True
            return False
        except Exception as e:
            logger.error("Failed to initialize storage hub: %s", str(e))
            return False

    async def get_storage(self, name: str) -> Optional[Dict[str, Any]]:
        """Get storage instance by name."""
        if not self.initialized:
            await self.initialize()
        return await self.factory.get_storage(name)

    async def cleanup(self) -> None:
        """Clean up expired storage instances."""
        await self.factory.cleanup()

    async def get_metrics(self) -> Dict[str, Any]:
        """Get storage metrics."""
        return await self.factory.get_metrics()


async def create_storage_hub(
    config: Optional[Dict[str, Any]] = None,
    base_path: Optional[str] = None,
    memory_bank: Any = None,
) -> StorageHub:
    """Create and initialize a storage hub instance."""
    try:
        hub = StorageHub(config=config, base_path=base_path, memory_bank=memory_bank)
        if not await hub.initialize():
            raise RuntimeError("Failed to initialize storage hub")
        logger.debug("Storage hub created and initialized")
        return hub
    except Exception as e:
        logger.error("Failed to create storage hub: %s", str(e))
        raise
