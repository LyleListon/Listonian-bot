"""
DEX Manager Module

This module provides functionality for:
- DEX interactions
- Pool discovery
- Price fetching
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Set
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address

from ...utils.async_manager import with_retry
from ..web3.interfaces import Web3Client

logger = logging.getLogger(__name__)

def load_abi(filename: str) -> Optional[Dict[str, Any]]:
    """
    Load ABI from file.

    Args:
        filename: ABI filename

    Returns:
        ABI dictionary or None if file not found
    """
    try:
        with open(os.path.join('abi', filename), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.debug(f"ABI file not found: {filename}")
        return None

def get_dex_abi(name: str, contract_type: str) -> Optional[Dict[str, Any]]:
    """
    Get DEX ABI by trying different naming patterns.

    Args:
        name: DEX name
        contract_type: Contract type (factory, pool, router)

    Returns:
        ABI dictionary or None if not found
    """
    # Try different naming patterns
    patterns = [
        f"{name}_{contract_type}.json",  # baseswap_pool.json
        f"{name}_v3_{contract_type}.json",  # baseswap_v3_pool.json
        f"{name}_v2_{contract_type}.json",  # baseswap_v2_pool.json
        f"I{name.capitalize()}V3{contract_type.capitalize()}.json",  # IBaseswapV3Pool.json
        f"I{name.capitalize()}V2{contract_type.capitalize()}.json",  # IBaseswapV2Pool.json
        f"I{contract_type.capitalize()}.json"  # IPool.json
    ]

    for pattern in patterns:
        abi = load_abi(pattern)
        if abi:
            return abi

    # Try generic interfaces
    generic_patterns = {
        'factory': ['IUniswapV3Factory.json', 'IUniswapV2Factory.json'],
        'pool': ['IUniswapV3Pool.json', 'IUniswapV2Pair.json'],
        'router': ['IUniswapV3Router.json', 'IUniswapV2Router.json']
    }

    for pattern in generic_patterns.get(contract_type, []):
        abi = load_abi(pattern)
        if abi:
            return abi

    return None

class DexInfo:
    """DEX information container."""

    def __init__(
        self,
        name: str,
        factory_address: str,
        router_address: str,
        fee_tiers: List[int]
    ):
        """
        Initialize DEX info.

        Args:
            name: DEX name
            factory_address: Factory contract address
            router_address: Router contract address
            fee_tiers: List of fee tiers (in basis points)
        """
        self.name = name
        self.factory_address = to_checksum_address(factory_address)
        self.router_address = to_checksum_address(router_address)
        self.fee_tiers = fee_tiers
        self.pools: Set[ChecksumAddress] = set()

        # Load ABIs
        self.factory_abi = get_dex_abi(name, 'factory')
        self.pool_abi = get_dex_abi(name, 'pool')

        if not self.factory_abi:
            logger.warning(f"No factory ABI found for {name}")
        if not self.pool_abi:
            logger.warning(f"No pool ABI found for {name}")

class DexManager:
    """Manages DEX interactions."""

    def __init__(
        self,
        web3_manager: Web3Client,
        dexes: Dict[str, DexInfo]
    ):
        """
        Initialize DEX manager.

        Args:
            web3_manager: Web3 client instance
            dexes: Dictionary of DEX info objects
        """
        self.web3_manager = web3_manager
        self.dexes = dexes

        logger.info(
            f"DEX manager initialized with {len(dexes)} DEXs: "
            f"{', '.join(dexes.keys())}"
        )

    async def discover_pools_v2(
        self,
        factory_contract: Any,
        dex: DexInfo,
        token_addresses: Optional[List[ChecksumAddress]] = None
    ) -> Set[ChecksumAddress]:
        """
        Discover pools for Uniswap V2 style DEX.

        Args:
            factory_contract: Factory contract instance
            dex: DEX info instance
            token_addresses: Optional list of token addresses to filter by

        Returns:
            Set of pool addresses
        """
        if token_addresses:
            # Filter by tokens
            for token0 in token_addresses:
                for token1 in token_addresses:
                    if token0 != token1:
                        try:
                            pool = await factory_contract.functions.getPair(
                                token0,
                                token1
                            ).call()

                            if pool != "0x0000000000000000000000000000000000000000":
                                dex.pools.add(to_checksum_address(pool))

                        except Exception as e:
                            logger.debug(
                                f"Failed to get pair for {token0}/{token1}: {e}"
                            )
        else:
            # Get all pools
            try:
                pool_count = await factory_contract.functions.allPairsLength().call()

                for i in range(pool_count):
                    try:
                        pool = await factory_contract.functions.allPairs(i).call()
                        dex.pools.add(to_checksum_address(pool))

                    except Exception as e:
                        logger.debug(f"Failed to get pair {i}: {e}")

            except Exception as e:
                logger.debug(f"Failed to get pair count: {e}")

        return dex.pools

    async def discover_pools_v3(
        self,
        factory_contract: Any,
        dex: DexInfo,
        token_addresses: Optional[List[ChecksumAddress]] = None
    ) -> Set[ChecksumAddress]:
        """
        Discover pools for Uniswap V3 style DEX.

        Args:
            factory_contract: Factory contract instance
            dex: DEX info instance
            token_addresses: Optional list of token addresses to filter by

        Returns:
            Set of pool addresses
        """
        if token_addresses:
            # Filter by tokens
            for token0 in token_addresses:
                for token1 in token_addresses:
                    if token0 != token1:
                        for fee in dex.fee_tiers:
                            try:
                                pool = await factory_contract.functions.getPool(
                                    token0,
                                    token1,
                                    fee
                                ).call()

                                if pool != "0x0000000000000000000000000000000000000000":
                                    dex.pools.add(to_checksum_address(pool))

                            except Exception as e:
                                logger.debug(
                                    f"Failed to get pool for {token0}/{token1}: {e}"
                                )
        else:
            # Get all pools
            try:
                pool_count = await factory_contract.functions.allPoolsLength().call()

                for i in range(pool_count):
                    try:
                        pool = await factory_contract.functions.allPools(i).call()
                        dex.pools.add(to_checksum_address(pool))

                    except Exception as e:
                        logger.debug(f"Failed to get pool {i}: {e}")

            except Exception as e:
                logger.debug(f"Failed to get pool count: {e}")

        return dex.pools

    @with_retry(retries=3, delay=1.0)
    async def discover_pools(
        self,
        dex_name: str,
        token_addresses: Optional[List[ChecksumAddress]] = None
    ) -> Set[ChecksumAddress]:
        """
        Discover pools for DEX.

        Args:
            dex_name: DEX name
            token_addresses: Optional list of token addresses to filter by

        Returns:
            Set of pool addresses

        Raises:
            ValueError: If DEX not found
        """
        try:
            if dex_name not in self.dexes:
                raise ValueError(f"DEX not found: {dex_name}")

            dex = self.dexes[dex_name]

            if not dex.factory_abi:
                logger.warning(f"No factory ABI for {dex_name}, skipping pool discovery")
                return set()

            # Create factory contract
            factory_contract = self.web3_manager.w3.eth.contract(
                address=dex.factory_address,
                abi=dex.factory_abi
            )

            # Try V3 style first
            try:
                await factory_contract.functions.getPool(
                    "0x0000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000000",
                    3000
                ).call()
                return await self.discover_pools_v3(
                    factory_contract,
                    dex,
                    token_addresses
                )
            except Exception:
                # Try V2 style
                try:
                    await factory_contract.functions.getPair(
                        "0x0000000000000000000000000000000000000000",
                        "0x0000000000000000000000000000000000000000"
                    ).call()
                    return await self.discover_pools_v2(
                        factory_contract,
                        dex,
                        token_addresses
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to discover pools for {dex_name}: {e}"
                    )
                    return set()

        except Exception as e:
            logger.warning(f"Failed to discover pools for {dex_name}: {e}")
            return set()

    @with_retry(retries=3, delay=1.0)
    async def get_pool_liquidity(
        self,
        token_address: ChecksumAddress
    ) -> int:
        """
        Get total liquidity for token across all pools.

        Args:
            token_address: Token address

        Returns:
            Total liquidity in wei
        """
        total_liquidity = 0

        for dex in self.dexes.values():
            if not dex.pool_abi:
                logger.debug(f"No pool ABI for {dex.name}, skipping liquidity check")
                continue

            for pool in dex.pools:
                try:
                    # Create pool contract
                    pool_contract = self.web3_manager.w3.eth.contract(
                        address=pool,
                        abi=dex.pool_abi
                    )

                    # Get token balance
                    balance = await pool_contract.functions.balanceOf(token_address).call()
                    total_liquidity += balance

                except Exception as e:
                    logger.debug(f"Failed to get liquidity for pool {pool}: {e}")

        return total_liquidity

    async def close(self):
        """Clean up resources."""
        pass

async def create_dex_manager(
    web3_manager: Web3Client,
    config: Dict[str, Any]
) -> DexManager:
    """
    Create a new DEX manager.

    Args:
        web3_manager: Web3 client instance
        config: Configuration dictionary

    Returns:
        DexManager instance
    """
    dexes = {}

    for name, dex_config in config['dexes'].items():
        dexes[name] = DexInfo(
            name=name,
            factory_address=dex_config['factory'],
            router_address=dex_config['router'],
            fee_tiers=dex_config.get('fee_tiers', [30, 100, 500, 3000, 10000])
        )

    return DexManager(
        web3_manager=web3_manager,
        dexes=dexes
    )
