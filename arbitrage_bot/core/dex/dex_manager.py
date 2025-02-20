"""DEX manager for handling multiple DEX integrations."""

import logging
import eventlet
from typing import Dict, Any, Optional, List, Tuple, cast, Set
from decimal import Decimal
from ..web3.web3_manager import Web3Manager
from .base_dex import BaseDEX
from .base_dex_v2 import BaseDEXV2
from .base_dex_v3 import BaseDEXV3
from .baseswap import BaseSwap
from .rocketswap_v3 import RocketSwapV3
from .swapbased import SwapBased

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
        self.known_methods: Set[str] = set()  # Common DEX method signatures
        self.known_contracts: Set[str] = set()  # Known DEX contract addresses
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
            logger.info(f"Using wallet address: {self.web3_manager.wallet_address}")
            
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
                    
                    # Initialize specific DEX implementation
                    if dex_name == 'baseswap':
                        dex = BaseSwap(
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
                    else:
                        logger.warning(f"Unsupported DEX: {dex_name}")
                        continue

                    # Initialize DEX
                    if await self._initialize_dex(dex):
                        self.dex_instances[dex_name] = dex
                        # Add DEX methods and contracts to known sets
                        self.known_methods.update(dex.get_method_signatures())
                        self.known_contracts.add(dex.get_router_address())
                        logger.info(f"Initialized DEX: {dex_name}")
                    else:
                        logger.error(f"Failed to initialize DEX: {dex_name}")

                except Exception as e:
                    logger.error(f"Error initializing DEX {dex_name}: {e}")
                    continue

            self.initialized = len(self.dex_instances) > 0
            if self.initialized:
                logger.info(f"Initialized {len(self.dex_instances)} DEXes")
            else:
                logger.error("No DEXes were successfully initialized")

            return self.initialized

        except Exception as e:
            logger.error(f"Failed to initialize DEX manager: {e}")
            return False

    async def _initialize_dex(self, dex: BaseDEX) -> bool:
        """Initialize a DEX instance."""
        try:
            return await eventlet.spawn(dex.initialize).wait()
        except Exception as e:
            logger.error(f"Error initializing DEX: {e}")
            return False

    def get_dex(self, name: str) -> Optional[BaseDEX]:
        """Get DEX instance by name."""
        return self.dex_instances.get(name)

    def get_all_dexes(self) -> List[BaseDEX]:
        """Get all initialized DEX instances."""
        return list(self.dex_instances.values())

    def get_enabled_dexes(self) -> List[BaseDEX]:
        """Get all enabled DEX instances."""
        return [
            dex for dex in self.dex_instances.values()
            if dex.config.get('enabled', False)
        ]

    def get_token_price(self, token_address: str) -> Dict[str, Decimal]:
        """Get token price across all enabled DEXes."""
        try:
            prices = {}
            for dex_name, dex in self.dex_instances.items():
                if not dex.config.get('enabled', False):
                    continue

                try:
                    price = dex.get_token_price(token_address)
                    if price and price > 0:
                        prices[dex_name] = Decimal(str(price))
                except Exception as e:
                    logger.error(f"Error getting price from {dex_name}: {e}")
                    continue

            return prices

        except Exception as e:
            logger.error(f"Failed to get token prices: {e}")
            return {}

    def get_best_price(self, token_address: str, side: str = 'buy') -> Tuple[str, Decimal]:
        """Get best price for token across all DEXes."""
        try:
            prices = self.get_token_price(token_address)
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
            logger.error(f"Failed to get best price: {e}")
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics for all DEXes."""
        try:
            metrics = {}
            for dex_name, dex in self.dex_instances.items():
                if not dex.config.get('enabled', False):
                    continue

                try:
                    dex_metrics = {
                        'version': dex.config.get('version', 'v2'),
                        'enabled': True,
                        'initialized': dex.initialized,
                        'last_update': eventlet.time.time(),
                        'error_count': getattr(dex, 'error_count', 0),
                        'success_rate': getattr(dex, 'success_rate', 0)
                    }
                    metrics[dex_name] = dex_metrics
                except Exception as e:
                    logger.error(f"Error getting metrics for {dex_name}: {e}")
                    continue

            return metrics

        except Exception as e:
            logger.error(f"Failed to get DEX metrics: {e}")
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
        logger.error(f"Failed to create DEX manager: {e}")
        raise
