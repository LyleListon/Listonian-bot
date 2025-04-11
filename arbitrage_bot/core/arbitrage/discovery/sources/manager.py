"""
DEX Discovery Manager

This module provides a manager for coordinating DEX discovery sources and repository.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set, Tuple

from .base import DEXSource, DEXInfo, DEXProtocolType
from .repository import DEXRepository
from .validator import DEXValidator
from .defillama import DefiLlamaSource
from .dexscreener import DexScreenerSource
from .defipulse import DefiPulseSource

logger = logging.getLogger(__name__)


class DEXDiscoveryManager:
    """
    Manager for DEX discovery.

    This class coordinates multiple DEX sources and a repository to discover,
    validate, and store DEX information.
    """

    def __init__(
        self,
        web3_manager: Any,
        repository: DEXRepository,
        validator: DEXValidator,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the DEX discovery manager.

        Args:
            web3_manager: Web3 manager for blockchain interactions
            repository: DEX repository
            validator: DEX validator
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        self.repository = repository
        self.validator = validator
        self.config = config or {}

        self._sources: Dict[str, DEXSource] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._discovery_task: Optional[asyncio.Task] = None

        # Discovery configuration
        self._discovery_interval = self.config.get(
            "discovery_interval_seconds", 3600
        )  # 1 hour
        self._auto_validate = self.config.get("auto_validate", True)
        self._chain_id = self.config.get("chain_id", 8453)  # Base chain ID

    async def initialize(self) -> bool:
        """
        Initialize the DEX discovery manager.

        Returns:
            True if initialization was successful, False otherwise
        """
        async with self._lock:
            if self._initialized:
                return True

            logger.info("Initializing DEX discovery manager")

            # Initialize repository
            if not await self.repository.initialize():
                logger.error("Failed to initialize DEX repository")
                return False

            # Initialize validator
            if not await self.validator.initialize():
                logger.error("Failed to initialize DEX validator")
                return False

            # Create and initialize sources
            await self._create_sources()

            self._initialized = True
            logger.info("DEX discovery manager initialized")
            return True

    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            # Stop discovery task
            if self._discovery_task and not self._discovery_task.done():
                self._discovery_task.cancel()
                try:
                    await self._discovery_task
                except asyncio.CancelledError:
                    pass

            # Clean up sources
            for source in self._sources.values():
                await source.cleanup()

            # Clean up repository
            await self.repository.cleanup()

            # Clean up validator
            await self.validator.cleanup()

            self._initialized = False

    async def start_discovery(self) -> None:
        """Start periodic discovery."""
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            if self._discovery_task and not self._discovery_task.done():
                logger.warning("Discovery task already running")
                return

            self._discovery_task = asyncio.create_task(self._discovery_loop())
            logger.info("Started DEX discovery task")

    async def stop_discovery(self) -> None:
        """Stop periodic discovery."""
        async with self._lock:
            if self._discovery_task and not self._discovery_task.done():
                self._discovery_task.cancel()
                try:
                    await self._discovery_task
                except asyncio.CancelledError:
                    pass

                self._discovery_task = None
                logger.info("Stopped DEX discovery task")

    async def discover_dexes(self, chain_id: Optional[int] = None) -> List[DEXInfo]:
        """
        Discover DEXes from all sources.

        Args:
            chain_id: Optional chain ID to filter by

        Returns:
            List of discovered DEXes
        """
        if not self._initialized:
            await self.initialize()

        chain_id = chain_id or self._chain_id
        all_dexes = []

        # Discover from each source
        for source_name, source in self._sources.items():
            try:
                logger.info(f"Discovering DEXes from {source_name}")
                dexes = await source.fetch_dexes(chain_id)
                logger.info(f"Discovered {len(dexes)} DEXes from {source_name}")
                all_dexes.extend(dexes)
            except Exception as e:
                logger.error(f"Error discovering DEXes from {source_name}: {e}")

        # Validate if auto-validate is enabled
        if self._auto_validate:
            validated_dexes = []

            for dex in all_dexes:
                try:
                    is_valid, errors = await self.validator.validate_dex(dex)
                    dex.validated = is_valid
                    dex.validation_errors = errors

                    if is_valid:
                        validated_dexes.append(dex)
                    else:
                        logger.warning(f"DEX {dex.name} failed validation: {errors}")
                except Exception as e:
                    logger.error(f"Error validating DEX {dex.name}: {e}")

            all_dexes = validated_dexes

        # Add to repository
        added_count = await self.repository.add_dexes(all_dexes)
        logger.info(f"Added {added_count} new DEXes to repository")

        return all_dexes

    async def get_dexes(self, chain_id: Optional[int] = None) -> List[DEXInfo]:
        """
        Get DEXes from repository.

        Args:
            chain_id: Optional chain ID to filter by

        Returns:
            List of DEXes
        """
        if not self._initialized:
            await self.initialize()

        chain_id = chain_id or self._chain_id
        return await self.repository.get_dexes_by_chain(chain_id)

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

        return await self.repository.get_dex(name)

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

        return await self.repository.get_dex_by_address(factory_address)

    async def validate_dex(self, dex_info: DEXInfo) -> Tuple[bool, List[str]]:
        """
        Validate a DEX.

        Args:
            dex_info: DEX information

        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not self._initialized:
            await self.initialize()

        return await self.validator.validate_dex(dex_info)

    async def _create_sources(self) -> None:
        """Create and initialize DEX sources."""
        # Create DeFiLlama source
        defillama_config = self.config.get("defillama", {})
        defillama_source = DefiLlamaSource(defillama_config)
        await defillama_source.initialize()
        self._sources["defillama"] = defillama_source

        # Create DexScreener source
        dexscreener_config = self.config.get("dexscreener", {})
        dexscreener_source = DexScreenerSource(dexscreener_config)
        await dexscreener_source.initialize()
        self._sources["dexscreener"] = dexscreener_source

        # Create DefiPulse source
        defipulse_config = self.config.get("defipulse", {})
        defipulse_source = DefiPulseSource(defipulse_config)
        await defipulse_source.initialize()
        self._sources["defipulse"] = defipulse_source

    async def _discovery_loop(self) -> None:
        """Background task for periodic discovery."""
        logger.info("Starting DEX discovery loop")

        while True:
            try:
                # Discover DEXes
                await self.discover_dexes()

                # Sleep until next discovery
                logger.info(f"Next discovery in {self._discovery_interval} seconds")
                await asyncio.sleep(self._discovery_interval)

            except asyncio.CancelledError:
                logger.info("DEX discovery loop cancelled")
                break

            except Exception as e:
                logger.error(f"Error in DEX discovery loop: {e}")
                await asyncio.sleep(60)  # Sleep for a minute before retrying


async def create_dex_discovery_manager(
    web3_manager: Any, config: Optional[Dict[str, Any]] = None
) -> DEXDiscoveryManager:
    """
    Create and initialize a DEX discovery manager.

    Args:
        web3_manager: Web3 manager for blockchain interactions
        config: Configuration dictionary

    Returns:
        Initialized DEX discovery manager
    """
    from .repository import create_dex_repository
    from .validator import create_dex_validator

    # Create repository
    repository = await create_dex_repository(config)

    # Create validator
    validator = await create_dex_validator(web3_manager, config)

    # Create manager
    manager = DEXDiscoveryManager(web3_manager, repository, validator, config)
    await manager.initialize()

    return manager
