"""
DEX Repository

This module provides a repository for storing and managing discovered DEXes.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set

from eth_utils import to_checksum_address

from .base import DEXInfo, DEXProtocolType

logger = logging.getLogger(__name__)


class DEXRepository:
    """
    Repository for storing and managing discovered DEXes.

    This class provides methods for adding, retrieving, and validating DEXes,
    as well as persisting them to disk.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the DEX repository.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._dexes: Dict[str, DEXInfo] = {}  # name -> DEXInfo
        self._dexes_by_address: Dict[str, DEXInfo] = {}  # factory_address -> DEXInfo
        self._lock = asyncio.Lock()
        self._initialized = False

        # Storage configuration
        self._storage_dir = self.config.get("storage_dir", "data/dexes")
        self._storage_file = self.config.get("storage_file", "dexes.json")
        self._auto_save = self.config.get("auto_save", True)

    async def initialize(self) -> bool:
        """
        Initialize the DEX repository.

        Returns:
            True if initialization was successful, False otherwise
        """
        async with self._lock:
            if self._initialized:
                return True

            logger.info("Initializing DEX repository")

            # Create storage directory if it doesn't exist
            os.makedirs(self._storage_dir, exist_ok=True)

            # Load existing DEXes from disk
            await self._load_dexes()

            self._initialized = True
            logger.info(f"DEX repository initialized with {len(self._dexes)} DEXes")
            return True

    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            if self._auto_save:
                await self._save_dexes()

            self._dexes.clear()
            self._dexes_by_address.clear()
            self._initialized = False

    async def add_dex(self, dex_info: DEXInfo) -> bool:
        """
        Add a DEX to the repository.

        Args:
            dex_info: DEX information

        Returns:
            True if the DEX was added, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            # Check if DEX already exists
            if dex_info.name in self._dexes:
                existing_dex = self._dexes[dex_info.name]

                # Update if newer
                if dex_info.last_updated > existing_dex.last_updated:
                    logger.info(f"Updating DEX {dex_info.name} with newer information")
                    self._dexes[dex_info.name] = dex_info
                    self._dexes_by_address[dex_info.factory_address] = dex_info

                    if self._auto_save:
                        await self._save_dexes()

                    return True

                return False

            # Add new DEX
            logger.info(f"Adding new DEX {dex_info.name}")
            self._dexes[dex_info.name] = dex_info
            self._dexes_by_address[dex_info.factory_address] = dex_info

            if self._auto_save:
                await self._save_dexes()

            return True

    async def add_dexes(self, dex_infos: List[DEXInfo]) -> int:
        """
        Add multiple DEXes to the repository.

        Args:
            dex_infos: List of DEX information

        Returns:
            Number of DEXes added
        """
        if not self._initialized:
            await self.initialize()

        added_count = 0

        for dex_info in dex_infos:
            if await self.add_dex(dex_info):
                added_count += 1

        return added_count

    async def get_dex(self, name: str) -> Optional[DEXInfo]:
        """
        Get a DEX by name.

        Args:
            name: DEX name

        Returns:
            DEX information or None if not found
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            return self._dexes.get(name)

    async def get_dex_by_address(self, factory_address: str) -> Optional[DEXInfo]:
        """
        Get a DEX by factory address.

        Args:
            factory_address: Factory contract address

        Returns:
            DEX information or None if not found
        """
        if not self._initialized:
            await self.initialize()

        # Normalize address
        factory_address = to_checksum_address(factory_address)

        async with self._lock:
            return self._dexes_by_address.get(factory_address)

    async def get_all_dexes(self) -> List[DEXInfo]:
        """
        Get all DEXes.

        Returns:
            List of all DEXes
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            return list(self._dexes.values())

    async def get_dexes_by_chain(self, chain_id: int) -> List[DEXInfo]:
        """
        Get DEXes for a specific chain.

        Args:
            chain_id: Chain ID

        Returns:
            List of DEXes for the specified chain
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            return [dex for dex in self._dexes.values() if dex.chain_id == chain_id]

    async def get_dexes_by_protocol(
        self, protocol_type: DEXProtocolType
    ) -> List[DEXInfo]:
        """
        Get DEXes of a specific protocol type.

        Args:
            protocol_type: Protocol type

        Returns:
            List of DEXes of the specified protocol type
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            return [
                dex
                for dex in self._dexes.values()
                if dex.protocol_type == protocol_type
            ]

    async def remove_dex(self, name: str) -> bool:
        """
        Remove a DEX from the repository.

        Args:
            name: DEX name

        Returns:
            True if the DEX was removed, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            if name in self._dexes:
                dex = self._dexes[name]
                del self._dexes[name]
                del self._dexes_by_address[dex.factory_address]

                if self._auto_save:
                    await self._save_dexes()

                return True

            return False

    async def mark_validated(
        self, name: str, validated: bool = True, errors: List[str] = None
    ) -> bool:
        """
        Mark a DEX as validated.

        Args:
            name: DEX name
            validated: Validation status
            errors: Validation errors

        Returns:
            True if the DEX was updated, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            if name in self._dexes:
                dex = self._dexes[name]
                dex.validated = validated
                dex.validation_errors = errors or []

                if self._auto_save:
                    await self._save_dexes()

                return True

            return False

    async def count(self) -> int:
        """
        Get the number of DEXes in the repository.

        Returns:
            Number of DEXes
        """
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            return len(self._dexes)

    async def save(self) -> bool:
        """
        Save DEXes to disk.

        Returns:
            True if the save was successful, False otherwise
        """
        if not self._initialized:
            await self.initialize()

        return await self._save_dexes()

    async def _load_dexes(self) -> None:
        """Load DEXes from disk."""
        storage_path = os.path.join(self._storage_dir, self._storage_file)

        if not os.path.exists(storage_path):
            logger.info(
                f"DEX storage file {storage_path} not found, starting with empty repository"
            )
            return

        try:
            with open(storage_path, "r") as f:
                data = json.load(f)

            for dex_data in data:
                try:
                    dex_info = DEXInfo.from_dict(dex_data)
                    self._dexes[dex_info.name] = dex_info
                    self._dexes_by_address[dex_info.factory_address] = dex_info
                except Exception as e:
                    logger.error(f"Error loading DEX: {e}")

            logger.info(f"Loaded {len(self._dexes)} DEXes from {storage_path}")

        except Exception as e:
            logger.error(f"Error loading DEXes from {storage_path}: {e}")

    async def _save_dexes(self) -> bool:
        """
        Save DEXes to disk.

        Returns:
            True if the save was successful, False otherwise
        """
        storage_path = os.path.join(self._storage_dir, self._storage_file)

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)

            # Convert DEXes to dictionaries
            dex_data = [dex.to_dict() for dex in self._dexes.values()]

            # Write to file
            with open(storage_path, "w") as f:
                json.dump(dex_data, f, indent=2)

            logger.info(f"Saved {len(self._dexes)} DEXes to {storage_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving DEXes to {storage_path}: {e}")
            return False


async def create_dex_repository(
    config: Optional[Dict[str, Any]] = None,
) -> DEXRepository:
    """
    Create and initialize a DEX repository.

    Args:
        config: Configuration dictionary

    Returns:
        Initialized DEX repository
    """
    repository = DEXRepository(config)
    await repository.initialize()
    return repository
