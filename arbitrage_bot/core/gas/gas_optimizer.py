"""Gas optimization for arbitrage operations."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from decimal import Decimal
import json
import os
from web3 import Web3

logger = logging.getLogger(__name__)

class GasOptimizer:
    """
    Optimizes gas usage for arbitrage operations.
    
    Provides accurate gas estimation for different DEXes, tokens, and path complexities
    based on historical data and network conditions.
    """
    
    def __init__(self, web3_manager: Any, config: Dict[str, Any]):
        """
        Initialize gas optimizer.
        
        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        
        # Configuration
        gas_config = config.get('gas_optimization', {})
        self.enabled = gas_config.get('enabled', True)
        self.cache_ttl = gas_config.get('cache_ttl', 300)  # 5 minutes
        self.history_file = gas_config.get('history_file', 'data/gas_history.json')
        self.min_data_points = gas_config.get('min_data_points', 5)
        self.max_gas_limit_increase = gas_config.get('max_gas_limit_increase', 1.5)  # 50% max increase
        
        # Base gas costs for different operations
        self.base_costs = {
            'swap': gas_config.get('base_swap_cost', 150000),
            'multi_hop_base': gas_config.get('multi_hop_base_cost', 180000),
            'hop_cost': gas_config.get('additional_hop_cost', 50000),
            'v2_swap': gas_config.get('v2_swap_cost', 120000),
            'v3_swap': gas_config.get('v3_swap_cost', 150000),
            'approval': gas_config.get('approval_cost', 60000),
            'flash_loan': gas_config.get('flash_loan_cost', 200000)
        }
        
        # DEX-specific adjustment factors (multipliers)
        self.dex_factors = gas_config.get('dex_factors', {
            'baseswap': 1.0,
            'baseswap_v3': 1.1,
            'pancakeswap': 1.05,
            'rocketswap_v3': 1.15,
            'swapbased': 1.0
        })
        
        # Token-specific adjustment factors (multipliers)
        self.token_factors = {}
        self.problematic_tokens = set(gas_config.get('problematic_tokens', []))
        
        # Gas usage history for learning
        self.gas_history: Dict[str, List[Dict[str, Any]]] = {}
        self.operations_count = 0
        
        # Cache for recent estimates
        self.estimate_cache: Dict[str, Tuple[int, float]] = {}  # (estimate, timestamp)
        
        # Lock for synchronization
        self._lock = asyncio.Lock()
        
        # Load historical data if available
        self._load_history()
        
        logger.info("Gas optimizer initialized")
    
    def _load_history(self) -> None:
        """Load gas usage history from file if available."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.gas_history = data.get('history', {})
                    self.operations_count = data.get('operations_count', 0)
                    logger.info(f"Loaded gas history with {self.operations_count} operations")
        except Exception as e:
            logger.error(f"Failed to load gas history: {e}")
    
    async def save_history(self) -> None:
        """Save gas usage history to file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            
            async with self._lock:
                with open(self.history_file, 'w') as f:
                    json.dump({
                        'history': self.gas_history,
                        'operations_count': self.operations_count,
                        'timestamp': time.time()
                    }, f, indent=2)
                logger.debug("Saved gas history")
        except Exception as e:
            logger.error(f"Failed to save gas history: {e}")
    
    async def record_gas_usage(
        self,
        operation_type: str,
        dex_name: str,
        token_addresses: List[str],
        gas_used: int,
        success: bool = True,
        path_length: int = 2
    ) -> None:
        """
        Record actual gas usage for an operation.
        
        Args:
            operation_type: Type of operation (swap, approval, etc.)
            dex_name: Name of the DEX used
            token_addresses: List of token addresses involved
            gas_used: Actual gas used
            success: Whether the operation was successful
            path_length: Number of tokens in the path
        """
        if not self.enabled:
            return
        
        async with self._lock:
            # Create operation key
            key = f"{operation_type}:{dex_name}:{path_length}"
            
            # Create entry
            entry = {
                'timestamp': time.time(),
                'gas_used': gas_used,
                'token_addresses': token_addresses,
                'success': success,
                'path_length': path_length
            }
            
            # Add to history
            if key not in self.gas_history:
                self.gas_history[key] = []
            
            self.gas_history[key].append(entry)
            self.operations_count += 1
            
            # Update token factors
            await self._update_token_factors(token_addresses, gas_used, success)
            
            # Save history periodically (every 10 operations)
            if self.operations_count % 10 == 0:
                await self.save_history()
    
    async def _update_token_factors(
        self,
        token_addresses: List[str],
        gas_used: int,
        success: bool
    ) -> None:
        """
        Update token-specific gas factors.
        
        Args:
            token_addresses: Token addresses involved
            gas_used: Gas used
            success: Whether operation was successful
        """
        # Skip if operation failed
        if not success:
            return
        
        # Calculate baseline gas for comparison
        baseline = self.base_costs.get('swap', 150000)
        if gas_used < baseline:
            return  # Skip if gas used is less than baseline
        
        # Calculate excessive gas usage
        excess_ratio = gas_used / baseline
        
        # Update token factors
        for token in token_addresses:
            if token not in self.token_factors:
                self.token_factors[token] = 1.0
            
            # If gas usage is excessive, gradually increase the token factor
            if excess_ratio > 1.2:  # 20% more than baseline
                # Increase factor by 5% of the excess
                self.token_factors[token] += (excess_ratio - 1.0) * 0.05
                
                # Cap at reasonable limit
                self.token_factors[token] = min(self.token_factors[token], 2.0)
                
                # Add to problematic tokens list if factor is high
                if self.token_factors[token] > 1.3:
                    self.problematic_tokens.add(token)
                    logger.warning(f"Token {token} marked as problematic with factor {self.token_factors[token]}")
    
    async def _get_current_gas_price(self) -> int:
        """Get current gas price with caching."""
        try:
            return await self.web3_manager.w3.eth.gas_price
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            return 20000000000  # Fallback to 20 gwei
    
    async def estimate_gas_for_path(
        self,
        path: List[str],
        dex_name: str,
        operation_type: str = 'swap'
    ) -> int:
        """
        Estimate gas for a given path.
        
        Args:
            path: List of token addresses in the path
            dex_name: Name of the DEX
            operation_type: Type of operation
            
        Returns:
            Estimated gas limit
        """
        if not self.enabled:
            # Return default estimates if optimizer is disabled
            if operation_type == 'swap':
                return self.base_costs['swap']
            elif operation_type == 'multi_hop':
                return self.base_costs['multi_hop_base'] + (len(path) - 2) * self.base_costs['hop_cost']
            else:
                return self.base_costs.get(operation_type, 150000)
        
        # Check cache first
        cache_key = f"{dex_name}:{operation_type}:{','.join(path)}"
        if cache_key in self.estimate_cache:
            estimate, timestamp = self.estimate_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return estimate
        
        # Get historical data for this operation
        key = f"{operation_type}:{dex_name}:{len(path)}"
        histories = self.gas_history.get(key, [])
        
        # Base gas calculation
        if operation_type == 'multi_hop' or len(path) > 2:
            # Multi-hop calculation
            base_gas = self.base_costs['multi_hop_base'] + (len(path) - 2) * self.base_costs['hop_cost']
        else:
            # Single hop calculation
            base_gas = self.base_costs.get(operation_type, self.base_costs['swap'])
        
        # Apply DEX-specific factor
        dex_factor = self.dex_factors.get(dex_name, 1.0)
        gas_estimate = base_gas * dex_factor
        
        # Apply token-specific factors
        token_factor = 1.0
        problematic_count = 0
        
        for token in path:
            # Check if token is in problematic list
            if token in self.problematic_tokens:
                problematic_count += 1
            
            # Apply known token factor
            if token in self.token_factors:
                token_factor = max(token_factor, self.token_factors[token])
        
        # Apply token factor
        gas_estimate *= token_factor
        
        # Extra gas for problematic tokens
        if problematic_count > 0:
            gas_estimate *= (1.0 + (0.1 * problematic_count))
        
        # Learn from historical data if available
        if len(histories) >= self.min_data_points:
            # Calculate average and max from successful operations
            successful_ops = [h for h in histories if h.get('success', False)]
            if successful_ops:
                gas_amounts = [h['gas_used'] for h in successful_ops]
                avg_gas = sum(gas_amounts) / len(gas_amounts)
                max_gas = max(gas_amounts)
                
                # Blend historical data with base calculation
                historical_weight = min(0.7, len(successful_ops) / 20)  # Cap at 70% weight
                gas_estimate = (gas_estimate * (1 - historical_weight)) + (avg_gas * historical_weight)
                
                # Add a safety margin based on variability
                if max_gas > avg_gas * 1.2:  # High variability
                    gas_estimate = gas_estimate * 1.15  # Add 15% safety margin
                else:
                    gas_estimate = gas_estimate * 1.1  # Add 10% safety margin
        else:
            # Add higher safety margin when no historical data
            gas_estimate = gas_estimate * 1.2  # Add 20% safety margin
        
        # Cap the gas limit increase
        original_base = base_gas * dex_factor
        max_allowed = original_base * self.max_gas_limit_increase
        gas_estimate = min(gas_estimate, max_allowed)
        
        # Round to nearest 10000
        gas_limit = int(round(gas_estimate / 10000) * 10000)
        
        # Ensure minimum gas limit
        gas_limit = max(gas_limit, base_gas)
        
        # Cache the estimate
        self.estimate_cache[cache_key] = (gas_limit, time.time())
        
        return gas_limit
    
    async def estimate_multi_hop_gas(
        self,
        path: List[str],
        dex_name: str
    ) -> int:
        """
        Estimate gas for a multi-hop path.
        
        Args:
            path: List of token addresses in the path
            dex_name: Name of the DEX
            
        Returns:
            Estimated gas limit
        """
        return await self.estimate_gas_for_path(path, dex_name, 'multi_hop')
    
    async def estimate_optimal_gas_price(self) -> int:
        """
        Estimate optimal gas price based on network conditions.
        
        Returns:
            Optimal gas price in wei
        """
        try:
            # Get current gas price
            current_gas_price = await self._get_current_gas_price()
            
            # Get network congestion factor (placeholder for future implementation)
            # This could use an EIP-1559 aware implementation in the future
            congestion_factor = 1.0
            
            # Check if we want to prioritize the transaction
            priority_factor = self.config.get('gas_optimization', {}).get('priority_factor', 1.05)
            
            # Calculate optimal gas price
            optimal_gas_price = int(current_gas_price * congestion_factor * priority_factor)
            
            return optimal_gas_price
            
        except Exception as e:
            logger.error(f"Failed to estimate optimal gas price: {e}")
            return 20000000000  # Default to 20 gwei
    
    async def get_token_gas_factor(self, token_address: str) -> float:
        """
        Get gas factor for a specific token.
        
        Args:
            token_address: Token address
            
        Returns:
            Gas factor (multiplier)
        """
        return self.token_factors.get(token_address, 1.0)
    
    async def is_token_problematic(self, token_address: str) -> bool:
        """
        Check if a token is known to cause gas issues.
        
        Args:
            token_address: Token address
            
        Returns:
            True if token is problematic
        """
        return token_address in self.problematic_tokens
    
    async def get_gas_metrics(self) -> Dict[str, Any]:
        """
        Get gas usage metrics.
        
        Returns:
            Dictionary of gas metrics
        """
        metrics = {
            'operations_recorded': self.operations_count,
            'problematic_tokens': len(self.problematic_tokens),
            'average_by_operation_type': {},
            'dex_factors': self.dex_factors.copy(),
            'cache_entries': len(self.estimate_cache)
        }
        
        # Calculate averages by operation type
        for key, histories in self.gas_history.items():
            if not histories:
                continue
                
            successful_ops = [h for h in histories if h.get('success', False)]
            if successful_ops:
                avg_gas = sum(h['gas_used'] for h in successful_ops) / len(successful_ops)
                metrics['average_by_operation_type'][key] = int(avg_gas)
        
        return metrics
    
    @staticmethod
    async def create_gas_optimizer(
        web3_manager: Any,
        config: Dict[str, Any]
    ) -> 'GasOptimizer':
        """
        Create and initialize a gas optimizer.
        
        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary
            
        Returns:
            Initialized GasOptimizer
        """
        optimizer = GasOptimizer(web3_manager, config)
        return optimizer
