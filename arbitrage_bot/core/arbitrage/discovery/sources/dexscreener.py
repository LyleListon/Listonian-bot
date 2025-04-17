"""
DexScreener Source

This module provides a DEX source that fetches information from DexScreener.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set

import aiohttp
from eth_utils import to_checksum_address

from .base import DEXSource, DEXInfo, DEXProtocolType

logger = logging.getLogger(__name__)


class DexScreenerSource(DEXSource):
    """
    DexScreener DEX source.

    This class fetches DEX information from DexScreener's API.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the DexScreener source.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # API configuration
        self._base_url = self.config.get(
            "base_url", "https://api.dexscreener.com/latest"
        )
        self._dexes_endpoint = self.config.get("dexes_endpoint", "/dexs/list/all")
        self._pairs_endpoint = self.config.get("pairs_endpoint", "/pairs")

        # Cache configuration
        self._cache_ttl = self.config.get("cache_ttl", 3600)  # 1 hour
        self._last_fetch = 0
        self._cached_dexes: List[DEXInfo] = []

        # Chain ID mapping (DexScreener chain name -> chain ID)
        self._chain_id_mapping = {
            "ethereum": 1,
            "base": 8453,
            "optimism": 10,
            "arbitrum": 42161,
            "polygon": 137,
            "bsc": 56,
            "avalanche": 43114,
            "fantom": 250,
            "gnosis": 100,
            "celo": 42220,
            "harmony": 1666600000,
            "moonbeam": 1284,
            "moonriver": 1285,
            "metis": 1088,
            "cronos": 25,
            "aurora": 1313161554,
            "boba": 288,
            "evmos": 9001,
            "kava": 2222,
            "klaytn": 8217,
            "okexchain": 66,
            "heco": 128,
            "fuse": 122,
            "telos": 40,
            "canto": 7700,
            "mantle": 5000,
            "linea": 59144,
            "scroll": 534352,
            "zksync": 324,
            "polygonzkevm": 1101,
            "blast": 81457,
        }

        # Protocol type mapping (DexScreener dex name -> DEXProtocolType)
        self._protocol_type_mapping = {
            "uniswap": DEXProtocolType.UNISWAP_V2,
            "uniswap-v2": DEXProtocolType.UNISWAP_V2,
            "uniswap-v3": DEXProtocolType.UNISWAP_V3,
            "sushiswap": DEXProtocolType.UNISWAP_V2,
            "pancakeswap": DEXProtocolType.UNISWAP_V2,
            "pancakeswap-v3": DEXProtocolType.UNISWAP_V3,
            "quickswap": DEXProtocolType.UNISWAP_V2,
            "quickswap-v3": DEXProtocolType.UNISWAP_V3,
            "spookyswap": DEXProtocolType.UNISWAP_V2,
            "spiritswap": DEXProtocolType.UNISWAP_V2,
            "trader-joe": DEXProtocolType.UNISWAP_V2,
            "trader-joe-v2": DEXProtocolType.UNISWAP_V3,
            "baseswap": DEXProtocolType.UNISWAP_V2,
            "baseswap-v3": DEXProtocolType.UNISWAP_V3,
            "aerodrome": DEXProtocolType.UNISWAP_V2,
            "aerodrome-v3": DEXProtocolType.UNISWAP_V3,
            "balancer": DEXProtocolType.BALANCER,
            "curve": DEXProtocolType.CURVE,
            "dodo": DEXProtocolType.CUSTOM,
            "kyberswap": DEXProtocolType.UNISWAP_V2,
            "kyberswap-elastic": DEXProtocolType.UNISWAP_V3,
        }

        # Session for API requests
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> bool:
        """
        Initialize the DexScreener source.

        Returns:
            True if initialization was successful, False otherwise
        """
        async with self._lock:
            if self._initialized:
                return True

            logger.info("Initializing DexScreener source")

            # Create session
            self._session = aiohttp.ClientSession()

            self._initialized = True
            logger.info("DexScreener source initialized")
            return True

    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            if self._session:
                await self._session.close()
                self._session = None

            self._initialized = False

    async def fetch_dexes(self, chain_id: Optional[int] = None) -> List[DEXInfo]:
        """
        Fetch DEX information from DexScreener.

        Args:
            chain_id: Optional chain ID to filter by

        Returns:
            List of DEX information
        """
        if not self._initialized:
            await self.initialize()

        # Check cache
        now = time.time()
        if now - self._last_fetch < self._cache_ttl and self._cached_dexes:
            logger.debug("Using cached DEX information from DexScreener")

            if chain_id:
                return [dex for dex in self._cached_dexes if dex.chain_id == chain_id]

            return self._cached_dexes

        async with self._lock:
            try:
                # Fetch DEXes
                dexes = await self._fetch_dexes()

                # Process DEXes
                dex_infos = await self._process_dexes(dexes)

                # Update cache
                self._cached_dexes = dex_infos
                self._last_fetch = now

                # Filter by chain ID if provided
                if chain_id:
                    return [dex for dex in dex_infos if dex.chain_id == chain_id]

                return dex_infos

            except Exception as e:
                logger.error(f"Error fetching DEX information from DexScreener: {e}")
                return []

    async def _fetch_dexes(self) -> List[Dict[str, Any]]:
        """
        Fetch DEX information from DexScreener.

        Returns:
            List of DEX information
        """
        if not self._session:
            raise RuntimeError("Session not initialized")

        url = f"{self._base_url}{self._dexes_endpoint}"

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.error(
                        f"Error fetching DEXes from DexScreener: {response.status}"
                    )
                    return []

                data = await response.json()
                return data.get("dexs", [])

        except Exception as e:
            logger.error(f"Error fetching DEXes from DexScreener: {e}")
            return []

    async def _fetch_top_pairs(self, chain: str, dex: str) -> List[Dict[str, Any]]:
        """
        Fetch top pairs for a DEX on a specific chain.

        Args:
            chain: Chain name
            dex: DEX name

        Returns:
            List of pair information
        """
        if not self._session:
            raise RuntimeError("Session not initialized")

        url = f"{self._base_url}{self._pairs_endpoint}/{chain}/{dex}"

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.error(
                        f"Error fetching pairs from DexScreener: {response.status}"
                    )
                    return []

                data = await response.json()
                return data.get("pairs", [])

        except Exception as e:
            logger.error(f"Error fetching pairs from DexScreener: {e}")
            return []

    async def _process_dexes(self, dexes: List[Dict[str, Any]]) -> List[DEXInfo]:
        """
        Process DEX information from DexScreener.

        Args:
            dexes: DEX information

        Returns:
            List of DEX information
        """
        result = []

        for dex_data in dexes:
            try:
                dex_name = dex_data.get("name", "")
                chains = dex_data.get("chains", [])

                for chain in chains:
                    # Skip if chain not in mapping
                    if chain not in self._chain_id_mapping:
                        continue

                    chain_id = self._chain_id_mapping[chain]

                    # Determine protocol type
                    protocol_type = self._determine_protocol_type(dex_name)

                    # Fetch top pairs to get contract addresses
                    pairs = await self._fetch_top_pairs(chain, dex_name)

                    if not pairs:
                        continue

                    # Extract addresses from pairs
                    addresses = self._extract_addresses(pairs)

                    if not addresses:
                        continue

                    # Create DEX info
                    dex_info = DEXInfo(
                        name=f"{dex_name}_{chain}",
                        protocol_type=protocol_type,
                        version=self._determine_version(dex_name),
                        chain_id=chain_id,
                        factory_address=addresses.get(
                            "factory", "0x0000000000000000000000000000000000000000"
                        ),
                        router_address=addresses.get(
                            "router", "0x0000000000000000000000000000000000000000"
                        ),
                        quoter_address=addresses.get("quoter"),
                        fee_tiers=self._determine_fee_tiers(protocol_type),
                        tvl_usd=dex_data.get("liquidity", {}).get("usd", 0),
                        volume_24h_usd=dex_data.get("volume", {}).get("h24", 0),
                        source="dexscreener",
                        metadata={
                            "url": dex_data.get("url", ""),
                            "logo": dex_data.get("logo", ""),
                            "chains": chains,
                            "pairs_count": len(pairs),
                            "top_pairs": [p.get("pairAddress") for p in pairs[:5]],
                        },
                    )

                    result.append(dex_info)

            except Exception as e:
                logger.error(f"Error processing DEX {dex_data.get('name', '')}: {e}")

        logger.info(f"Processed {len(result)} DEXes from DexScreener")
        return result

    def _extract_addresses(self, pairs: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extract contract addresses from pairs.

        Args:
            pairs: Pair information

        Returns:
            Dictionary of contract addresses
        """
        addresses = {}

        for pair in pairs:
            # Extract factory address
            if "factory" in pair and not addresses.get("factory"):
                try:
                    addresses["factory"] = to_checksum_address(
                        pair["factory"]["address"]
                    )
                except Exception:
                    pass

            # Extract router address
            if "router" in pair and not addresses.get("router"):
                try:
                    addresses["router"] = to_checksum_address(pair["router"]["address"])
                except Exception:
                    pass

        return addresses

    def _determine_protocol_type(self, dex_name: str) -> DEXProtocolType:
        """
        Determine protocol type from DEX name.

        Args:
            dex_name: DEX name

        Returns:
            Protocol type
        """
        # Check if name is in mapping
        if dex_name in self._protocol_type_mapping:
            return self._protocol_type_mapping[dex_name]

        # Check for specific patterns
        dex_name_lower = dex_name.lower()

        if "uniswap" in dex_name_lower and "v3" in dex_name_lower:
            return DEXProtocolType.UNISWAP_V3
        elif "uniswap" in dex_name_lower:
            return DEXProtocolType.UNISWAP_V2
        elif "sushi" in dex_name_lower:
            return DEXProtocolType.UNISWAP_V2
        elif "curve" in dex_name_lower:
            return DEXProtocolType.CURVE
        elif "balancer" in dex_name_lower:
            return DEXProtocolType.BALANCER

        # Default to unknown
        return DEXProtocolType.UNKNOWN

    def _determine_version(self, dex_name: str) -> str:
        """
        Determine protocol version from DEX name.

        Args:
            dex_name: DEX name

        Returns:
            Protocol version
        """
        dex_name_lower = dex_name.lower()

        if "v3" in dex_name_lower:
            return "v3"
        elif "v2" in dex_name_lower:
            return "v2"
        elif "v1" in dex_name_lower:
            return "v1"

        # Default to v1
        return "v1"

    def _determine_fee_tiers(self, protocol_type: DEXProtocolType) -> List[int]:
        """
        Determine fee tiers based on protocol type.

        Args:
            protocol_type: Protocol type

        Returns:
            List of fee tiers
        """
        if protocol_type == DEXProtocolType.UNISWAP_V3:
            return [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
        elif protocol_type == DEXProtocolType.UNISWAP_V2:
            return [3000]  # 0.3%
        elif protocol_type == DEXProtocolType.BALANCER:
            return [100, 500, 1000, 3000]  # 0.01%, 0.05%, 0.1%, 0.3%
        elif protocol_type == DEXProtocolType.CURVE:
            return [400]  # 0.04%

        # Default to 0.3%
        return [3000]


async def create_dexscreener_source(
    config: Optional[Dict[str, Any]] = None,
) -> DexScreenerSource:
    """
    Create and initialize a DexScreener source.

    Args:
        config: Configuration dictionary

    Returns:
        Initialized DexScreener source
    """
    source = DexScreenerSource(config)
    await source.initialize()
    return source
