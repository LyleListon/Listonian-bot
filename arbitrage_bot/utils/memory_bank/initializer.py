"""Memory Bank Initialization.

This module provides functionality to initialize and verify the memory bank system,
ensuring all required components are in place and properly configured.
"""

import asyncio
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .monitor import MemoryBankMonitor, HealthStatus
from .schema import SchemaValidator

logger = logging.getLogger(__name__)

CORE_DIRECTORIES = ['trades', 'metrics', 'state']
CORE_FILES = [
    'projectbrief.md',
    'productContext.md',
    'systemPatterns.md',
    'techContext.md',
    'activeContext.md',
    'progress.md'
]

class MemoryBankInitializer:
    """Handles initialization and verification of the memory bank system."""

    def __init__(self, base_path: Path):
        self._base_path = Path(base_path)
        self._initialized = False
        self._lock = asyncio.Lock()
        self._monitor: Optional[MemoryBankMonitor] = None
        self._validator: Optional[SchemaValidator] = None
        self._backup_path = self._base_path / '.backups' / datetime.now().strftime('%Y%m%d_%H%M%S')

    async def initialize(self, preserve_data: bool = True) -> None:
        """Initialize the memory bank system.

        Args:
            preserve_data: Whether to preserve existing data during initialization.
        """
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing memory bank system")

            try:
                # Create backup if preserving data
                if preserve_data:
                    await self._create_backup()

                # Initialize core components
                await self._initialize_directories()
                await self._initialize_core_files()

                # Set up monitoring and validation
                self._monitor = MemoryBankMonitor(self._base_path)
                self._validator = SchemaValidator()

                await self._monitor.initialize()
                await self._validator.initialize()

                # Validate existing data if preserving
                if preserve_data:
                    await self._validate_existing_data()

                self._initialized = True
                logger.info("Memory bank system initialized successfully")

            except Exception as e:
                error_msg = f"Failed to initialize memory bank: {e}"
                logger.error(error_msg, exc_info=True)
                if preserve_data:
                    await self._restore_backup()
                raise RuntimeError(error_msg)

    async def _create_backup(self) -> None:
        """Create a backup of the current memory bank state."""
        logger.info("Creating memory bank backup")

        try:
            if self._base_path.exists():
                self._backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(
                    self._base_path,
                    self._backup_path,
                    ignore=shutil.ignore_patterns('.backups', '__pycache__', '*.pyc')
                )
                logger.info(f"Backup created at {self._backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    async def _restore_backup(self) -> None:
        """Restore from backup in case of initialization failure."""
        if not self._backup_path.exists():
            return

        logger.info("Restoring from backup")

        try:
            if self._base_path.exists():
                shutil.rmtree(self._base_path)
            shutil.copytree(self._backup_path, self._base_path)
            logger.info("Backup restored successfully")
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            raise

    async def _initialize_directories(self) -> None:
        """Initialize required directory structure."""
        logger.info("Initializing directory structure")

        try:
            self._base_path.mkdir(parents=True, exist_ok=True)
            for dir_name in CORE_DIRECTORIES:
                dir_path = self._base_path / dir_name
                dir_path.mkdir(exist_ok=True)
                logger.debug(f"Directory created/verified: {dir_path}")
        except Exception as e:
            logger.error(f"Failed to initialize directories: {e}")
            raise

    async def _initialize_core_files(self) -> None:
        """Initialize core documentation files."""
        logger.info("Initializing core files")

        try:
            timestamp = datetime.utcnow().isoformat()
            for file_name in CORE_FILES:
                file_path = self._base_path / file_name
                if not file_path.exists():
                    with open(file_path, 'w') as f:
                        f.write(f"# Listonian Arbitrage Bot - {file_name.replace('.md', '')}\n\n")
                        f.write(f"Created: {timestamp}\n\n")
                        f.write("[Content to be added]\n")
                    logger.debug(f"Core file created: {file_path}")
        except Exception as e:
            logger.error(f"Failed to initialize core files: {e}")
            raise

    async def _validate_existing_data(self) -> None:
        """Validate existing data structures."""
        logger.info("Validating existing data")

        try:
            # Validate trades
            trades_dir = self._base_path / 'trades'
            for trade_file in trades_dir.glob('*.json'):
                await self._validator.validate_file(trade_file, 'trade')

            # Validate metrics
            metrics_file = self._base_path / 'metrics' / 'metrics.json'
            if metrics_file.exists():
                await self._validator.validate_file(metrics_file, 'metrics')

            logger.info("Data validation completed successfully")

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            raise

    async def get_status(self) -> HealthStatus:
        """Get current initialization status."""
        if not self._initialized or not self._monitor:
            raise RuntimeError("Memory bank not initialized")
        return await self._monitor.get_health_status()

    async def cleanup(self) -> None:
        """Clean up initialization resources."""
        async with self._lock:
            if not self._initialized:
                return

            logger.info("Cleaning up memory bank initializer")

            try:
                if self._monitor:
                    await self._monitor.cleanup()
                if self._validator:
                    await self._validator.cleanup()

                self._initialized = False
                logger.info("Memory bank initializer cleaned up successfully")

            except Exception as e:
                logger.error(f"Error cleaning up memory bank initializer: {e}")
                raise

async def initialize_memory_bank(
    base_path: Path,
    preserve_data: bool = True
) -> HealthStatus:
    """Initialize the memory bank system.

    Args:
        base_path: Base path for the memory bank.
        preserve_data: Whether to preserve existing data.

    Returns:
        HealthStatus: Current health status after initialization.
    """
    initializer = MemoryBankInitializer(base_path)
    await initializer.initialize(preserve_data)
    status = await initializer.get_status()
    await initializer.cleanup()
    return status