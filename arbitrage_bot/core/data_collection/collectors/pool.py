"""Pool data collector implementation."""

import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
from decimal import Decimal
from web3 import Web3

from ..base import DataCollector

class PoolDataCollector(DataCollector):
    """Collect pool-specific data including liquidity and volume metrics."""
    
    def __init__(self, web3_manager, dex_manager, config: Dict[str, Any]):
        """
        Initialize pool data collector.
        
        Args:
            web3_manager: Web3Manager instance
            dex_manager: DEXManager instance
            config: Configuration dictionary containing:
                - interval_seconds: Collection interval
                - pools: List of pools to track
                - metrics: Dictionary of enabled metrics
                - validation: Validation rules
        """
        super().__init__(config)
        self.web3 = web3_manager.web3
        self.dex_manager = dex_manager
        self.tracked_pools = config.get('pools', [])
        
        # Initialize metric collection functions
        self.metrics = {
            'reserves': self._collect_reserves,
            'volume': self._collect_volume,
            'price_impact': self._collect_price_impact,
            'concentration': self._collect_concentration,
            'utilization': self._collect_utilization,
            'liquidity_depth': self._collect_liquidity_depth,
            'swap_activity': self._collect_swap_activity
        }
        
        # Track historical data for analysis
        self._volume_history = {}  # pool_address -> List[volume]
        self._price_history = {}   # pool_address -> List[price]
        self.max_history_size = config.get('max_history_size', 1000)
        
    async def collect(self) -> Dict[str, Any]:
        """
        Collect pool metrics.
        
        Returns:
            Dictionary containing metrics for each tracked pool:
                - reserves: Current pool reserves
                - volume: Trading volume metrics
                - price_impact: Price impact analysis
                - concentration: Liquidity concentration metrics
                - utilization: Pool utilization metrics
                - liquidity_depth: Liquidity depth analysis
                - swap_activity: Recent swap activity metrics
        """
        data = {}
        enabled_metrics = self.config.get('metrics', {})
        
        for pool in self.tracked_pools:
            try:
                pool_data = {}
                for metric_name, metric_config in enabled_metrics.items():
                    if metric_config.get('enabled', True):
                        collector_func = self.metrics.get(metric_name)
                        if collector_func:
                            pool_data[metric_name] = await collector_func(pool)
                            
                data[pool['address']] = {
                    'dex': pool['dex'],
                    'metrics': pool_data,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error collecting data for pool {pool['address']}: {e}")
                
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
        
        for pool_address, pool_data in data.items():
            metrics = pool_data.get('metrics', {})
            
            for metric_name, value in metrics.items():
                rules = validation_rules.get(metric_name, {})
                
                # Check if required metric is missing
                if rules.get('required', False) and value is None:
                    return False, f"Required metric {metric_name} missing for pool {pool_address}"
                    
                # Skip further validation if value is None
                if value is None:
                    continue
                    
                # Validate numeric ranges
                if isinstance(value, (int, float, Decimal)):
                    min_value = rules.get('min_value')
                    max_value = rules.get('max_value')
                    
                    if min_value is not None and value < min_value:
                        return False, f"{metric_name} value {value} below minimum {min_value} for pool {pool_address}"
                        
                    if max_value is not None and value > max_value:
                        return False, f"{metric_name} value {value} above maximum {max_value} for pool {pool_address}"
                        
        return True, None
        
    async def _collect_reserves(self, pool: Dict) -> Dict[str, Any]:
        """
        Collect pool reserves.
        
        Args:
            pool: Pool configuration dictionary
            
        Returns:
            Dictionary containing:
                - token0_reserve: Reserve of token0
                - token1_reserve: Reserve of token1
                - last_update: Timestamp of last update
        """
        try:
            contract = self.dex_manager.get_pool_contract(
                pool['address'],
                pool['dex']
            )
            
            if pool.get('version') == 'v3':
                # Handle V3 pool
                slot0 = await contract.functions.slot0().call()
                liquidity = await contract.functions.liquidity().call()
                return {
                    'sqrtPriceX96': slot0[0],
                    'tick': slot0[1],
                    'liquidity': liquidity,
                    'last_update': datetime.utcnow().isoformat()
                }
            else:
                # Handle V2 pool
                reserves = await contract.functions.getReserves().call()
                return {
                    'token0_reserve': reserves[0],
                    'token1_reserve': reserves[1],
                    'last_update': datetime.fromtimestamp(reserves[2]).isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error collecting reserves for pool {pool['address']}: {e}")
            return None
            
    async def _collect_volume(self, pool: Dict) -> Dict[str, Any]:
        """
        Collect trading volume metrics.
        
        Args:
            pool: Pool configuration dictionary
            
        Returns:
            Dictionary containing:
                - volume_24h: 24-hour trading volume
                - volume_1h: 1-hour trading volume
                - swap_count_24h: Number of swaps in 24 hours
        """
        try:
            # Get events from the last 24 hours
            current_block = await self.web3.eth.block_number
            blocks_24h = int(86400 / 12)  # Approximate blocks in 24 hours
            blocks_1h = int(3600 / 12)    # Approximate blocks in 1 hour
            
            contract = self.dex_manager.get_pool_contract(
                pool['address'],
                pool['dex']
            )
            
            # Get swap events
            swap_filter_24h = contract.events.Swap.create_filter(
                fromBlock=current_block - blocks_24h
            )
            swaps_24h = await swap_filter_24h.get_all_entries()
            
            swap_filter_1h = contract.events.Swap.create_filter(
                fromBlock=current_block - blocks_1h
            )
            swaps_1h = await swap_filter_1h.get_all_entries()
            
            # Calculate volumes
            volume_24h = sum(
                abs(swap['args']['amount0In'] - swap['args']['amount0Out'])
                for swap in swaps_24h
            )
            
            volume_1h = sum(
                abs(swap['args']['amount0In'] - swap['args']['amount0Out'])
                for swap in swaps_1h
            )
            
            return {
                'volume_24h': volume_24h,
                'volume_1h': volume_1h,
                'swap_count_24h': len(swaps_24h),
                'swap_count_1h': len(swaps_1h)
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting volume for pool {pool['address']}: {e}")
            return None
            
    async def _collect_price_impact(self, pool: Dict) -> Dict[str, Any]:
        """
        Calculate price impact metrics.
        
        Args:
            pool: Pool configuration dictionary
            
        Returns:
            Dictionary containing:
                - impact_1k: Price impact for $1k trade
                - impact_10k: Price impact for $10k trade
                - impact_100k: Price impact for $100k trade
        """
        try:
            # Get pool contract
            contract = self.dex_manager.get_pool_contract(
                pool['address'],
                pool['dex']
            )
            
            # Define test amounts
            amounts = [
                Web3.to_wei(1000, 'ether'),   # $1k
                Web3.to_wei(10000, 'ether'),  # $10k
                Web3.to_wei(100000, 'ether')  # $100k
            ]
            
            impacts = {}
            for amount in amounts:
                try:
                    # Get quote for test amount
                    if pool.get('version') == 'v3':
                        quote = await contract.functions.quote(
                            amount,
                            pool['fee']
                        ).call()
                    else:
                        amounts_out = await contract.functions.getAmountsOut(
                            amount,
                            [pool['token0'], pool['token1']]
                        ).call()
                        quote = amounts_out[1]
                        
                    # Calculate price impact
                    impact = abs(1 - (quote / amount))
                    impacts[f'impact_{amount/1e18:.0f}k'] = impact
                    
                except Exception as e:
                    self.logger.warning(f"Error calculating impact for amount {amount}: {e}")
                    impacts[f'impact_{amount/1e18:.0f}k'] = None
                    
            return impacts
            
        except Exception as e:
            self.logger.error(f"Error collecting price impact for pool {pool['address']}: {e}")
            return None
            
    async def _collect_concentration(self, pool: Dict) -> Dict[str, Any]:
        """
        Calculate liquidity concentration metrics.
        
        Args:
            pool: Pool configuration dictionary
            
        Returns:
            Dictionary containing concentration metrics
        """
        try:
            if pool.get('version') == 'v3':
                # For V3 pools, analyze tick distribution
                contract = self.dex_manager.get_pool_contract(
                    pool['address'],
                    pool['dex']
                )
                
                # Get current tick
                slot0 = await contract.functions.slot0().call()
                current_tick = slot0[1]
                
                # Analyze ticks around current price
                tick_spacing = pool.get('tick_spacing', 60)
                ticks_to_check = 10  # Check 10 ticks in each direction
                
                liquidity_distribution = []
                for i in range(-ticks_to_check, ticks_to_check + 1):
                    tick = current_tick + (i * tick_spacing)
                    try:
                        tick_info = await contract.functions.ticks(tick).call()
                        liquidity_distribution.append({
                            'tick': tick,
                            'liquidity_gross': tick_info[0],
                            'liquidity_net': tick_info[1]
                        })
                    except Exception as e:
                        self.logger.warning(f"Error getting tick {tick} info: {e}")
                        
                return {
                    'current_tick': current_tick,
                    'liquidity_distribution': liquidity_distribution
                }
                
            else:
                # For V2 pools, return reserve ratio
                reserves = await self._collect_reserves(pool)
                if reserves:
                    total = reserves['token0_reserve'] + reserves['token1_reserve']
                    if total > 0:
                        ratio = reserves['token0_reserve'] / total
                        return {
                            'reserve_ratio': ratio,
                            'imbalance': abs(0.5 - ratio) * 2  # 0 = perfectly balanced, 1 = max imbalance
                        }
                        
            return None
            
        except Exception as e:
            self.logger.error(f"Error collecting concentration for pool {pool['address']}: {e}")
            return None
            
    async def _collect_utilization(self, pool: Dict) -> float:
        """
        Calculate pool utilization rate.
        
        Args:
            pool: Pool configuration dictionary
            
        Returns:
            Utilization rate (0-1)
        """
        try:
            # Get recent volume
            volume = await self._collect_volume(pool)
            if not volume:
                return None
                
            # Get current reserves
            reserves = await self._collect_reserves(pool)
            if not reserves:
                return None
                
            # Calculate utilization as volume/reserves ratio
            if pool.get('version') == 'v3':
                total_liquidity = reserves['liquidity']
            else:
                total_liquidity = reserves['token0_reserve'] + reserves['token1_reserve']
                
            if total_liquidity > 0:
                utilization = volume['volume_24h'] / total_liquidity
                return min(utilization, 1.0)  # Cap at 100%
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating utilization for pool {pool['address']}: {e}")
            return None