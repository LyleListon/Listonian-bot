"""Network data collector implementation."""

import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from web3 import Web3

from ..base import DataCollector

class NetworkDataCollector(DataCollector):
    """Collect network-level data including gas prices and blockchain metrics."""
    
    def __init__(self, web3_manager, config: Dict[str, Any]):
        """
        Initialize network data collector.
        
        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary containing:
                - interval_seconds: Collection interval
                - metrics: Dictionary of enabled metrics
                - validation: Validation rules
        """
        super().__init__(config)
        self.web3 = web3_manager.web3
        
        # Initialize metric collection functions
        self.metrics = {
            'base_fee': self._collect_base_fee,
            'priority_fee': self._collect_priority_fee,
            'block_utilization': self._collect_block_utilization,
            'pending_txs': self._collect_pending_transactions,
            'network_load': self._collect_network_load,
            'block_time': self._collect_block_time,
            'gas_price_history': self._collect_gas_price_history
        }
        
        # Track historical data for analysis
        self._block_times = []
        self._gas_prices = []
        self.max_history_size = config.get('max_history_size', 1000)
        
    async def collect(self) -> Dict[str, Any]:
        """
        Collect network metrics.
        
        Returns:
            Dictionary containing:
                - base_fee: Current base fee in wei
                - priority_fee: Current priority fee in wei
                - block_utilization: Current block utilization (0-1)
                - pending_txs: Number of pending transactions
                - network_load: Network load indicator (0-1)
                - block_time: Average block time in seconds
                - gas_price_history: Recent gas price trends
        """
        data = {}
        enabled_metrics = self.config.get('metrics', {})
        
        for metric_name, metric_config in enabled_metrics.items():
            if metric_config.get('enabled', True):
                try:
                    collector_func = self.metrics.get(metric_name)
                    if collector_func:
                        data[metric_name] = await collector_func()
                except Exception as e:
                    self.logger.error(f"Error collecting {metric_name}: {e}")
                    data[metric_name] = None
                    
        return data
        
    async def validate_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate collected data.
        
        Args:
            data: Data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        validation_rules = self.config.get('validation', {})
        
        for metric_name, value in data.items():
            rules = validation_rules.get(metric_name, {})
            
            # Check if required metric is missing
            if rules.get('required', False) and value is None:
                return False, f"Required metric {metric_name} is missing"
                
            # Skip further validation if value is None
            if value is None:
                continue
                
            # Validate numeric ranges
            if isinstance(value, (int, float)):
                min_value = rules.get('min_value')
                max_value = rules.get('max_value')
                
                if min_value is not None and value < min_value:
                    return False, f"{metric_name} value {value} below minimum {min_value}"
                    
                if max_value is not None and value > max_value:
                    return False, f"{metric_name} value {value} above maximum {max_value}"
                    
        return True, None
        
    async def _collect_base_fee(self) -> int:
        """
        Collect current base fee.
        
        Returns:
            Base fee in wei
        """
        block = await self.web3.eth.get_block('latest')
        return block.baseFeePerGas
        
    async def _collect_priority_fee(self) -> int:
        """
        Collect current priority fee.
        
        Returns:
            Priority fee in wei
        """
        return await self.web3.eth.max_priority_fee
        
    async def _collect_block_utilization(self) -> float:
        """
        Calculate block utilization.
        
        Returns:
            Block utilization ratio (0-1)
        """
        block = await self.web3.eth.get_block('latest')
        return block.gasUsed / block.gasLimit
        
    async def _collect_pending_transactions(self) -> int:
        """
        Get pending transaction count.
        
        Returns:
            Number of pending transactions
        """
        return len(await self.web3.eth.get_pending_transactions())
        
    async def _collect_network_load(self) -> float:
        """
        Calculate network load based on multiple metrics.
        
        Returns:
            Network load indicator (0-1)
        """
        try:
            # Get relevant metrics
            block_util = await self._collect_block_utilization()
            pending_count = await self._collect_pending_transactions()
            
            # Calculate load score (customize based on your needs)
            load_score = (
                block_util * 0.6 +  # Weight block utilization more heavily
                min(pending_count / 1000, 1) * 0.4  # Cap pending tx contribution
            )
            
            return min(load_score, 1.0)  # Ensure result is 0-1
            
        except Exception as e:
            self.logger.error(f"Error calculating network load: {e}")
            return 0.0
            
    async def _collect_block_time(self) -> float:
        """
        Calculate average block time.
        
        Returns:
            Average block time in seconds
        """
        try:
            # Get current and previous block
            current_block = await self.web3.eth.get_block('latest')
            prev_block = await self.web3.eth.get_block(current_block.number - 1)
            
            # Calculate time difference
            block_time = current_block.timestamp - prev_block.timestamp
            
            # Update history
            self._block_times.append(block_time)
            if len(self._block_times) > self.max_history_size:
                self._block_times.pop(0)
                
            # Calculate moving average
            return sum(self._block_times) / len(self._block_times)
            
        except Exception as e:
            self.logger.error(f"Error calculating block time: {e}")
            return 0.0
            
    async def _collect_gas_price_history(self) -> Dict[str, Any]:
        """
        Collect gas price history and trends.
        
        Returns:
            Dictionary containing:
                - current: Current gas price in wei
                - average: Average over history
                - trend: Recent trend direction
                - volatility: Price volatility indicator
        """
        try:
            current_price = await self.web3.eth.gas_price
            
            # Update history
            self._gas_prices.append(current_price)
            if len(self._gas_prices) > self.max_history_size:
                self._gas_prices.pop(0)
                
            # Calculate statistics
            avg_price = sum(self._gas_prices) / len(self._gas_prices)
            
            # Calculate trend (positive or negative)
            if len(self._gas_prices) >= 2:
                trend = 1 if self._gas_prices[-1] > self._gas_prices[-2] else -1
            else:
                trend = 0
                
            # Calculate volatility (standard deviation)
            if len(self._gas_prices) >= 2:
                mean = sum(self._gas_prices) / len(self._gas_prices)
                variance = sum((x - mean) ** 2 for x in self._gas_prices) / len(self._gas_prices)
                volatility = (variance ** 0.5) / mean  # Coefficient of variation
            else:
                volatility = 0
                
            return {
                'current': current_price,
                'average': avg_price,
                'trend': trend,
                'volatility': volatility
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting gas price history: {e}")
            return {
                'current': 0,
                'average': 0,
                'trend': 0,
                'volatility': 0
            }