"""Memory Bank Monitoring System.

This module provides real-time monitoring and integrity checking for the memory bank system.
It ensures data consistency, validates schemas, and maintains system health metrics.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FileIntegrityInfo:
    """Information about a file's integrity state."""
    path: Path
    checksum: str
    last_validated: datetime
    size: int
    is_valid: bool = True
    error_message: Optional[str] = None

@dataclass
class HealthStatus:
    """System health status information."""
    status: str  # healthy|degraded|error
    message: str
    timestamp: datetime
    metrics: Dict[str, Any]

class MemoryBankMonitor:
    """Monitors the memory bank system in real-time."""

    def __init__(self, base_path: Path):
        self._base_path = Path(base_path)
        self._initialized = False
        self._lock = asyncio.Lock()
        self._file_checksums: Dict[Path, FileIntegrityInfo] = {}
        self._health_status = HealthStatus(
            status="initializing",
            message="Monitor starting up",
            timestamp=datetime.utcnow(),
            metrics={}
        )
        self._watched_paths: Set[Path] = set()
        self._check_interval = 30  # seconds
        self._monitoring_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize the monitoring system."""
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing memory bank monitor")

            try:
                # Ensure base directories exist
                for dir_name in ['trades', 'metrics', 'state']:
                    dir_path = self._base_path / dir_name
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self._watched_paths.add(dir_path)

                # Initialize file checksums
                await self._initialize_checksums()

                # Start monitoring task
                self._monitoring_task = asyncio.create_task(
                    self._monitoring_loop()
                )

                self._initialized = True
                self._health_status = HealthStatus(
                    status="healthy",
                    message="Monitor initialized successfully",
                    timestamp=datetime.utcnow(),
                    metrics={
                        "watched_files": len(self._file_checksums),
                        "watched_dirs": len(self._watched_paths)
                    }
                )
                logger.info("Memory bank monitor initialized successfully")

            except Exception as e:
                error_msg = f"Failed to initialize memory bank monitor: {e}"
                logger.error(error_msg, exc_info=True)
                self._health_status = HealthStatus(
                    status="error",
                    message=error_msg,
                    timestamp=datetime.utcnow(),
                    metrics={}
                )
                raise

    async def _initialize_checksums(self) -> None:
        """Initialize checksums for all monitored files."""
        for path in self._watched_paths:
            if path.is_dir():
                for file_path in path.glob('**/*'):
                    if file_path.is_file():
                        checksum = await self._calculate_checksum(file_path)
                        self._file_checksums[file_path] = FileIntegrityInfo(
                            path=file_path,
                            checksum=checksum,
                            last_validated=datetime.utcnow(),
                            size=file_path.stat().st_size
                        )

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        hasher = hashlib.sha256()
        try:
            # Read in chunks to handle large files
            chunk_size = 8192
            async with asyncio.Lock():
                with open(file_path, 'rb') as f:
                    while chunk := f.read(chunk_size):
                        hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating checksum for {file_path}: {e}")
            raise

    async def _validate_file_integrity(self, file_path: Path) -> FileIntegrityInfo:
        """Validate a file's integrity."""
        try:
            current_checksum = await self._calculate_checksum(file_path)
            current_size = file_path.stat().st_size
            previous_info = self._file_checksums.get(file_path)

            if not previous_info:
                return FileIntegrityInfo(
                    path=file_path,
                    checksum=current_checksum,
                    last_validated=datetime.utcnow(),
                    size=current_size
                )

            is_valid = (
                current_checksum == previous_info.checksum and
                current_size == previous_info.size
            )

            return FileIntegrityInfo(
                path=file_path,
                checksum=current_checksum,
                last_validated=datetime.utcnow(),
                size=current_size,
                is_valid=is_valid,
                error_message=None if is_valid else "File modified unexpectedly"
            )

        except Exception as e:
            error_msg = f"Error validating {file_path}: {e}"
            logger.error(error_msg)
            return FileIntegrityInfo(
                path=file_path,
                checksum="",
                last_validated=datetime.utcnow(),
                size=0,
                is_valid=False,
                error_message=error_msg
            )

    async def _check_system_health(self) -> HealthStatus:
        """Check overall system health."""
        try:
            invalid_files = []
            total_size = 0
            metrics = {
                "total_files": 0,
                "total_size_bytes": 0,
                "invalid_files": 0,
                "last_check": datetime.utcnow().isoformat()
            }

            for file_path, integrity_info in self._file_checksums.items():
                metrics["total_files"] += 1
                metrics["total_size_bytes"] += integrity_info.size
                if not integrity_info.is_valid:
                    metrics["invalid_files"] += 1
                    invalid_files.append(str(file_path))

            status = "healthy"
            message = "All systems operational"

            if metrics["invalid_files"] > 0:
                status = "degraded"
                message = f"Found {metrics['invalid_files']} invalid files"

            if metrics["invalid_files"] > metrics["total_files"] // 3:
                status = "error"
                message = "Critical number of invalid files detected"

            return HealthStatus(
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                metrics=metrics
            )

        except Exception as e:
            error_msg = f"Error checking system health: {e}"
            logger.error(error_msg, exc_info=True)
            return HealthStatus(
                status="error",
                message=error_msg,
                timestamp=datetime.utcnow(),
                metrics={}
            )

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            try:
                for file_path in list(self._file_checksums.keys()):
                    integrity_info = await self._validate_file_integrity(file_path)
                    self._file_checksums[file_path] = integrity_info

                    if not integrity_info.is_valid:
                        logger.warning(
                            f"File integrity check failed for {file_path}: "
                            f"{integrity_info.error_message}"
                        )

                self._health_status = await self._check_system_health()

                if self._health_status.status != "healthy":
                    logger.warning(
                        f"System health degraded: {self._health_status.message}"
                    )

                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self._check_interval)

    async def get_health_status(self) -> HealthStatus:
        """Get current system health status."""
        if not self._initialized:
            raise RuntimeError("Monitor not initialized")
        return self._health_status

    async def cleanup(self) -> None:
        """Clean up monitoring resources."""
        async with self._lock:
            if not self._initialized:
                return

            logger.info("Cleaning up memory bank monitor")

            try:
                if self._monitoring_task:
                    self._monitoring_task.cancel()
                    try:
                        await self._monitoring_task
                    except asyncio.CancelledError:
                        pass

                self._initialized = False
                logger.info("Memory bank monitor cleaned up successfully")

            except Exception as e:
                logger.error(f"Error cleaning up memory bank monitor: {e}")
                raise