"""
Memory-Mapped Files Implementation for Efficient Data Sharing

This module provides a memory-mapped file system for efficient data sharing
between processes with proper locking mechanisms and automatic cleanup.
"""

import os
import mmap
import json
import struct
import asyncio
import logging
import tempfile
# import threading # Unused
import contextlib
import time
import uuid
import pickle
# import weakref # Unused
import atexit
from enum import Enum
from typing import (
    Dict,
    Any,
    Optional,
    List,
    # Set, # Unused
    Tuple,
    Union,
    TypeVar,
    # Generic, # Unused
    Callable,
)
from dataclasses import dataclass, field
from pathlib import Path
from filelock import FileLock
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar("T")
SchemaType = Dict[str, Any]
DataType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class LockType(str, Enum):
    """Types of locks for shared memory regions."""

    READ = "read"
    WRITE = "write"
    EXCLUSIVE = "exclusive"


class MemoryRegionType(str, Enum):
    """Types of memory regions."""

    METRICS = "metrics"
    STATE = "state"
    CACHE = "cache"
    CONFIG = "config"
    CUSTOM = "custom"


@dataclass
class MemoryRegionInfo:
    """Information about a memory region."""

    name: str
    path: str
    size: int
    type: MemoryRegionType
    schema: Optional[SchemaType] = None
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    lock_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "type": self.type.value,
            "schema": self.schema,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "lock_path": self.lock_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRegionInfo":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            path=data["path"],
            size=data["size"],
            type=MemoryRegionType(data["type"]),
            schema=data.get("schema"),
            created_at=data.get("created_at", time.time()),
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 0),
            lock_path=data.get("lock_path"),
        )


class SharedMemoryError(Exception):
    """Base exception for shared memory errors."""

    pass


class SchemaValidationError(SharedMemoryError):
    """Exception raised when data doesn't match schema."""

    pass


class MemoryRegionNotFoundError(SharedMemoryError):
    """Exception raised when a memory region is not found."""

    pass


class LockAcquisitionError(SharedMemoryError):
    """Exception raised when a lock cannot be acquired."""

    pass


class CorruptDataError(SharedMemoryError):
    """Exception raised when data is corrupted."""

    pass


