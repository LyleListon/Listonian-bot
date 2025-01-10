"""Gas optimization system."""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import statistics

from ..dex.dex_manager import DEXManager
from ..dex.utils import GAS_COSTS

logger = logging.getLogger(__name__)

class GasOptimizer:
    """Optimizes gas usage for arbitrage trades."""

    def __init__(
        self,
        dex_manager: DEXManager,
        base_gas_limit: int = 500000,  # 500k gas units
        max_gas_price: int = 100000000000,  # 100 gwei
        min_gas_price: int = 5000000000,  # 5 gwei
        gas_price_buffer: float = 1.1,  # 10% buffer
        gas_history_window: int = 200  # blocks
    ):
        """Initialize gas optimizer."""
        self.dex_manager = dex_manager
        self.base_gas_limit = base_gas_limit
        self.max_gas_price = max_gas_price
        self.min_gas_price = min_gas_price
        self.gas_price_buffer = gas_price_buffer
        self.gas_history_window = gas_history_window
        
        # Gas price history
        self.gas_prices: List[int] = []
        self.last_update = datetime.min
        
        # Gas usage statistics
        self.dex_gas_stats: Dict[str, Dict[str, Any]] = {}
        self.protocol_gas_stats = {
            'v2': {'base': GAS_COSTS['v2']['base_cost'], 'hop': GAS_COSTS['v2']['hop_cost']},
            'v3': {'base': GAS_COSTS['v3']['base_cost'], 'hop': GAS_COSTS['v3']['hop_cost']}
        }

    async def get_optimal_gas_price(self) -> int:
        """
        Get optimal gas price based on network conditions.
        
        Returns:
            int: Optimal gas price in wei
        """
        try:
            # Update gas price history
            await self._update_gas_history()
            
            if not self.gas_prices:
                return self.min_gas_price
            
            # Calculate optimal price
            recent_prices = self.gas_prices[-20:]  # Last 20 blocks
            median_price = statistics.median(recent_prices)
            
            # Add buffer for safety
            optimal_price = int(median_price * self.gas_price_buffer)
            
            # Ensure within bounds
            optimal_price = max(self.min_gas_price, min(self.max_gas_price, optimal_price))
            
            return optimal_price
            
        except Exception as e:
            logger.error(f"Error getting optimal gas price: {e}")
            return self.min_gas_price

    async def estimate_gas_limit(
        self,
        dex_name: str,
        path: List[str],
        protocol: str = 'v2'
    ) -> int:
        """
        Estimate gas limit for a trade path.
        
        Args:
            dex_name: Name of DEX
            path: Token path for trade
            protocol: DEX protocol ('v2' or 'v3')
            
        Returns:
            int: Estimated gas limit
        """
        try:
            # Get base costs for protocol
            protocol_stats = self.protocol_gas_stats[protocol]
            base_cost = protocol_stats['base']
            hop_cost = protocol_stats['hop']
            
            # Calculate path cost
            path_length = len(path)
            path_cost = base_cost + (hop_cost * (path_length - 1))
            
            # Add DEX-specific adjustment
            dex_stats = self.dex_gas_stats.get(dex_name, {})
            adjustment = dex_stats.get('adjustment', 1.0)
            
            # Calculate final limit with safety buffer
            gas_limit = int(path_cost * adjustment * GAS_COSTS[protocol]['buffer'])
            
            # Ensure within bounds
            return min(gas_limit, self.base_gas_limit)
            
        except Exception as e:
            logger.error(f"Error estimating gas limit: {e}")
            return self.base_gas_limit

    async def update_gas_stats(
        self,
        dex_name: str,
        protocol: str,
        actual_gas: int,
        path_length: int
    ) -> None:
        """
        Update gas usage statistics.
        
        Args:
            dex_name: Name of DEX
            protocol: DEX protocol ('v2' or 'v3')
            actual_gas: Actual gas used
            path_length: Length of trade path
        """
        try:
            # Initialize DEX stats if needed
            if dex_name not in self.dex_gas_stats:
                self.dex_gas_stats[dex_name] = {
                    'total_trades': 0,
                    'total_gas': 0,
                    'avg_gas': 0,
                    'adjustment': 1.0
                }
            
            stats = self.dex_gas_stats[dex_name]
            
            # Update running averages
            stats['total_trades'] += 1
            stats['total_gas'] += actual_gas
            stats['avg_gas'] = stats['total_gas'] / stats['total_trades']
            
            # Calculate expected gas
            protocol_stats = self.protocol_gas_stats[protocol]
            expected_gas = protocol_stats['base'] + (protocol_stats['hop'] * (path_length - 1))
            
            # Update adjustment factor
            if expected_gas > 0:
                current_ratio = actual_gas / expected_gas
                stats['adjustment'] = (
                    (stats['adjustment'] * (stats['total_trades'] - 1) + current_ratio) /
                    stats['total_trades']
                )
            
        except Exception as e:
            logger.error(f"Error updating gas stats: {e}")

    async def optimize_path_gas(
        self,
        paths: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Optimize gas usage across multiple paths.
        
        Args:
            paths: List of path details from DEXs
            
        Returns:
            List[Dict[str, Any]]: Optimized paths with gas estimates
        """
        try:
            optimized = []
            gas_price = await self.get_optimal_gas_price()
            
            for path in paths:
                dex_name = path['dex_name']
                protocol = 'v3' if 'quoter' in path else 'v2'
                
                # Get gas limit
                gas_limit = await self.estimate_gas_limit(
                    dex_name=dex_name,
                    path=path['path'],
                    protocol=protocol
                )
                
                # Calculate gas cost
                gas_cost = gas_limit * gas_price
                
                # Update path
                path_copy = path.copy()
                path_copy.update({
                    'gas_limit': gas_limit,
                    'gas_price': gas_price,
                    'gas_cost': gas_cost
                })
                
                optimized.append(path_copy)
            
            return optimized
            
        except Exception as e:
            logger.error(f"Error optimizing path gas: {e}")
            return paths

    async def _update_gas_history(self) -> None:
        """Update gas price history."""
        try:
            now = datetime.now()
            if (now - self.last_update) < timedelta(seconds=15):
                return
                
            # Get recent blocks
            w3 = self.dex_manager.web3_manager.w3
            latest = w3.eth.block_number
            start = max(0, latest - self.gas_history_window)
            
            prices = []
            for block_num in range(start, latest + 1):
                block = w3.eth.get_block(block_num)
                if 'baseFeePerGas' in block:
                    prices.append(block['baseFeePerGas'])
            
            self.gas_prices = prices
            self.last_update = now
            
        except Exception as e:
            logger.error(f"Error updating gas history: {e}")

    def get_dex_gas_stats(self, dex_name: str) -> Optional[Dict[str, Any]]:
        """Get gas statistics for a specific DEX."""
        return self.dex_gas_stats.get(dex_name)

    def get_protocol_gas_stats(self, protocol: str) -> Optional[Dict[str, Any]]:
        """Get gas statistics for a specific protocol."""
        return self.protocol_gas_stats.get(protocol)

    async def analyze_gas_usage(self) -> Dict[str, Any]:
        """
        Analyze gas usage patterns.
        
        Returns:
            Dict[str, Any]: Gas usage analysis
        """
        try:
            analysis = {
                'current_gas_price': await self.get_optimal_gas_price(),
                'dex_stats': self.dex_gas_stats.copy(),
                'protocol_stats': self.protocol_gas_stats.copy(),
                'recommendations': []
            }
            
            # Generate recommendations
            for dex_name, stats in self.dex_gas_stats.items():
                if stats['adjustment'] > 1.2:  # Using 20% more gas than expected
                    analysis['recommendations'].append(
                        f"{dex_name} using {(stats['adjustment'] - 1) * 100:.1f}% more gas "
                        "than expected. Consider reviewing path optimization."
                    )
            
            if self.gas_prices:
                avg_price = sum(self.gas_prices) / len(self.gas_prices)
                if avg_price > self.max_gas_price * 0.8:  # Within 20% of max
                    analysis['recommendations'].append(
                        "Network gas prices approaching maximum threshold. "
                        "Consider adjusting trading thresholds."
                    )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing gas usage: {e}")
            return {
                'current_gas_price': self.min_gas_price,
                'dex_stats': {},
                'protocol_stats': {},
                'recommendations': [f"Error analyzing gas usage: {e}"]
            }
