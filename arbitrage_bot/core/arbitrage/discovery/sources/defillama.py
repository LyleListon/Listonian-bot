"""
DeFiLlama Source

This module provides a DEX source that fetches information from DeFiLlama.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set

import aiohttp
from eth_utils import to_checksum_address

from .base import DEXSource, DEXInfo, DEXProtocolType

logger = logging.getLogger(__name__)


class DefiLlamaSource(DEXSource):
    """
    DeFiLlama DEX source.

    This class fetches DEX information from DeFiLlama's API.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the DeFiLlama source.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)

        # API configuration
        self._base_url = self.config.get("base_url", "https://api.llama.fi")
        self._protocols_endpoint = self.config.get("protocols_endpoint", "/protocols")
        self._dexes_endpoint = self.config.get("dexes_endpoint", "/dexs")

        # Cache configuration
        self._cache_ttl = self.config.get("cache_ttl", 3600)  # 1 hour
        self._last_fetch = 0
        self._cached_dexes: List[DEXInfo] = []

        # Chain ID mapping (DeFiLlama chain name -> chain ID)
        self._chain_id_mapping = {
            "Ethereum": 1,
            "Base": 8453,
            "Optimism": 10,
            "Arbitrum": 42161,
            "Polygon": 137,
            "BSC": 56,
            "Avalanche": 43114,
            "Fantom": 250,
            "Gnosis": 100,
            "Celo": 42220,
            "Harmony": 1666600000,
            "Moonbeam": 1284,
            "Moonriver": 1285,
            "Metis": 1088,
            "Cronos": 25,
            "Aurora": 1313161554,
            "Boba": 288,
            "Evmos": 9001,
            "Kava": 2222,
            "Klaytn": 8217,
            "OKExChain": 66,
            "Heco": 128,
            "Fuse": 122,
            "Telos": 40,
            "Canto": 7700,
            "Mantle": 5000,
            "Linea": 59144,
            "Scroll": 534352,
            "zkSync Era": 324,
            "Polygon zkEVM": 1101,
            "Blast": 81457,
        }

        # Protocol type mapping (DeFiLlama category -> DEXProtocolType)
        self._protocol_type_mapping = {
            "Dexes": DEXProtocolType.UNISWAP_V2,  # Default to Uniswap V2
            "Dexes - AMM": DEXProtocolType.UNISWAP_V2,
            "Dexes - Orderbook": DEXProtocolType.CUSTOM,
            "Dexes - Aggregator": DEXProtocolType.CUSTOM,
            "Dexes - Derivatives": DEXProtocolType.CUSTOM,
            "Dexes - Stableswap": DEXProtocolType.CURVE,
            "Dexes - Concentrated Liquidity": DEXProtocolType.UNISWAP_V3,
            "Dexes - Balancer": DEXProtocolType.BALANCER,
            "Dexes - Curve": DEXProtocolType.CURVE,
        }

        # Session for API requests
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> bool:
        """
        Initialize the DeFiLlama source.

        Returns:
            True if initialization was successful, False otherwise
        """
        async with self._lock:
            if self._initialized:
                return True

            logger.info("Initializing DeFiLlama source")

            # Create session
            self._session = aiohttp.ClientSession()

            self._initialized = True
            logger.info("DeFiLlama source initialized")
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
        Fetch DEX information from DeFiLlama.

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
            logger.debug("Using cached DEX information from DeFiLlama")

            if chain_id:
                return [dex for dex in self._cached_dexes if dex.chain_id == chain_id]

            return self._cached_dexes

        async with self._lock:
            try:
                # Fetch protocols
                protocols = await self._fetch_protocols()

                # Fetch DEXes
                dexes = await self._fetch_dexes()

                # Combine information
                dex_infos = await self._process_data(protocols, dexes)

                # Update cache
                self._cached_dexes = dex_infos
                self._last_fetch = now

                # Filter by chain ID if provided
                if chain_id:
                    return [dex for dex in dex_infos if dex.chain_id == chain_id]

                return dex_infos

            except Exception as e:
                logger.error(f"Error fetching DEX information from DeFiLlama: {e}")
                return []

    async def _fetch_protocols(self) -> List[Dict[str, Any]]:
        """
        Fetch protocol information from DeFiLlama.

        Returns:
            List of protocol information
        """
        if not self._session:
            raise RuntimeError("Session not initialized")

        url = f"{self._base_url}{self._protocols_endpoint}"

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.error(
                        f"Error fetching protocols from DeFiLlama: {response.status}"
                    )
                    return []

                data = await response.json()
                return data

        except Exception as e:
            logger.error(f"Error fetching protocols from DeFiLlama: {e}")
            return []

    async def _fetch_dexes(self) -> Dict[str, Any]:
        """
        Fetch DEX information from DeFiLlama.

        Returns:
            Dictionary of DEX information
        """
        if not self._session:
            raise RuntimeError("Session not initialized")

        url = f"{self._base_url}{self._dexes_endpoint}"

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.error(
                        f"Error fetching DEXes from DeFiLlama: {response.status}"
                    )
                    return {}

                data = await response.json()
                return data

        except Exception as e:
            logger.error(f"Error fetching DEXes from DeFiLlama: {e}")
            return {}

    async def _process_data(
        self, protocols: List[Dict[str, Any]], dexes: Dict[str, Any]
    ) -> List[DEXInfo]:
        """
        Process data from DeFiLlama.

        Args:
            protocols: Protocol information
            dexes: DEX information

        Returns:
            List of DEX information
        """
        result = []

        # Create mapping of protocol name to protocol data
        protocol_map = {p["name"]: p for p in protocols}

        # Process DEX data
        for dex_name, dex_data in dexes.get("protocols", {}).items():
            try:
                # Get protocol data
                protocol = protocol_map.get(dex_name)

                if not protocol:
                    continue

                # Get chain information
                for chain_name, chain_data in dex_data.get("chains", {}).items():
                    # Skip if chain not in mapping
                    if chain_name not in self._chain_id_mapping:
                        continue

                    chain_id = self._chain_id_mapping[chain_name]

                    # Get addresses from protocol data
                    addresses = self._extract_addresses(protocol, chain_name)

                    if not addresses:
                        continue

                    # Determine protocol type
                    protocol_type = self._determine_protocol_type(protocol)

                    # Create DEX info
                    dex_info = DEXInfo(
                        name=f"{dex_name}_{chain_name}",
                        protocol_type=protocol_type,
                        version=self._determine_version(protocol),
                        chain_id=chain_id,
                        factory_address=addresses.get(
                            "factory", "0x0000000000000000000000000000000000000000"
                        ),
                        router_address=addresses.get(
                            "router", "0x0000000000000000000000000000000000000000"
                        ),
                        quoter_address=addresses.get("quoter"),
                        fee_tiers=self._determine_fee_tiers(protocol_type),
                        tvl_usd=chain_data.get("tvl", 0),
                        volume_24h_usd=chain_data.get("volume", 0),
                        source="defillama",
                        metadata={
                            "url": protocol.get("url", ""),
                            "description": protocol.get("description", ""),
                            "logo": protocol.get("logo", ""),
                            "category": protocol.get("category", ""),
                            "chains": list(protocol.get("chains", [])),
                            "audit_links": protocol.get("audit_links", []),
                            "gecko_id": protocol.get("gecko_id", ""),
                            "twitter": protocol.get("twitter", ""),
                            "github": protocol.get("github", ""),
                            "slug": protocol.get("slug", ""),
                        },
                    )

                    result.append(dex_info)

            except Exception as e:
                logger.error(f"Error processing DEX {dex_name}: {e}")

        logger.info(f"Processed {len(result)} DEXes from DeFiLlama")
        return result

    def _extract_addresses(
        self, protocol: Dict[str, Any], chain_name: str
    ) -> Dict[str, str]:
        """
        Extract contract addresses from protocol data.

        Args:
            protocol: Protocol data
            chain_name: Chain name

        Returns:
            Dictionary of contract addresses
        """
        addresses = {}

        # Check if addresses are available
        if "addresses" not in protocol:
            return addresses

        # Get chain-specific addresses
        chain_addresses = protocol["addresses"].get(chain_name, {})

        if not chain_addresses:
            return addresses

        # Extract factory address
        if "factory" in chain_addresses:
            try:
                addresses["factory"] = to_checksum_address(chain_addresses["factory"])
            except Exception:
                pass

        # Extract router address
        if "router" in chain_addresses:
            try:
                addresses["router"] = to_checksum_address(chain_addresses["router"])
            except Exception:
                pass

        # Extract quoter address
        if "quoter" in chain_addresses:
            try:
                addresses["quoter"] = to_checksum_address(chain_addresses["quoter"])
            except Exception:
                pass

        return addresses

    def _determine_protocol_type(self, protocol: Dict[str, Any]) -> DEXProtocolType:
        """
        Determine protocol type from protocol data.

        Args:
            protocol: Protocol data

        Returns:
            Protocol type
        """
        category = protocol.get("category", "")

        # Check if category is in mapping
        if category in self._protocol_type_mapping:
            return self._protocol_type_mapping[category]

        # Check for specific protocols
        name = protocol.get("name", "").lower()

        if "uniswap" in name and "v3" in name:
            return DEXProtocolType.UNISWAP_V3
        elif "uniswap" in name:
            return DEXProtocolType.UNISWAP_V2
        elif "sushi" in name:
            return DEXProtocolType.UNISWAP_V2
        elif "curve" in name:
            return DEXProtocolType.CURVE
        elif "balancer" in name:
            return DEXProtocolType.BALANCER

        # Default to unknown
        return DEXProtocolType.UNKNOWN

    def _determine_version(self, protocol: Dict[str, Any]) -> str:
        """
        Determine protocol version from protocol data.

        Args:
            protocol: Protocol data

        Returns:
            Protocol version
        """
        name = protocol.get("name", "").lower()

        if "v3" in name:
            return "v3"
        elif "v2" in name:
            return "v2"
        elif "v1" in name:
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


async def create_defillama_source(
    config: Optional[Dict[str, Any]] = None,
) -> DefiLlamaSource:
    """
    Create and initialize a DeFiLlama source.

    Args:
        config: Configuration dictionary

    Returns:
        Initialized DeFiLlama source
    """
    source = DefiLlamaSource(config)
    await source.initialize()
    return source
