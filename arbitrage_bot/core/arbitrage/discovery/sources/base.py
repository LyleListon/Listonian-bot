"""
Base DEX Source

This module defines the base class for DEX sources and common data structures.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set
from eth_utils import to_checksum_address

logger = logging.getLogger(__name__)


class DEXProtocolType(Enum):
    """DEX protocol type enumeration."""
    UNISWAP_V2 = auto()
    UNISWAP_V3 = auto()
    BALANCER = auto()
    CURVE = auto()
    CUSTOM = auto()
    UNKNOWN = auto()


@dataclass
class DEXInfo:
    """
    Information about a DEX.
    
    This class contains all the necessary information to interact with a DEX,
    including contract addresses, protocol type, and metadata.
    """
    
    # Basic information
    name: str
    protocol_type: DEXProtocolType
    version: str
    chain_id: int
    
    # Contract addresses
    factory_address: str
    router_address: str
    
    # Optional addresses
    quoter_address: Optional[str] = None
    
    # Fee information
    fee_tiers: List[int] = field(default_factory=list)
    default_fee: int = 30  # 0.3%
    
    # Metadata
    tvl_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    last_updated: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    
    # Validation
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize addresses."""
        # Convert addresses to checksum format
        self.factory_address = to_checksum_address(self.factory_address)
        self.router_address = to_checksum_address(self.router_address)
        
        if self.quoter_address:
            self.quoter_address = to_checksum_address(self.quoter_address)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "protocol_type": self.protocol_type.name,
            "version": self.version,
            "chain_id": self.chain_id,
            "factory_address": self.factory_address,
            "router_address": self.router_address,
            "quoter_address": self.quoter_address,
            "fee_tiers": self.fee_tiers,
            "default_fee": self.default_fee,
            "tvl_usd": self.tvl_usd,
            "volume_24h_usd": self.volume_24h_usd,
            "last_updated": self.last_updated.isoformat(),
            "source": self.source,
            "validated": self.validated,
            "validation_errors": self.validation_errors,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DEXInfo':
        """Create from dictionary."""
        # Convert protocol_type from string to enum
        if isinstance(data.get("protocol_type"), str):
            data["protocol_type"] = DEXProtocolType[data["protocol_type"]]
        
        # Convert last_updated from string to datetime
        if isinstance(data.get("last_updated"), str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        
        return cls(**data)


class DEXSource(ABC):
    """
    Base class for DEX sources.
    
    A DEX source is responsible for fetching DEX information from a specific
    source, such as a community-maintained list or an API.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the DEX source.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._lock = asyncio.Lock()
        self._initialized = False
    
    @abstractmethod
    async def fetch_dexes(self, chain_id: Optional[int] = None) -> List[DEXInfo]:
        """
        Fetch DEX information from the source.
        
        Args:
            chain_id: Optional chain ID to filter by
            
        Returns:
            List of DEX information
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the DEX source.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass