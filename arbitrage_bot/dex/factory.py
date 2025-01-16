"""DEX factory for creating DEX instances."""

import logging
from typing import Dict, Any, Optional
from web3 import Web3

from .base_dex import BaseDEX
from .aerodrome_v2 import AerodromeV2
from .aerodrome_v3 import AerodromeV3
from .swapbased import SwapBased

logger = logging.getLogger(__name__)

class DEXRegistry:
    """Registry of supported DEXes."""
    
    def __init__(self):
        """Initialize DEX registry."""
        self._dexes: Dict[str, BaseDEX] = {}
        
    def register(self, name: str, dex: BaseDEX):
        """Register a DEX instance."""
        self._dexes[name.lower()] = dex
        
    def get(self, name: str) -> Optional[BaseDEX]:
        """Get DEX instance by name."""
        return self._dexes.get(name.lower())
        
    def list_dexes(self) -> list:
        """List registered DEXes."""
        return list(self._dexes.keys())
        
    def clear(self):
        """Clear all registered DEXes."""
        self._dexes.clear()

# Global registry instance
registry = DEXRegistry()

async def create_dex(
    name: str,
    web3: Web3,
    config: Dict[str, Any]
) -> Optional[BaseDEX]:
    """
    Create a DEX instance.
    
    Args:
        name: DEX name (e.g., 'aerodrome')
        web3: Web3 instance
        config: Configuration dictionary
        
    Returns:
        Optional[BaseDEX]: DEX instance if supported, None otherwise
    """
    try:
        # Check if already registered
        if registry.get(name):
            return registry.get(name)
            
        # Create new instance
        dex = None
        name = name.lower()
        
        if name == "aerodrome":
            dex = AerodromeV2(web3, config)
            logger.info("Created Aerodrome V2 DEX instance")
        elif name == "aerodrome_v3":
            dex = AerodromeV3(web3, config)
            logger.info("Created Aerodrome V3 DEX instance")
        elif name == "swapbased":
            dex = SwapBased(web3, config)
            logger.info("Created SwapBased DEX instance")
            
        # Register if created
        if dex:
            registry.register(name, dex)
            return dex
            
        logger.warning(f"Unsupported DEX: {name}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to create DEX {name}: {e}")
        return None

async def initialize_dexes(
    web3: Web3,
    config: Dict[str, Any]
) -> Dict[str, BaseDEX]:
    """
    Initialize all configured DEXes.
    
    Args:
        web3: Web3 instance
        config: Configuration dictionary
        
    Returns:
        Dict[str, BaseDEX]: Dictionary of initialized DEXes
    """
    try:
        # Clear existing registry
        registry.clear()
        
        # Initialize each configured DEX
        for dex_name, dex_config in config.get("dexes", {}).items():
            if not dex_config.get("enabled", True):
                logger.info(f"Skipping disabled DEX: {dex_name}")
                continue
                
            dex = await create_dex(dex_name, web3, config)
            if dex:
                logger.info(f"Initialized DEX: {dex_name}")
            else:
                logger.warning(f"Failed to initialize DEX: {dex_name}")
                
        return {name: dex for name, dex in registry._dexes.items()}
        
    except Exception as e:
        logger.error(f"Failed to initialize DEXes: {e}")
        return {}