class SharedMemoryManager:
    """
    Manager for memory-mapped files with proper locking mechanisms.

    This class provides:
    - Creation and management of memory-mapped files
    - Proper locking mechanisms using file locks
    - Automatic cleanup on process exit
    - Support for structured data with schema validation
    """

    def __init__(self, base_dir: Optional[str] = None, executor_workers: int = 4):
        """
        Initialize the shared memory manager.

        Args:
            base_dir: Base directory for memory-mapped files
            executor_workers: Number of workers for the thread pool executor
        """
        # Base directory for memory-mapped files
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = (
                Path(tempfile.gettempdir()) / "arbitrage_bot" / "shared_memory"
            )

        # Create base directory if it doesn't exist
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Registry file path
        self.registry_path = self.base_dir / "registry.json"
        self.registry_lock_path = self.base_dir / "registry.lock"

        # Initialize registry if it doesn't exist
        if not self.registry_path.exists():
            with FileLock(str(self.registry_lock_path)):
                with open(self.registry_path, "w") as f:
                    json.dump({}, f)

        # Thread pool executor for blocking operations
        self._executor = ThreadPoolExecutor(max_workers=executor_workers)

        # Asyncio lock for thread safety
        self._lock = asyncio.Lock()

        # Set of open memory maps
        self._open_maps: Dict[str, Tuple[mmap.mmap, FileLock]] = {}

        # Register cleanup on process exit
        atexit.register(self._cleanup)

        logger.debug(
            f"SharedMemoryManager initialized with base directory: {self.base_dir}"
        )

    async def create_region(
        self,
        name: str,
        size: int,
        region_type: MemoryRegionType,
        schema: Optional[SchemaType] = None,
    ) -> MemoryRegionInfo:
        """
        Create a new memory region.

        Args:
            name: Name of the memory region
            size: Size of the memory region in bytes
            region_type: Type of the memory region
            schema: Optional schema for data validation

        Returns:
            Information about the created memory region

        Raises:
            ValueError: If a region with the same name already exists
        """
        async with self._lock:
            # Check if region already exists
            registry = await self._load_registry()
            if name in registry:
                raise ValueError(f"Memory region '{name}' already exists")

            # Create region file
            region_path = self.base_dir / f"{name}_{uuid.uuid4().hex}.dat"
            lock_path = self.base_dir / f"{name}_{uuid.uuid4().hex}.lock"

            # Create the file with the specified size
            await asyncio.to_thread(self._create_file, str(region_path), size)

            # Create region info
            region_info = MemoryRegionInfo(
                name=name,
                path=str(region_path),
                size=size,
                type=region_type,
                schema=schema,
                lock_path=str(lock_path),
            )

            # Update registry
            registry[name] = region_info.to_dict()
            await self._save_registry(registry)

            logger.debug(
                f"Created memory region '{name}' of type {region_type.value} with size {size} bytes"
            )

            return region_info

    async def get_region_info(self, name: str) -> MemoryRegionInfo:
        """
        Get information about a memory region.

        Args:
            name: Name of the memory region

        Returns:
            Information about the memory region

        Raises:
            MemoryRegionNotFoundError: If the region is not found
        """
        registry = await self._load_registry()
        if name not in registry:
            raise MemoryRegionNotFoundError(f"Memory region '{name}' not found")

        return MemoryRegionInfo.from_dict(registry[name])

    async def list_regions(
        self, region_type: Optional[MemoryRegionType] = None
    ) -> List[MemoryRegionInfo]:
        """
        List all memory regions.

        Args:
            region_type: Optional filter by region type

        Returns:
            List of memory region information
        """
        registry = await self._load_registry()
        regions = [MemoryRegionInfo.from_dict(info) for info in registry.values()]

        if region_type:
            regions = [region for region in regions if region.type == region_type]

        return regions

    async def delete_region(self, name: str) -> bool:
        """
        Delete a memory region.

        Args:
            name: Name of the memory region

        Returns:
            True if the region was deleted, False otherwise

        Raises:
            MemoryRegionNotFoundError: If the region is not found
        """
        async with self._lock:
            registry = await self._load_registry()
            if name not in registry:
                raise MemoryRegionNotFoundError(f"Memory region '{name}' not found")

            region_info = MemoryRegionInfo.from_dict(registry[name])

            # Close and remove from open maps if open
            if name in self._open_maps:
                mm, lock = self._open_maps[name]
                mm.close()
                lock.release()
                del self._open_maps[name]

            # Delete the file
            try:
                os.remove(region_info.path)
                if region_info.lock_path:
                    os.remove(region_info.lock_path)
            except OSError as e:
                logger.error(f"Error deleting memory region files: {e}")

            # Update registry
            del registry[name]
            await self._save_registry(registry)

            logger.debug(f"Deleted memory region '{name}'")

            return True

    @contextlib.asynccontextmanager
    async def open_region(self, name: str, lock_type: LockType = LockType.READ):
        """
        Open a memory region for reading or writing.

        Args:
            name: Name of the memory region
            lock_type: Type of lock to acquire

        Yields:
            Memory-mapped file object

        Raises:
            MemoryRegionNotFoundError: If the region is not found
            LockAcquisitionError: If the lock cannot be acquired
        """
        region_info = await self.get_region_info(name)

        # Determine access mode based on lock type
        access_mode = mmap.ACCESS_READ
        if lock_type in (LockType.WRITE, LockType.EXCLUSIVE):
            access_mode = mmap.ACCESS_WRITE

        # Acquire lock
        lock = FileLock(region_info.lock_path)
        try:
            # Non-blocking for read locks if not exclusive
            blocking = lock_type == LockType.EXCLUSIVE
            lock.acquire(blocking=blocking, timeout=10)
        except TimeoutError:
            raise LockAcquisitionError(
                f"Failed to acquire lock for memory region '{name}'"
            )

        try:
            # Open the file
            f = open(
                region_info.path, "r+b" if access_mode == mmap.ACCESS_WRITE else "rb"
            )

            # Create memory map
            mm = mmap.mmap(f.fileno(), 0, access=access_mode)

            # Store in open maps
            self._open_maps[name] = (mm, lock)

            # Update access statistics
            await self._update_access_stats(name)

            try:
                yield mm
            finally:
                # Close memory map
                mm.close()
                f.close()

                # Release lock
                lock.release()

                # Remove from open maps
                if name in self._open_maps:
                    del self._open_maps[name]
        except Exception as e:
            # Release lock on error
            lock.release()
            logger.error(f"Error opening memory region '{name}': {e}")
            raise

    async def write_data(
        self, name: str, data: Any, offset: int = 0, validate: bool = True
    ) -> int:
        """
        Write data to a memory region.

        Args:
            name: Name of the memory region
            data: Data to write (will be pickled)
            offset: Offset in bytes
            validate: Whether to validate against schema

        Returns:
            Number of bytes written

        Raises:
            MemoryRegionNotFoundError: If the region is not found
            SchemaValidationError: If data doesn't match schema
        """
        region_info = await self.get_region_info(name)

        # Validate against schema if needed
        if validate and region_info.schema:
            if not self._validate_schema(data, region_info.schema):
                raise SchemaValidationError(
                    f"Data doesn't match schema for memory region '{name}'"
                )

        # Pickle data
        pickled_data = pickle.dumps(data)
        data_size = len(pickled_data)

        # Check if data fits
        if offset + data_size > region_info.size:
            raise ValueError(
                f"Data size ({data_size} bytes) exceeds available space in memory region '{name}'"
            )

        # Write data
        async with self.open_region(name, LockType.WRITE) as mm:
            mm.seek(offset)
            mm.write(struct.pack("!I", data_size))
            mm.write(pickled_data)

        return data_size + 4  # 4 bytes for size header

    async def read_data(self, name: str, offset: int = 0) -> Any:
        """
        Read data from a memory region.

        Args:
            name: Name of the memory region
            offset: Offset in bytes

        Returns:
            Unpickled data

        Raises:
            MemoryRegionNotFoundError: If the region is not found
            CorruptDataError: If data is corrupted
        """
        async with self.open_region(name, LockType.READ) as mm:
            try:
                mm.seek(offset)
                size_bytes = mm.read(4)
                if len(size_bytes) < 4:
                    raise CorruptDataError(
                        f"Failed to read size header from memory region '{name}'"
                    )

                data_size = struct.unpack("!I", size_bytes)[0]
                pickled_data = mm.read(data_size)

                if len(pickled_data) < data_size:
                    raise CorruptDataError(
                        f"Failed to read complete data from memory region '{name}'"
                    )

                return pickle.loads(pickled_data)
            except (pickle.PickleError, struct.error) as e:
                raise CorruptDataError(f"Corrupt data in memory region '{name}': {e}")

    async def update_data(
        self,
        name: str,
        update_func: Callable[[Any], Any],
        offset: int = 0,
        validate: bool = True,
    ) -> int:
        """
        Update data in a memory region using an update function.

        Args:
            name: Name of the memory region
            update_func: Function that takes current data and returns updated data
            offset: Offset in bytes
            validate: Whether to validate against schema

        Returns:
            Number of bytes written

        Raises:
            MemoryRegionNotFoundError: If the region is not found
            SchemaValidationError: If data doesn't match schema
        """
        async with self._lock:
            # Read current data
            current_data = await self.read_data(name, offset)

            # Apply update function
            updated_data = update_func(current_data)

            # Write updated data
            return await self.write_data(name, updated_data, offset, validate)

    async def _load_registry(self) -> Dict[str, Any]:
        """Load the registry file."""
        try:
            async with asyncio.to_thread(FileLock, str(self.registry_lock_path)):
                return await asyncio.to_thread(self._load_registry_sync)
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return {}

    def _load_registry_sync(self) -> Dict[str, Any]:
        """Synchronous version of loading the registry file."""
        with open(self.registry_path, "r") as f:
            return json.load(f)

    async def _save_registry(self, registry: Dict[str, Any]) -> None:
        """Save the registry file."""
        try:
            async with asyncio.to_thread(FileLock, str(self.registry_lock_path)):
                await asyncio.to_thread(self._save_registry_sync, registry)
        except Exception as e:
            logger.error(f"Error saving registry: {e}")

    def _save_registry_sync(self, registry: Dict[str, Any]) -> None:
        """Synchronous version of saving the registry file."""
        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2)

    async def _update_access_stats(self, name: str) -> None:
        """Update access statistics for a memory region."""
        registry = await self._load_registry()
        if name in registry:
            registry[name]["last_accessed"] = time.time()
            registry[name]["access_count"] += 1
            await self._save_registry(registry)

    def _create_file(self, path: str, size: int) -> None:
        """Create a file with the specified size."""
        with open(path, "wb") as f:
            f.seek(size - 1)
            f.write(b"\0")

    def _validate_schema(self, data: Any, schema: SchemaType) -> bool:
        """
        Validate data against a schema.

        This is a simple implementation. In a real-world scenario,
        you might want to use a more robust schema validation library.
        """
        # For now, just check if the data is a dictionary with the required keys
        if not isinstance(schema, dict) or not isinstance(data, dict):
            return False

        for key, value_type in schema.items():
            if key not in data:
                return False

            if value_type == "string" and not isinstance(data[key], str):
                return False
            elif value_type == "number" and not isinstance(data[key], (int, float)):
                return False
            elif value_type == "boolean" and not isinstance(data[key], bool):
                return False
            elif value_type == "object" and not isinstance(data[key], dict):
                return False
            elif value_type == "array" and not isinstance(data[key], list):
                return False

        return True

    def _cleanup(self) -> None:
        """Clean up resources on process exit."""
        # Close all open memory maps
        for name, (mm, lock) in self._open_maps.items():
            try:
                mm.close()
                lock.release()
            except Exception as e:
                logger.error(f"Error closing memory map '{name}': {e}")

        # Shutdown executor
        self._executor.shutdown(wait=False)

        logger.debug("SharedMemoryManager cleaned up")


