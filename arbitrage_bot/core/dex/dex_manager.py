"""DEX manager for handling multiple DEX integrations."""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple, cast, Set
from decimal import Decimal
from web3 import Web3
from ..web3.web3_manager import Web3Manager
from .base_dex import BaseDEX
from .base_dex_v2 import BaseDEXV2
from .base_dex_v3 import BaseDEXV3
from .baseswap import BaseSwap
from .rocketswap_v3 import RocketSwapV3
from .swapbased import SwapBased
from .pancakeswap import PancakeSwap
from .baseswap_v3 import BaseSwapV3

logger = logging.getLogger(__name__)

__all__ = ['DexManager', 'create_dex_manager']

class DexManager:
    """Manages multiple DEX integrations."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize DEX manager."""
        self.web3_manager = web3_manager
        self.config = config
        self.dex_instances = {}
        self.initialized = False
        self.known_methods = set()  # Common DEX method signatures
        self.known_contracts = set()  # Known DEX contract addresses
        logger.debug("DEX manager initialized")

    async def initialize(self) -> bool:
        """Initialize all configured DEXes."""
        try:
            # Get DEX configurations
            dex_configs = self.config.get('dexes', {})
            
            # Get wallet configuration from web3_manager
            wallet_config = {
                'wallet': {
                    'address': self.web3_manager.wallet_address,
                    'private_key': self.web3_manager.private_key
                }
            }
            logger.info("Using wallet address: %s", self.web3_manager.wallet_address)
            
            # Get WETH address from tokens config
            weth_address = self.config.get('tokens', {}).get('WETH', {}).get('address')
            if not weth_address:
                logger.error("WETH address not found in config")
                return False

            # Ensure WETH address is valid
            try:
                weth_address = Web3.to_checksum_address(weth_address)
            except Exception as e:
                logger.error("Invalid WETH address in config: %s", str(e))
                return False
            
            # Initialize each enabled DEX
            for dex_name, dex_config in dex_configs.items():
                if not dex_config.get('enabled', False):
                    continue

                try:
                    # Create a clean config without 'name' field
                    clean_config = {k: v for k, v in dex_config.items() if k != 'name'}
                    
                    # Add name to config for ABI loading
                    clean_config['name'] = dex_name
                    
                    # Add wallet configuration
                    clean_config.update(wallet_config)
                    
                    # Add WETH address to config
                    clean_config['weth_address'] = weth_address
                    
                    # Add tokens configuration
                    clean_config['tokens'] = self.config.get('tokens', {})
                    
                    # Initialize specific DEX implementation
                    dex = None
                    if dex_name == 'baseswap':
                        dex = BaseSwap(
                            web3_manager=self.web3_manager,
                            config=clean_config
                        )
                    elif dex_name == 'baseswap_v3':
                        dex = BaseSwapV3(
                            web3_manager=self.web3_manager,
                            config=clean_config
                        )
                    elif dex_name == 'swapbased':
                        dex = SwapBased(
                            web3_manager=self.web3_manager,
                            config=clean_config
                        )
                    elif dex_name == 'rocketswap_v3':
                        dex = RocketSwapV3(
                            web3_manager=self.web3_manager,
                            config=clean_config
                        )
                    elif dex_name == 'pancakeswap':
                        dex = PancakeSwap(
                            web3_manager=self.web3_manager,
                            config=clean_config
                        )
                    else:
                        logger.warning("Unsupported DEX: %s", dex_name)
                        continue

                    # Initialize DEX
                    if dex and await dex.initialize():
                        self.dex_instances[dex_name] = dex
                        # Add DEX methods and contracts to known sets
                        self.known_methods.update(dex.get_method_signatures())
                        self.known_contracts.add(dex.get_router_address())
                        logger.info("Initialized DEX: %s", dex_name)
                    else:
                        logger.error("Failed to initialize DEX: %s", dex_name)

                except Exception as e:
                    logger.error("Error initializing DEX %s: %s", dex_name, str(e))
                    continue

            self.initialized = len(self.dex_instances) > 0
            if self.initialized:
                logger.info("Initialized %d DEXes", len(self.dex_instances))
            else:
                logger.error("No DEXes were successfully initialized")

            return self.initialized

        except Exception as e:
            logger.error("Failed to initialize DEX manager: %s", str(e))
            return False

    def get_dex(self, name: str) -> Optional[BaseDEX]:
        """Get DEX instance by name."""
        return self.dex_instances.get(name)

    def get_all_dexes(self) -> List[BaseDEX]:
        """Get all initialized DEX instances."""
        return list(self.dex_instances.values())

    async def get_enabled_dexes(self) -> List[BaseDEX]:
        """Get all enabled DEX instances."""
        enabled_dexes = []
        for dex in self.dex_instances.values():
            if await dex.is_enabled():
                enabled_dexes.append(dex)
        return enabled_dexes

    async def get_token_price(self, token_address: str) -> Dict[str, Decimal]:
        """Get token price across all enabled DEXes."""
        try:
            prices = {}
            enabled_dexes = await self.get_enabled_dexes()
            
            for dex in enabled_dexes:
                try:
                    price = await dex.get_token_price(token_address)
                    if price and price > 0:
                        prices[dex.name] = Decimal(str(price))
                except Exception as e:
                    logger.error("Error getting price from %s: %s", dex.name, str(e))
                    continue

            return prices

        except Exception as e:
            logger.error("Failed to get token prices: %s", str(e))
            return {}

    async def get_best_price(self, token_address: str, side: str = 'buy') -> Tuple[str, Decimal]:
        """Get best price for token across all DEXes."""
        try:
            prices = await self.get_token_price(token_address)
            if not prices:
                raise ValueError("No valid prices found")

            if side.lower() == 'buy':
                # Get lowest price for buying
                best_dex = min(prices.items(), key=lambda x: x[1])
            else:
                # Get highest price for selling
                best_dex = max(prices.items(), key=lambda x: x[1])

            return best_dex

        except Exception as e:
            logger.error("Failed to get best price: %s", str(e))
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics for all DEXes."""
        try:
            metrics = {}
            for dex_name, dex in self.dex_instances.items():
                try:
                    dex_metrics = {
                        'version': dex.config.get('version', 'v2'),
                        'enabled': dex.config.get('enabled', False),
                        'initialized': dex.initialized,
                        'last_update': time.time(),
                        'error_count': getattr(dex, 'error_count', 0),
                        'success_rate': getattr(dex, 'success_rate', 0)
                    }
                    metrics[dex_name] = dex_metrics
                except Exception as e:
                    logger.error("Error getting metrics for %s: %s", dex_name, str(e))
                    continue

            return metrics

        except Exception as e:
            logger.error("Failed to get DEX metrics: %s", str(e))
            return {}


async def create_dex_manager(web3_manager: Web3Manager, config: Dict[str, Any]) -> DexManager:
    """Create and initialize DEX manager."""
    try:
        manager = DexManager(web3_manager, config)
        if not await manager.initialize():
            raise RuntimeError("Failed to initialize DEX manager")
        logger.debug("Created DEX manager")
        return manager
    except Exception as e:
        logger.error("Failed to create DEX manager: %s", str(e))
        raise
