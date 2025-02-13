"""DEX management system for efficient protocol interactions."""

import logging
from typing import Dict, Any, Optional, List, cast
from web3 import Web3

from arbitrage_bot.core.dex.baseswap import Baseswap
from arbitrage_bot.core.dex.swapbased import SwapBased
from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)

class DEXManager:
    """Manages DEX protocol interactions."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize DEX manager."""
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self.dexes: Dict[str, Any] = {}
        self.initialized = False
        
        # Performance tracking
        self.performance_metrics = {
            'success_rate': {},
            'avg_response_time': {},
            'error_rate': {}
        }

    async def initialize(self) -> bool:
        """Initialize all configured DEXes."""
        try:
            if self.initialized:
                return True

            dex_classes = {
                'baseswap': Baseswap,
                'swapbased': SwapBased
            }

            for dex_name, dex_config in self.config.get('dexes', {}).items():
                if dex_name in dex_classes:
                    try:
                        dex = dex_classes[dex_name](self.web3_manager, dex_config)
                        if await dex.initialize():
                            self.dexes[dex_name] = dex
                            logger.info(f"Initialized {dex_name} interface")
                            
                            # Initialize performance tracking
                            self.performance_metrics['success_rate'][dex_name] = 1.0
                            self.performance_metrics['avg_response_time'][dex_name] = 0
                            self.performance_metrics['error_rate'][dex_name] = 0
                            
                    except Exception as e:
                        logger.error(f"Failed to initialize {dex_name}: {e}")
                        continue

            if not self.dexes:
                logger.error("No DEXes initialized successfully")
                return False

            self.initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize DEX manager: {e}")
            return False

    def get_dex(self, dex_name: Optional[str]) -> Optional[Any]:
        """Get DEX interface by name."""
        if not dex_name:
            return None
        return self.dexes.get(dex_name)

    def get_dex_by_address(self, address: str) -> Optional[Any]:
        """Get DEX interface by router address."""
        address = Web3.to_checksum_address(address)
        for dex in self.dexes.values():
            if dex.router_address.lower() == address.lower():
                return dex
        return None

    async def get_all_pairs(self) -> List[Dict[str, Any]]:
        """Get all trading pairs from all DEXes."""
        pairs = []
        for dex_name, dex in self.dexes.items():
            try:
                dex_pairs = await dex.get_all_pairs()
                for pair in dex_pairs:
                    pair['dex'] = dex_name
                pairs.extend(dex_pairs)
            except Exception as e:
                logger.error(f"Error getting pairs from {dex_name}: {e}")
        return pairs

    async def update_performance_metrics(self, dex_name: str, metrics: Dict[str, Any]) -> None:
        """Update performance metrics for a DEX."""
        try:
            if dex_name in self.performance_metrics['success_rate']:
                # Update success rate with exponential moving average
                alpha = 0.1  # Weight for new data
                old_rate = self.performance_metrics['success_rate'][dex_name]
                new_rate = metrics.get('success', old_rate)
                self.performance_metrics['success_rate'][dex_name] = (
                    old_rate * (1 - alpha) + new_rate * alpha
                )

                # Update response time
                old_time = self.performance_metrics['avg_response_time'][dex_name]
                new_time = metrics.get('response_time', old_time)
                self.performance_metrics['avg_response_time'][dex_name] = (
                    old_time * (1 - alpha) + new_time * alpha
                )

                # Update error rate
                old_errors = self.performance_metrics['error_rate'][dex_name]
                new_errors = metrics.get('error_rate', old_errors)
                self.performance_metrics['error_rate'][dex_name] = (
                    old_errors * (1 - alpha) + new_errors * alpha
                )

        except Exception as e:
            logger.error(f"Error updating performance metrics for {dex_name}: {e}")

    def get_performance_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get current performance metrics for all DEXes."""
        return self.performance_metrics.copy()

    async def cleanup(self) -> None:
        """Cleanup DEX connections."""
        try:
            for dex in self.dexes.values():
                try:
                    if hasattr(dex, 'cleanup'):
                        await dex.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up DEX: {e}")
            
            self.dexes.clear()
            self.initialized = False
            logger.info("DEX manager cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during DEX manager cleanup: {e}")

    def get_best_dex(self, token_pair: str) -> str:
        """Get best performing DEX for a token pair."""
        try:
            best_score = -1
            best_dex = next(iter(self.dexes.keys()))  # Default to first DEX
            
            for dex_name in self.dexes:
                # Calculate performance score
                success_rate = self.performance_metrics['success_rate'].get(dex_name, 0)
                response_time = self.performance_metrics['avg_response_time'].get(dex_name, float('inf'))
                error_rate = self.performance_metrics['error_rate'].get(dex_name, 1)
                
                # Normalize response time (0-1 where 1 is best)
                norm_time = 1 / (1 + response_time/1000)  # Convert ms to normalized score
                
                # Calculate weighted score
                score = (
                    success_rate * 0.5 +      # 50% weight on success
                    norm_time * 0.3 +         # 30% weight on speed
                    (1 - error_rate) * 0.2    # 20% weight on reliability
                )
                
                if score > best_score:
                    best_score = score
                    best_dex = dex_name
            
            return best_dex
            
        except Exception as e:
            logger.error(f"Error finding best DEX: {e}")
            return next(iter(self.dexes.keys()))  # Return first DEX as fallback

async def create_dex_manager(web3_manager: Web3Manager, config: Dict[str, Any]) -> DEXManager:
    """Create and initialize a new DEXManager instance.
    
    Args:
        web3_manager: Initialized Web3Manager instance
        config: Configuration dictionary with DEX settings
        
    Returns:
        Initialized DEXManager instance
    """
    dex_manager = DEXManager(web3_manager, config)
    await dex_manager.initialize()
    return dex_manager
