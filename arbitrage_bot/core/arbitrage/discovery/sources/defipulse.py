"""
DefiPulse Source

This module provides a DEX source that fetches information from DefiPulse.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set

import aiohttp
from eth_utils import to_checksum_address

from .base import DEXSource, DEXInfo, DEXProtocolType

logger = logging.getLogger(__name__)


class DefiPulseSource(DEXSource):
    """
    DefiPulse DEX source.
    
    This class fetches DEX information from DefiPulse's API.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the DefiPulse source.
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        
        # API configuration
        self._base_url = self.config.get("base_url", "https://data-api.defipulse.com/api/v1")
        self._projects_endpoint = self.config.get("projects_endpoint", "/projects")
        self._api_key = self.config.get("api_key", "")
        
        # Cache configuration
        self._cache_ttl = self.config.get("cache_ttl", 3600)  # 1 hour
        self._last_fetch = 0
        self._cached_dexes: List[DEXInfo] = []
        
        # Chain ID mapping (DefiPulse chain name -> chain ID)
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
            "Blast": 81457
        }
        
        # Protocol type mapping (DefiPulse category -> DEXProtocolType)
        self._protocol_type_mapping = {
            "DEX": DEXProtocolType.UNISWAP_V2,  # Default to Uniswap V2
            "DEX - AMM": DEXProtocolType.UNISWAP_V2,
            "DEX - Orderbook": DEXProtocolType.CUSTOM,
            "DEX - Aggregator": DEXProtocolType.CUSTOM,
            "DEX - Derivatives": DEXProtocolType.CUSTOM,
            "DEX - Stableswap": DEXProtocolType.CURVE,
            "DEX - Concentrated Liquidity": DEXProtocolType.UNISWAP_V3,
            "DEX - Balancer": DEXProtocolType.BALANCER,
            "DEX - Curve": DEXProtocolType.CURVE
        }
        
        # Known DEX addresses (name -> addresses)
        self._known_addresses = {
            "uniswap_v2": {
                "factory": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
                "router": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
            },
            "uniswap_v3": {
                "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
                "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6"
            },
            "sushiswap": {
                "factory": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
                "router": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
            },
            "baseswap": {
                "factory": "0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB",
                "router": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86"
            },
            "aerodrome": {
                "factory": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
                "router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
            }
        }
        
        # Session for API requests
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """
        Initialize the DefiPulse source.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing DefiPulse source")
            
            # Check if API key is provided
            if not self._api_key:
                logger.warning("No API key provided for DefiPulse source")
                # We'll still initialize but won't be able to fetch data
            
            # Create session
            self._session = aiohttp.ClientSession()
            
            self._initialized = True
            logger.info("DefiPulse source initialized")
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
        Fetch DEX information from DefiPulse.
        
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
            logger.debug("Using cached DEX information from DefiPulse")
            
            if chain_id:
                return [dex for dex in self._cached_dexes if dex.chain_id == chain_id]
            
            return self._cached_dexes
        
        async with self._lock:
            try:
                # Check if API key is provided
                if not self._api_key:
                    logger.warning("No API key provided for DefiPulse source, using fallback data")
                    dex_infos = await self._get_fallback_dexes()
                else:
                    # Fetch projects
                    projects = await self._fetch_projects()
                    
                    # Process projects
                    dex_infos = await self._process_projects(projects)
                
                # Update cache
                self._cached_dexes = dex_infos
                self._last_fetch = now
                
                # Filter by chain ID if provided
                if chain_id:
                    return [dex for dex in dex_infos if dex.chain_id == chain_id]
                
                return dex_infos
            
            except Exception as e:
                logger.error(f"Error fetching DEX information from DefiPulse: {e}")
                return []
    
    async def _fetch_projects(self) -> List[Dict[str, Any]]:
        """
        Fetch project information from DefiPulse.
        
        Returns:
            List of project information
        """
        if not self._session:
            raise RuntimeError("Session not initialized")
        
        if not self._api_key:
            return []
        
        url = f"{self._base_url}{self._projects_endpoint}"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        
        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Error fetching projects from DefiPulse: {response.status}")
                    return []
                
                data = await response.json()
                return data
        
        except Exception as e:
            logger.error(f"Error fetching projects from DefiPulse: {e}")
            return []
    
    async def _process_projects(self, projects: List[Dict[str, Any]]) -> List[DEXInfo]:
        """
        Process project information from DefiPulse.
        
        Args:
            projects: Project information
            
        Returns:
            List of DEX information
        """
        result = []
        
        for project in projects:
            try:
                # Skip non-DEX projects
                category = project.get("category", "")
                if not category.startswith("DEX"):
                    continue
                
                name = project.get("name", "")
                chains = project.get("chains", ["Ethereum"])
                
                for chain in chains:
                    # Skip if chain not in mapping
                    if chain not in self._chain_id_mapping:
                        continue
                    
                    chain_id = self._chain_id_mapping[chain]
                    
                    # Determine protocol type
                    protocol_type = self._determine_protocol_type(project)
                    
                    # Get addresses
                    addresses = self._get_addresses(name, chain)
                    
                    if not addresses:
                        continue
                    
                    # Create DEX info
                    dex_info = DEXInfo(
                        name=f"{name}_{chain}",
                        protocol_type=protocol_type,
                        version=self._determine_version(name),
                        chain_id=chain_id,
                        factory_address=addresses.get("factory", "0x0000000000000000000000000000000000000000"),
                        router_address=addresses.get("router", "0x0000000000000000000000000000000000000000"),
                        quoter_address=addresses.get("quoter"),
                        fee_tiers=self._determine_fee_tiers(protocol_type),
                        tvl_usd=project.get("tvl", {}).get("USD", 0),
                        volume_24h_usd=project.get("volume", {}).get("USD", 0),
                        source="defipulse",
                        metadata={
                            "url": project.get("url", ""),
                            "description": project.get("description", ""),
                            "logo": project.get("logo", ""),
                            "category": category,
                            "chains": chains,
                            "twitter": project.get("twitter", ""),
                            "github": project.get("github", ""),
                            "slug": project.get("slug", "")
                        }
                    )
                    
                    result.append(dex_info)
            
            except Exception as e:
                logger.error(f"Error processing project {project.get('name', '')}: {e}")
        
        logger.info(f"Processed {len(result)} DEXes from DefiPulse")
        return result
    
    async def _get_fallback_dexes(self) -> List[DEXInfo]:
        """
        Get fallback DEX information.
        
        Returns:
            List of DEX information
        """
        result = []
        
        # Use known addresses for common DEXes
        for name, addresses in self._known_addresses.items():
            try:
                # Determine protocol type
                protocol_type = DEXProtocolType.UNISWAP_V2
                if "v3" in name:
                    protocol_type = DEXProtocolType.UNISWAP_V3
                elif "balancer" in name:
                    protocol_type = DEXProtocolType.BALANCER
                elif "curve" in name:
                    protocol_type = DEXProtocolType.CURVE
                
                # Determine chain ID
                chain_id = 1  # Default to Ethereum
                if "base" in name:
                    chain_id = 8453
                
                # Create DEX info
                dex_info = DEXInfo(
                    name=name,
                    protocol_type=protocol_type,
                    version=self._determine_version(name),
                    chain_id=chain_id,
                    factory_address=addresses.get("factory", "0x0000000000000000000000000000000000000000"),
                    router_address=addresses.get("router", "0x0000000000000000000000000000000000000000"),
                    quoter_address=addresses.get("quoter"),
                    fee_tiers=self._determine_fee_tiers(protocol_type),
                    source="defipulse_fallback",
                    metadata={
                        "fallback": True
                    }
                )
                
                result.append(dex_info)
            
            except Exception as e:
                logger.error(f"Error creating fallback DEX {name}: {e}")
        
        logger.info(f"Created {len(result)} fallback DEXes")
        return result
    
    def _determine_protocol_type(self, project: Dict[str, Any]) -> DEXProtocolType:
        """
        Determine protocol type from project data.
        
        Args:
            project: Project data
            
        Returns:
            Protocol type
        """
        category = project.get("category", "")
        
        # Check if category is in mapping
        if category in self._protocol_type_mapping:
            return self._protocol_type_mapping[category]
        
        # Check for specific protocols
        name = project.get("name", "").lower()
        
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
    
    def _determine_version(self, name: str) -> str:
        """
        Determine protocol version from name.
        
        Args:
            name: Protocol name
            
        Returns:
            Protocol version
        """
        name_lower = name.lower()
        
        if "v3" in name_lower:
            return "v3"
        elif "v2" in name_lower:
            return "v2"
        elif "v1" in name_lower:
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
    
    def _get_addresses(self, name: str, chain: str) -> Dict[str, str]:
        """
        Get addresses for a DEX on a specific chain.
        
        Args:
            name: DEX name
            chain: Chain name
            
        Returns:
            Dictionary of addresses
        """
        name_lower = name.lower()
        
        # Check for known addresses
        for known_name, addresses in self._known_addresses.items():
            if known_name.lower() in name_lower:
                return addresses
        
        # Default to empty addresses
        return {}


async def create_defipulse_source(config: Optional[Dict[str, Any]] = None) -> DefiPulseSource:
    """
    Create and initialize a DefiPulse source.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized DefiPulse source
    """
    source = DefiPulseSource(config)
    await source.initialize()
    return source