class SharedMetricsStore:
    """
    Memory-mapped metrics storage with atomic updates and TTL-based cache invalidation.

    This class provides:
    - Efficient storage of metrics data in memory-mapped files
    - Atomic update operations
    - Efficient read access with minimal locking
    - TTL-based cache invalidation
    """

    def __init__(
        self, memory_manager: SharedMemoryManager, region_size: int = 1024 * 1024
    ):
        """
        Initialize the shared metrics store.

        Args:
            memory_manager: Shared memory manager
            region_size: Size of memory regions in bytes
        """
        self.memory_manager = memory_manager
        self.region_size = region_size
        self._lock = asyncio.Lock()
        self._metrics_regions: Dict[str, str] = {}  # Maps metric type to region name
        self._ttl_values: Dict[str, float] = {}  # TTL values for each metric type

        # Default TTL values (seconds)
        self._default_ttl = 10.0

        logger.debug("SharedMetricsStore initialized")

    async def initialize(self) -> None:
        """Initialize the metrics store."""
        async with self._lock:
            # Create registry region if it doesn't exist
            try:
                await self.memory_manager.get_region_info("metrics_registry")
            except MemoryRegionNotFoundError:
                await self.memory_manager.create_region(
                    name="metrics_registry",
                    size=64 * 1024,  # 64 KB
                    region_type=MemoryRegionType.METRICS,
                    schema={"metrics_regions": "object", "ttl_values": "object"},
                )

                # Initialize registry data
                await self.memory_manager.write_data(
                    name="metrics_registry",
                    data={"metrics_regions": {}, "ttl_values": {}},
                )

            # Load registry data
            registry_data = await self.memory_manager.read_data("metrics_registry")
            self._metrics_regions = registry_data.get("metrics_regions", {})
            self._ttl_values = registry_data.get("ttl_values", {})

            logger.debug("SharedMetricsStore initialized")

    async def set_ttl(self, metric_type: str, ttl: float) -> None:
        """
        Set TTL for a metric type.

        Args:
            metric_type: Type of metrics
            ttl: Time-to-live in seconds
        """
        async with self._lock:
            self._ttl_values[metric_type] = ttl

            # Update registry
            registry_data = await self.memory_manager.read_data("metrics_registry")
            registry_data["ttl_values"] = self._ttl_values
            await self.memory_manager.write_data("metrics_registry", registry_data)

    async def get_ttl(self, metric_type: str) -> float:
        """
        Get TTL for a metric type.

        Args:
            metric_type: Type of metrics

        Returns:
            TTL in seconds
        """
        return self._ttl_values.get(metric_type, self._default_ttl)

    async def store_metrics(self, metric_type: str, metrics: Dict[str, Any]) -> None:
        """
        Store metrics data.

        Args:
            metric_type: Type of metrics
            metrics: Metrics data
        """
        # Ensure region exists
        region_name = await self._ensure_region(metric_type)

        # Add timestamp
        metrics_with_timestamp = {"data": metrics, "timestamp": time.time()}

        # Write data
        await self.memory_manager.write_data(region_name, metrics_with_timestamp)

    async def get_metrics(self, metric_type: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics data.

        Args:
            metric_type: Type of metrics

        Returns:
            Metrics data or None if not found or expired
        """
        # Check if region exists
        if metric_type not in self._metrics_regions:
            return None

        region_name = self._metrics_regions[metric_type]

        try:
            # Read data
            metrics_with_timestamp = await self.memory_manager.read_data(region_name)

            # Check TTL
            ttl = await self.get_ttl(metric_type)
            if time.time() - metrics_with_timestamp["timestamp"] > ttl:
                return None

            return metrics_with_timestamp["data"]
        except (MemoryRegionNotFoundError, CorruptDataError) as e:
            logger.error(f"Error reading metrics for {metric_type}: {e}")
            return None

    async def update_metrics(
        self, metric_type: str, update_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> None:
        """
        Update metrics data using an update function.

        Args:
            metric_type: Type of metrics
            update_func: Function that takes current metrics and returns updated metrics
        """
        # Ensure region exists
        region_name = await self._ensure_region(metric_type)

        # Define update function for the entire data structure
        def update_wrapper(data: Dict[str, Any]) -> Dict[str, Any]:
            current_metrics = data.get("data", {}) if data else {}
            updated_metrics = update_func(current_metrics)
            return {"data": updated_metrics, "timestamp": time.time()}

        # Update data
        await self.memory_manager.update_data(region_name, update_wrapper)

    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all metrics data.

        Returns:
            Dictionary mapping metric types to their data
        """
        result = {}
        for metric_type in self._metrics_regions:
            metrics = await self.get_metrics(metric_type)
            if metrics:
                result[metric_type] = metrics

        return result

    async def clear_expired_metrics(self) -> int:
        """
        Clear expired metrics.

        Returns:
            Number of cleared metrics
        """
        count = 0
        for metric_type in list(self._metrics_regions.keys()):
            region_name = self._metrics_regions[metric_type]

            try:
                # Read data
                metrics_with_timestamp = await self.memory_manager.read_data(
                    region_name
                )

                # Check TTL
                ttl = await self.get_ttl(metric_type)
                if time.time() - metrics_with_timestamp["timestamp"] > ttl:
                    # Clear data
                    await self.memory_manager.write_data(
                        region_name, {"data": {}, "timestamp": time.time()}
                    )
                    count += 1
            except (MemoryRegionNotFoundError, CorruptDataError) as e:
                logger.error(f"Error clearing expired metrics for {metric_type}: {e}")

        return count

    async def _ensure_region(self, metric_type: str) -> str:
        """
        Ensure a memory region exists for the metric type.

        Args:
            metric_type: Type of metrics

        Returns:
            Name of the memory region
        """
        async with self._lock:
            if metric_type in self._metrics_regions:
                return self._metrics_regions[metric_type]

            # Create new region
            region_name = f"metrics_{metric_type}_{uuid.uuid4().hex}"
            await self.memory_manager.create_region(
                name=region_name,
                size=self.region_size,
                region_type=MemoryRegionType.METRICS,
            )

            # Update registry
            self._metrics_regions[metric_type] = region_name
            registry_data = await self.memory_manager.read_data("metrics_registry")
            registry_data["metrics_regions"] = self._metrics_regions
            await self.memory_manager.write_data("metrics_registry", registry_data)

            return region_name


class SharedStateManager:
    """
    Process-safe state sharing with change notification and versioning.

    This class provides:
    - Process-safe state sharing
    - Change notification system
    - Versioning for conflict resolution
    - Error handling for corrupt states
    """

    def __init__(
        self, memory_manager: SharedMemoryManager, region_size: int = 1024 * 1024
    ):
        """
        Initialize the shared state manager.

        Args:
            memory_manager: Shared memory manager
            region_size: Size of memory regions in bytes
        """
        self.memory_manager = memory_manager
        self.region_size = region_size
        self._lock = asyncio.Lock()
        self._state_regions: Dict[str, str] = {}  # Maps state name to region name
        self._change_callbacks: Dict[
            str, List[Callable[[Dict[str, Any], int], None]]
        ] = {}

        logger.debug("SharedStateManager initialized")

    async def initialize(self) -> None:
        """Initialize the state manager."""
        async with self._lock:
            # Create registry region if it doesn't exist
            try:
                await self.memory_manager.get_region_info("state_registry")
            except MemoryRegionNotFoundError:
                await self.memory_manager.create_region(
                    name="state_registry",
                    size=64 * 1024,  # 64 KB
                    region_type=MemoryRegionType.STATE,
                    schema={"state_regions": "object"},
                )

                # Initialize registry data
                await self.memory_manager.write_data(
                    name="state_registry", data={"state_regions": {}}
                )

            # Load registry data
            registry_data = await self.memory_manager.read_data("state_registry")
            self._state_regions = registry_data.get("state_regions", {})

            logger.debug("SharedStateManager initialized")

    async def set_state(
        self, state_name: str, state: Dict[str, Any], version: Optional[int] = None
    ) -> int:
        """
        Set state data.

        Args:
            state_name: Name of the state
            state: State data
            version: Optional version for conflict resolution

        Returns:
            New version number

        Raises:
            ValueError: If version doesn't match current version
        """
        # Ensure region exists
        region_name = await self._ensure_region(state_name)

        # Define update function
        def update_wrapper(current_data: Dict[str, Any]) -> Dict[str, Any]:
            if current_data is None:
                current_data = {"data": {}, "version": 0}

            current_version = current_data.get("version", 0)

            # Check version if provided
            if version is not None and version != current_version:
                raise ValueError(
                    f"Version mismatch: expected {version}, got {current_version}"
                )

            # Update data
            new_version = current_version + 1
            return {"data": state, "version": new_version, "timestamp": time.time()}

        try:
            # Update data
            await self.memory_manager.update_data(region_name, update_wrapper)

            # Get updated data
            updated_data = await self.memory_manager.read_data(region_name)
            new_version = updated_data["version"]

            # Notify callbacks
            await self._notify_change(state_name, state, new_version)

            return new_version
        except ValueError as e:
            logger.error(f"Error setting state '{state_name}': {e}")
            raise

    async def get_state(self, state_name: str) -> Tuple[Dict[str, Any], int]:
        """
        Get state data.

        Args:
            state_name: Name of the state

        Returns:
            Tuple of (state data, version)

        Raises:
            MemoryRegionNotFoundError: If the state is not found
        """
        # Check if region exists
        if state_name not in self._state_regions:
            raise MemoryRegionNotFoundError(f"State '{state_name}' not found")

        region_name = self._state_regions[state_name]

        try:
            # Read data
            state_data = await self.memory_manager.read_data(region_name)
            return state_data["data"], state_data["version"]
        except (MemoryRegionNotFoundError, CorruptDataError) as e:
            logger.error(f"Error reading state '{state_name}': {e}")
            raise

    async def register_change_callback(
        self, state_name: str, callback: Callable[[Dict[str, Any], int], None]
    ) -> None:
        """
        Register a callback for state changes.

        Args:
            state_name: Name of the state
            callback: Callback function that takes state data and version
        """
        if state_name not in self._change_callbacks:
            self._change_callbacks[state_name] = []

        self._change_callbacks[state_name].append(callback)

    async def _notify_change(
        self, state_name: str, state: Dict[str, Any], version: int
    ) -> None:
        """
        Notify callbacks of state changes.

        Args:
            state_name: Name of the state
            state: State data
            version: State version
        """
        if state_name in self._change_callbacks:
            for callback in self._change_callbacks[state_name]:
                try:
                    callback(state, version)
                except Exception as e:
                    logger.error(
                        f"Error in state change callback for '{state_name}': {e}"
                    )

    async def _ensure_region(self, state_name: str) -> str:
        """
        Ensure a memory region exists for the state.

        Args:
            state_name: Name of the state

        Returns:
            Name of the memory region
        """
        async with self._lock:
            if state_name in self._state_regions:
                return self._state_regions[state_name]

            # Create new region
            region_name = f"state_{state_name}_{uuid.uuid4().hex}"
            await self.memory_manager.create_region(
                name=region_name,
                size=self.region_size,
                region_type=MemoryRegionType.STATE,
            )

            # Update registry
            self._state_regions[state_name] = region_name
            registry_data = await self.memory_manager.read_data("state_registry")
            registry_data["state_regions"] = self._state_regions
            await self.memory_manager.write_data("state_registry", registry_data)

            return region_name
