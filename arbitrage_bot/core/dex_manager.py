"""DEX management and initialization."""

import logging
from typing import Dict, Any, Optional
from web3 import Web3

from .dex_types import DEXType
from ..dex.base_dex import BaseDEX
from ..dex.aerodrome_v2 import AerodromeV2
from ..dex.aerodrome_v3 import AerodromeV3

logger = logging.getLogger(__name__)

class DEXManager:
    """Manages DEX initialization and access."""
    
    def __init__(self, web3: Web3, config: Dict[str, Any]):
        """Initialize DEX manager."""
        self.web3 = web3
        self.config = config
        self.dexes: Dict[str, BaseDEX] = {}
        
    def _get_dex_type(self, name: str) -> Optional[DEXType]:
        """Get DEX type from name."""
        name = name.lower()
        if name == "aerodrome":
            return DEXType.AERODROME_V2
        elif name == "aerodrome_v3":
            return DEXType.AERODROME_V3
        elif name == "uniswap_v2":
            return DEXType.UNISWAP_V2
        elif name == "uniswap_v3":
            return DEXType.UNISWAP_V3
        elif name == "baseswap":
            return DEXType.BASESWAP
        elif name == "pancakeswap":
            return DEXType.PANCAKESWAP
        elif name == "swapbased":
            return DEXType.SWAPBASED
        elif name == "rocketswap":
            return DEXType.ROCKETSWAP
        return None
        
    async def initialize_dex(self, name: str) -> Optional[BaseDEX]:
        """Initialize a DEX instance."""
        try:
            # Get DEX type
            dex_type = self._get_dex_type(name)
            if not dex_type:
                logger.warning(f"Unsupported DEX type: {name}")
                return None
                
            # Get DEX config
            dex_configs = self.config.get("dexes", {})
            if not dex_configs:
                logger.warning("No DEX configurations found")
                return None

            dex_config = dex_configs.get(name)
            if not dex_config:
                logger.warning(f"No configuration found for DEX: {name}")
                return None

            # Convert addresses to checksum format
            if 'router' in dex_config:
                dex_config['router'] = self.web3.to_checksum_address(dex_config['router'])
            if 'factory' in dex_config:
                dex_config['factory'] = self.web3.to_checksum_address(dex_config['factory'])
            if 'quoter' in dex_config:
                dex_config['quoter'] = self.web3.to_checksum_address(dex_config['quoter'])

            # Create a new config with just this DEX's config
            config = {
                "dexes": {name: dex_config},
                "tokens": self.config.get("tokens", {})
            }

            try:
                # Create and initialize instance based on type
                if dex_type == DEXType.AERODROME_V2:
                    dex = AerodromeV2(self.web3, dex_config)
                    await dex.initialize()
                    logger.info(f"Created Aerodrome V2 instance")
                elif dex_type == DEXType.AERODROME_V3:
                    dex = AerodromeV3(self.web3, dex_config)
                    await dex.initialize()
                    logger.info(f"Created Aerodrome V3 instance")
                elif dex_type == DEXType.UNISWAP_V3:
                    from ..dex.uniswap_v3 import UniswapV3
                    dex = UniswapV3(self.web3, dex_config)
                    await dex.initialize()
                    logger.info(f"Created Uniswap V3 instance")
                elif dex_type == DEXType.BASESWAP:
                    from ..dex.baseswap import Baseswap
                    dex = Baseswap(self.web3, dex_config)
                    await dex.initialize()
                    logger.info(f"Created Baseswap instance")
                elif dex_type == DEXType.PANCAKESWAP:
                    from ..dex.pancakeswap import Pancakeswap
                    dex = Pancakeswap(self.web3, dex_config)
                    await dex.initialize()
                    logger.info(f"Created Pancakeswap instance")
                elif dex_type == DEXType.SWAPBASED:
                    from ..dex.swapbased import SwapBased
                    dex = SwapBased(self.web3, dex_config)
                    await dex.initialize()
                    logger.info(f"Created SwapBased instance")
                elif dex_type == DEXType.ROCKETSWAP:
                    from ..dex.rocketswap import RocketSwap
                    dex = RocketSwap(self.web3, dex_config)
                    await dex.initialize()
                    logger.info(f"Created RocketSwap instance")
                else:
                    logger.warning(f"DEX type not implemented: {dex_type}")
                    return None
            except Exception as e:
                logger.error(f"Error in {name} (1/3): {e}")
                return None

            # Verify contracts exist
            try:
                if not dex.factory or not dex.router:
                    logger.error(f"Missing required contracts for {name}")
                    return None
                logger.info(f"Verified contracts for {name}")
            except Exception as e:
                logger.error(f"Failed to verify contracts for {name}: {e}")
                return None
                
            # Store instance
            self.dexes[name] = dex
            logger.info(f"Initialized DEX: {name} ({dex_type})")
            return dex
            
        except Exception as e:
            logger.error(f"Failed to initialize DEX {name}: {e}")
            return None
            
    async def initialize(self) -> bool:
        """Initialize DEX manager."""
        try:
            dexes = await self.initialize_all()
            if not dexes:
                logger.error("No DEXes were initialized")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to initialize DEX manager: {e}")
            return False

    async def initialize_all(self) -> Dict[str, BaseDEX]:
        """Initialize all configured DEXes."""
        try:
            # Clear existing instances
            self.dexes.clear()
            
            # Initialize each configured DEX
            initialized_count = 0
            for dex_name, dex_config in self.config.get("dexes", {}).items():
                if not dex_config.get("enabled", True):
                    logger.info(f"Skipping disabled DEX: {dex_name}")
                    continue
                    
                dex = await self.initialize_dex(dex_name)
                if dex:
                    initialized_count += 1
                else:
                    logger.warning(f"Failed to initialize DEX: {dex_name}")
            
            if initialized_count == 0:
                logger.error("No DEXes were initialized successfully")
                return {}
                
            return self.dexes
            
        except Exception as e:
            logger.error(f"Failed to initialize DEXes: {e}")
            return {}
            
    def get_dex(self, name: str) -> Optional[BaseDEX]:
        """Get initialized DEX instance."""
        return self.dexes.get(name.lower())
        
    def list_dexes(self) -> list:
        """List initialized DEXes."""
        return list(self.dexes.keys())
