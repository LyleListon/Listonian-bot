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
from ..web3.interfaces import Web3Client, ContractWrapper

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
        fee_tiers: List[int],
        version: str = 'v2'
    ):
        """
        Initialize DEX info.

        Args:
            name: DEX name
            factory_address: Factory contract address
            router_address: Router contract address
            fee_tiers: List of fee tiers (in basis points)
            version: DEX version ('v2' or 'v3')
        """
        self.name = name
        self.factory_address = to_checksum_address(factory_address)
        self.router_address = to_checksum_address(router_address)
        self.fee_tiers = fee_tiers
        self.pools: Set[ChecksumAddress] = set()
        self.version = version

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

    @classmethod
    async def create(
        cls,
        web3_manager: Web3Client,
        config: Dict[str, Any]
    ) -> 'DexManager':
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
                fee_tiers=dex_config.get('fee_tiers', [30, 100, 500, 3000, 10000]),
                version=dex_config.get('version', 'v2')
            )

        return cls(web3_manager=web3_manager, dexes=dexes)

    async def discover_pools_aerodrome(
        self,
        factory_contract: ContractWrapper,
        dex: DexInfo,
        token_addresses: Optional[List[ChecksumAddress]] = None
    ) -> Set[ChecksumAddress]:
        """
        Discover pools for Aerodrome style DEX.

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
                        # Try both stable and volatile pools
                        for stable in [True, False]:
                            try:
                                pool = await factory_contract.functions.getPool(
                                    token0,
                                    token1,
                                    stable
                                ).call()

                                if pool != "0x0000000000000000000000000000000000000000":
                                    dex.pools.add(to_checksum_address(pool))

                            except Exception as e:
                                logger.debug(
                                    f"Failed to get pool for {token0}/{token1} (stable={stable}): {e}"
                                )

        return dex.pools

    async def discover_pools_v2(
        self,
        factory_contract: ContractWrapper,
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
        factory_contract: ContractWrapper,
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

    @with_retry(max_attempts=3, base_delay=1.0)
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
            factory_contract = self.web3_manager.contract(
                address=dex.factory_address,
                abi=dex.factory_abi
            )

            # Check DEX type based on version and name
            if dex.name == 'aerodrome':
                return await self.discover_pools_aerodrome(
                    factory_contract,
                    dex,
                    token_addresses
                )
            elif dex.version == 'v3' or dex.name == 'swapbased':  # swapbased uses v3 style despite config
                return await self.discover_pools_v3(
                    factory_contract,
                    dex,
                    token_addresses
                )
            else:  # v2 style
                return await self.discover_pools_v2(
                    factory_contract,
                    dex,
                    token_addresses
                )

        except Exception as e:
            logger.warning(f"Failed to discover pools for {dex_name}: {e}")
            return set()

    @with_retry(max_attempts=3, base_delay=1.0)
    async def get_price(
        self,
        dex_name: str,
        token_in: ChecksumAddress,
        token_out: ChecksumAddress,
        amount_in: int
    ) -> int:
        """
        Get output amount for token swap.

        Args:
            dex_name: DEX name
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in wei

        Returns:
            Output amount in wei
        """
        try:
            dex = self.dexes[dex_name]
            pool = await self.get_pool(dex_name, token_in, token_out)
            
            if not pool:
                return 0

            pool_contract = self.web3_manager.contract(
                address=pool,
                abi=dex.pool_abi
            )

            # Try V3 style first
            try:
                slot0 = await pool_contract.functions.slot0().call()
                sqrtPriceX96 = slot0[0]
                amount_out = amount_in * sqrtPriceX96 * sqrtPriceX96 // (2**192)
                return amount_out
            except Exception:
                # Try V2 style
                try:
                    reserves = await pool_contract.functions.getReserves().call()
                    reserve_in = reserves[0] if token_in < token_out else reserves[1]
                    reserve_out = reserves[1] if token_in < token_out else reserves[0]
                    
                    # Using constant product formula: dy = y * dx / (x + dx)
                    amount_out = (amount_in * reserve_out) // (reserve_in + amount_in)
                    return amount_out
                except Exception as e:
                    logger.debug(f"Failed to get price from pool {pool}: {e}")
                    return 0

        except Exception as e:
            logger.debug(f"Failed to get price for {token_in}/{token_out} on {dex_name}: {e}")
            return 0

    @with_retry(max_attempts=3, base_delay=1.0)
    async def get_pool(
        self,
        dex_name: str,
        token_in: ChecksumAddress,
        token_out: ChecksumAddress
    ) -> Optional[ChecksumAddress]:
        """
        Get pool address for token pair.

        Args:
            dex_name: DEX name
            token_in: Input token address
            token_out: Output token address

        Returns:
            Pool address or None if not found
        """
        try:
            dex = self.dexes[dex_name]
            
            # Discover pools if needed
            if not dex.pools:
                await self.discover_pools(dex_name, [token_in, token_out])

            # Find pool with both tokens
            for pool in dex.pools:
                pool_contract = self.web3_manager.contract(
                    address=pool,
                    abi=dex.pool_abi
                )
                
                try:
                    token0 = await pool_contract.functions.token0().call()
                    token1 = await pool_contract.functions.token1().call()
                    
                    if (token0 == token_in and token1 == token_out) or \
                       (token0 == token_out and token1 == token_in):
                        return pool
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Failed to get pool for {token_in}/{token_out} on {dex_name}: {e}")
            return None

    @with_retry(max_attempts=3, base_delay=1.0)
    async def get_fee(
        self,
        dex_name: str,
        pool_address: ChecksumAddress
    ) -> int:
        """Get pool fee in basis points."""
        try:
            dex = self.dexes[dex_name]
            pool_contract = self.web3_manager.contract(
                address=pool_address,
                abi=dex.pool_abi
            )
            
            fee = await pool_contract.functions.fee().call()
            return fee
        except Exception:
            # Default to 30 bps (0.3%) if fee not found
            return 30

    @with_retry(max_attempts=3, base_delay=1.0)
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
                    pool_contract = self.web3_manager.contract(
                        address=pool,
                        abi=dex.pool_abi
                    )

                    # Get token balance
                    balance = await pool_contract.functions.balanceOf(token_address).call()
                    total_liquidity += balance

                except Exception as e:
                    logger.debug(f"Failed to get liquidity for pool {pool}: {e}")

        return total_liquidity

    @with_retry(max_attempts=3, base_delay=1.0)
    async def calculate_price_impact(
        self,
        dex_name: str,
        pool_address: ChecksumAddress,
        amount_in: int
    ) -> float:
        """
        Calculate price impact of swap.

        Args:
            dex_name: DEX name
            pool_address: Pool address
            amount_in: Input amount in wei

        Returns:
            Price impact as decimal (0.01 = 1%)
        """
        try:
            dex = self.dexes[dex_name]
            pool_contract = self.web3_manager.contract(
                address=pool_address,
                abi=dex.pool_abi
            )

            # Try V3 style first
            try:
                liquidity = await pool_contract.functions.liquidity().call()
                impact = amount_in / liquidity
                return min(impact, 1.0)  # Cap at 100%
            except Exception:
                # Try V2 style
                try:
                    reserves = await pool_contract.functions.getReserves().call()
                    impact = amount_in / (reserves[0] + reserves[1])
                    return min(impact, 1.0)  # Cap at 100%
                except Exception as e:
                    logger.debug(f"Failed to calculate price impact for pool {pool_address}: {e}")
                    return 1.0  # Assume 100% impact on failure

        except Exception as e:
            logger.debug(f"Failed to calculate price impact for pool {pool_address}: {e}")
            return 1.0  # Assume 100% impact on failure

    @with_retry(max_attempts=3, base_delay=1.0)
    async def get_supported_tokens(self) -> List[ChecksumAddress]:
        """
        Get list of supported tokens across all DEXs.

        Returns:
            List of token addresses
        """
        tokens = set()

        for dex in self.dexes.values():
            for pool in dex.pools:
                try:
                    pool_contract = self.web3_manager.contract(
                        address=pool,
                        abi=dex.pool_abi
                    )
                    tokens.add(await pool_contract.functions.token0().call())
                    tokens.add(await pool_contract.functions.token1().call())
                except Exception:
                    continue

        return sorted(list(tokens))

    async def close(self):
        """Clean up resources."""
        pass
