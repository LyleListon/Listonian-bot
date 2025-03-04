"""
Path Finder Implementation

This module provides a concrete implementation of the PathFinder interface
for discovering and evaluating arbitrage paths.
"""

import asyncio
import logging
import time
import math
from decimal import Decimal
from typing import List, Dict, Any, Optional, Set, Tuple, Union, cast

from web3 import Web3

from ...dex.interfaces import DexManager
from ...price.interfaces import PriceFetcher
from ...utils.decimal import format_decimal
from .interfaces import (
    PathFinder,
    GraphExplorer,
    ArbitragePath,
    MultiPathOpportunity,
    Pool
)
from .graph_explorer import NetworkXGraphExplorer
from .path_optimizer import MonteCarloPathOptimizer

logger = logging.getLogger(__name__)


class MultiPathFinder(PathFinder):
    """
    Implementation of the PathFinder interface for multi-path arbitrage.
    
    This class uses the graph explorer to find potential arbitrage paths
    and evaluates them to determine profitability.
    """
    
    def __init__(
        self,
        graph_explorer: GraphExplorer,
        dex_manager: DexManager,
        price_fetcher: Optional[PriceFetcher] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the multi-path finder.
        
        Args:
            graph_explorer: Graph explorer for finding paths
            dex_manager: Manager for DEX interactions
            price_fetcher: Optional price fetcher for price data
            config: Configuration parameters
        """
        self.graph_explorer = graph_explorer
        self.dex_manager = dex_manager
        self.price_fetcher = price_fetcher
        self.config = config or {}
        
        # Extract configuration parameters
        self.max_path_length = self.config.get("max_path_length", 4)
        self.max_paths = self.config.get("max_paths", 100)
        self.min_profit_threshold = Decimal(self.config.get("min_profit_threshold", "0.001"))
        self.min_profit_percentage = Decimal(self.config.get("min_profit_percentage", "0.001"))
        self.gas_price_buffer = Decimal(self.config.get("gas_price_buffer", "1.1"))
        self.slippage_tolerance = Decimal(self.config.get("slippage_tolerance", "0.005"))
        
        # Create optimizer
        optimizer_config = self.config.get("optimizer", {})
        self.optimizer = MonteCarloPathOptimizer(
            dex_manager=dex_manager,
            price_fetcher=price_fetcher,
            config=optimizer_config
        )
        
        # State
        self._initialized = False
        self._initialization_lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """
        Initialize the path finder.
        
        Returns:
            True if initialization succeeds, False otherwise
        """
        async with self._initialization_lock:
            if self._initialized:
                return True
            
            try:
                logger.info("Initializing multi-path finder")
                
                # Initialize graph explorer
                if not isinstance(self.graph_explorer, NetworkXGraphExplorer):
                    logger.error("Graph explorer is not a NetworkXGraphExplorer instance")
                    return False
                
                if not await self.graph_explorer.initialize():
                    logger.error("Failed to initialize graph explorer")
                    return False
                
                # Initialize optimizer
                if not await self.optimizer.initialize():
                    logger.error("Failed to initialize optimizer")
                    return False
                
                self._initialized = True
                logger.info("Multi-path finder initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize multi-path finder: {e}")
                return False
    
    async def find_paths(
        self,
        start_token: str,
        max_paths: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ArbitragePath]:
        """
        Find arbitrage paths starting and ending at the given token.
        
        Args:
            start_token: Starting/ending token address (checksummed)
            max_paths: Maximum number of paths to return
            filters: Optional filters to apply to path finding
            
        Returns:
            List of arbitrage paths
        """
        await self._ensure_initialized()
        
        # Ensure token is checksummed
        start_token = Web3.to_checksum_address(start_token)
        
        # Set default filters if not provided
        filters = filters or {}
        
        try:
            # Find cycles using graph explorer
            max_length = filters.get("max_length", self.max_path_length)
            
            logger.info(f"Finding arbitrage paths for {start_token}")
            cycles = await self.graph_explorer.find_cycles(
                start_token=start_token,
                max_length=max_length,
                max_cycles=max_paths * 2,  # Get extra cycles to account for filtering
                filters=filters
            )
            
            if not cycles:
                logger.info(f"No cycles found for {start_token}")
                return []
            
            logger.info(f"Found {len(cycles)} cycles for {start_token}")
            
            # Convert cycles to arbitrage paths
            paths = []
            
            for cycle in cycles:
                path = await self._cycle_to_path(cycle)
                if path:
                    paths.append(path)
            
            logger.info(f"Converted {len(paths)} cycles to arbitrage paths")
            
            # Evaluate paths for profitability
            evaluated_paths = []
            
            for path in paths:
                evaluated_path = await self.evaluate_path(path)
                if evaluated_path and evaluated_path.profit and evaluated_path.profit > 0:
                    evaluated_paths.append(evaluated_path)
            
            logger.info(f"Found {len(evaluated_paths)} profitable paths")
            
            # Sort by profit yield and return the top paths
            evaluated_paths.sort(key=lambda p: p.path_yield, reverse=True)
            return evaluated_paths[:max_paths]
            
        except Exception as e:
            logger.error(f"Error finding paths: {e}")
            return []
    
    async def evaluate_path(self, path: ArbitragePath) -> ArbitragePath:
        """
        Evaluate an arbitrage path to determine its profitability.
        
        This method calculates the optimal input amount, expected output,
        and other metrics for the path.
        
        Args:
            path: Arbitrage path to evaluate
            
        Returns:
            Evaluated arbitrage path
        """
        await self._ensure_initialized()
        
        try:
            # Skip paths that are too short or not cyclic
            if len(path.pools) < 2 or not path.is_cyclic:
                logger.debug("Path is too short or not cyclic")
                return path
            
            # Get optimal amount and expected output
            optimal_amount, expected_output, confidence = await self._calculate_optimal_amount(path)
            
            if optimal_amount <= 0 or expected_output <= optimal_amount:
                logger.debug(f"Path is not profitable: input={optimal_amount}, output={expected_output}")
                return path
            
            # Calculate gas cost
            estimated_gas, estimated_gas_cost = await self._estimate_gas_cost(path)
            
            # Calculate profit
            profit = expected_output - optimal_amount
            
            # Calculate profit yield
            path_yield = float(profit / optimal_amount) if optimal_amount > 0 else 0.0
            
            # Update path with calculated values
            path.optimal_amount = optimal_amount
            path.expected_output = expected_output
            path.path_yield = path_yield
            path.confidence = confidence
            path.estimated_gas = estimated_gas
            path.estimated_gas_cost = estimated_gas_cost
            
            logger.debug(
                f"Path evaluated: input={format_decimal(optimal_amount)}, "
                f"output={format_decimal(expected_output)}, "
                f"profit={format_decimal(profit)}, "
                f"yield={path_yield:.4f}, "
                f"gas={estimated_gas}, "
                f"gas_cost={format_decimal(estimated_gas_cost)}"
            )
            
            return path
            
        except Exception as e:
            logger.error(f"Error evaluating path: {e}")
            return path
    
    async def find_opportunities(
        self,
        start_token: str,
        max_opportunities: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[MultiPathOpportunity]:
        """
        Find multi-path arbitrage opportunities.
        
        Args:
            start_token: Starting token address (checksummed)
            max_opportunities: Maximum number of opportunities to return
            filters: Optional filters to apply to opportunity finding
            
        Returns:
            List of multi-path arbitrage opportunities
        """
        await self._ensure_initialized()
        
        # Ensure token is checksummed
        start_token = Web3.to_checksum_address(start_token)
        
        # Set default filters if not provided
        filters = filters or {}
        
        try:
            # Find profitable paths
            paths = await self.find_paths(
                start_token=start_token,
                max_paths=self.max_paths,
                filters=filters
            )
            
            if not paths:
                logger.info(f"No profitable paths found for {start_token}")
                return []
            
            logger.info(f"Found {len(paths)} profitable paths for {start_token}")
            
            # Filter paths by minimum profit percentage
            min_profit_percentage = filters.get(
                "min_profit_percentage",
                self.min_profit_percentage
            )
            
            filtered_paths = [
                p for p in paths
                if p.path_yield >= float(min_profit_percentage)
            ]
            
            logger.info(
                f"Filtered to {len(filtered_paths)} paths with "
                f"yield >= {min_profit_percentage}"
            )
            
            if not filtered_paths:
                return []
            
            # Group paths by common characteristics
            grouped_paths = self._group_paths(filtered_paths)
            
            # Create opportunities
            opportunities = []
            
            for i, group in enumerate(grouped_paths):
                if i >= max_opportunities:
                    break
                
                # Get capital allocation for the group
                capital_available = await self._get_available_capital(start_token)
                
                # Optimize allocation
                allocations, expected_profit = await self.optimizer.optimize_allocation(
                    paths=group,
                    total_capital=capital_available
                )
                
                # Create opportunity
                if expected_profit > 0:
                    opportunity = await self.optimizer.create_opportunity(
                        paths=group,
                        allocations=allocations,
                        expected_profit=expected_profit,
                        start_token=start_token
                    )
                    
                    opportunities.append(opportunity)
            
            logger.info(f"Created {len(opportunities)} multi-path opportunities")
            
            # Sort by expected profit and return
            opportunities.sort(key=lambda o: o.expected_profit, reverse=True)
            return opportunities[:max_opportunities]
            
        except Exception as e:
            logger.error(f"Error finding opportunities: {e}")
            return []
    
    async def close(self) -> None:
        """Close the path finder and clean up resources."""
        logger.info("Closing multi-path finder")
        
        if hasattr(self, 'optimizer') and self.optimizer:
            await self.optimizer.close()
        
        if hasattr(self, 'graph_explorer') and self.graph_explorer:
            await self.graph_explorer.close()
        
        self._initialized = False
    
    async def _cycle_to_path(
        self,
        cycle: List[Tuple[str, Pool]]
    ) -> Optional[ArbitragePath]:
        """
        Convert a cycle of (token, pool) tuples to an arbitrage path.
        
        Args:
            cycle: Cycle as a list of (token, pool) tuples
            
        Returns:
            ArbitragePath or None if conversion fails
        """
        try:
            if not cycle:
                return None
            
            # Extract tokens and pools
            tokens = [token for token, _ in cycle]
            pools = [pool for _, pool in cycle[:-1]]  # Last pool is None
            
            # Add the start token again to make a complete cycle
            tokens.append(tokens[0])
            
            # Get dexes
            dexes = [pool.dex for pool in pools]
            
            # Create swap data for each hop
            swap_data = []
            
            for i, pool in enumerate(pools):
                token_from = tokens[i]
                token_to = tokens[i + 1]
                
                # Get DEX instance
                dex = await self.dex_manager.get_dex(pool.dex)
                if not dex:
                    logger.warning(f"DEX not found: {pool.dex}")
                    continue
                
                # Create swap data
                try:
                    data = await dex.get_swap_data(
                        token_from=token_from,
                        token_to=token_to,
                        pool=pool
                    )
                    
                    swap_data.append(data)
                except Exception as e:
                    logger.warning(f"Failed to get swap data: {e}")
                    continue
            
            # Create arbitrage path
            return ArbitragePath(
                tokens=tokens,
                pools=pools,
                dexes=dexes,
                swap_data=swap_data
            )
            
        except Exception as e:
            logger.error(f"Error converting cycle to path: {e}")
            return None
    
    async def _calculate_optimal_amount(
        self,
        path: ArbitragePath
    ) -> Tuple[Decimal, Decimal, float]:
        """
        Calculate the optimal amount to trade through a path.
        
        This method uses numerical optimization to find the amount that
        maximizes profit for the given path.
        
        Args:
            path: Arbitrage path to optimize
            
        Returns:
            Tuple of (optimal_amount, expected_output, confidence)
        """
        # Start with a small amount
        start_token = path.start_token
        
        # Get token details
        token_info = await self._get_token_info(start_token)
        if not token_info:
            return Decimal("0"), Decimal("0"), 0.0
        
        decimals = token_info.get("decimals", 18)
        
        # Initial amounts to try
        test_amounts = [
            Decimal("0.1") * Decimal(10 ** decimals),
            Decimal("1") * Decimal(10 ** decimals),
            Decimal("10") * Decimal(10 ** decimals),
            Decimal("100") * Decimal(10 ** decimals),
        ]
        
        best_amount = Decimal("0")
        best_output = Decimal("0")
        best_profit = Decimal("0")
        
        # Try each amount
        for amount in test_amounts:
            try:
                # Simulate each swap in the path
                current_amount = amount
                confidence_product = 1.0
                
                for i, (token_from, token_to) in enumerate(zip(path.tokens[:-1], path.tokens[1:])):
                    pool = path.pools[i]
                    dex = await self.dex_manager.get_dex(pool.dex)
                    
                    if not dex:
                        logger.warning(f"DEX not found: {pool.dex}")
                        current_amount = Decimal("0")
                        break
                    
                    # Get quote
                    quote_result = await dex.get_quote(
                        token_from=token_from,
                        token_to=token_to,
                        amount=current_amount,
                        pool=pool
                    )
                    
                    if not quote_result or quote_result.get("amount_out", 0) <= 0:
                        logger.warning(f"Failed to get quote for {token_from} -> {token_to}")
                        current_amount = Decimal("0")
                        break
                    
                    # Update current amount and confidence
                    current_amount = Decimal(str(quote_result.get("amount_out", 0)))
                    confidence = quote_result.get("confidence", 0.95)
                    confidence_product *= confidence
                
                # Calculate profit
                if current_amount > amount:
                    profit = current_amount - amount
                    
                    if profit > best_profit:
                        best_amount = amount
                        best_output = current_amount
                        best_profit = profit
                
            except Exception as e:
                logger.warning(f"Error simulating amount {amount}: {e}")
        
        # If no profitable amount found, return zeros
        if best_profit <= 0:
            return Decimal("0"), Decimal("0"), 0.0
        
        return best_amount, best_output, confidence_product
    
    async def _estimate_gas_cost(
        self,
        path: ArbitragePath
    ) -> Tuple[int, Decimal]:
        """
        Estimate the gas cost for executing a path.
        
        Args:
            path: Arbitrage path to estimate gas for
            
        Returns:
            Tuple of (estimated_gas, estimated_gas_cost_in_eth)
        """
        # Base gas cost for transaction
        base_gas = 21000
        
        # Gas for each swap
        swap_gas = 0
        
        for i, pool in enumerate(path.pools):
            dex_name = path.dexes[i]
            
            # Get DEX instance
            dex = await self.dex_manager.get_dex(dex_name)
            if not dex:
                logger.warning(f"DEX not found: {dex_name}")
                continue
            
            # Get gas estimate for the swap
            try:
                gas_estimate = await dex.estimate_swap_gas(
                    token_from=path.tokens[i],
                    token_to=path.tokens[i + 1],
                    amount=path.optimal_amount if path.optimal_amount else Decimal("0"),
                    pool=pool
                )
                
                swap_gas += gas_estimate
                
            except Exception as e:
                logger.warning(f"Failed to estimate gas: {e}")
                # Use a default estimate
                swap_gas += 150000
        
        # Total gas
        total_gas = base_gas + swap_gas
        
        # Get current gas price
        gas_price = await self._get_gas_price()
        
        # Apply buffer
        gas_price_with_buffer = gas_price * self.gas_price_buffer
        
        # Calculate cost in ETH
        gas_cost = Decimal(total_gas) * gas_price_with_buffer / Decimal(10 ** 18)
        
        return total_gas, gas_cost
    
    async def _get_gas_price(self) -> Decimal:
        """
        Get the current gas price.
        
        Returns:
            Gas price in wei as Decimal
        """
        try:
            # Try to get from dex manager
            gas_price = await self.dex_manager.get_gas_price()
            if gas_price:
                return Decimal(gas_price)
            
            # Use default if not available
            return Decimal("50000000000")  # 50 gwei
            
        except Exception as e:
            logger.error(f"Error getting gas price: {e}")
            return Decimal("50000000000")  # 50 gwei
    
    async def _get_token_info(
        self,
        token_address: str
    ) -> Dict[str, Any]:
        """
        Get information about a token.
        
        Args:
            token_address: Token address (checksummed)
            
        Returns:
            Token information dictionary
        """
        try:
            # Try to get from dex manager
            token_info = await self.dex_manager.get_token_info(token_address)
            if token_info:
                return token_info
            
            # Use default if not available
            return {
                "address": token_address,
                "symbol": "TOKEN",
                "name": "Unknown Token",
                "decimals": 18
            }
            
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return {
                "address": token_address,
                "symbol": "TOKEN",
                "name": "Unknown Token",
                "decimals": 18
            }
    
    async def _get_available_capital(
        self,
        token_address: str
    ) -> Decimal:
        """
        Get the available capital for a token.
        
        Args:
            token_address: Token address (checksummed)
            
        Returns:
            Available capital as Decimal
        """
        try:
            # Get from config
            default_capital = self.config.get("default_capital", {})
            default_amount = default_capital.get(token_address, "10")
            
            # Convert to Decimal
            return Decimal(default_amount)
            
        except Exception as e:
            logger.error(f"Error getting available capital: {e}")
            return Decimal("10")  # Default to 10 tokens
    
    def _group_paths(
        self,
        paths: List[ArbitragePath]
    ) -> List[List[ArbitragePath]]:
        """
        Group paths by common characteristics for multi-path opportunities.
        
        Args:
            paths: List of paths to group
            
        Returns:
            List of path groups
        """
        # Sort paths by yield
        sorted_paths = sorted(paths, key=lambda p: p.path_yield, reverse=True)
        
        # Group by common tokens
        token_groups: Dict[Tuple[str, ...], List[ArbitragePath]] = {}
        
        for path in sorted_paths:
            # Create a token set as the group key
            token_set = tuple(sorted(set(path.tokens)))
            
            if token_set in token_groups:
                token_groups[token_set].append(path)
            else:
                token_groups[token_set] = [path]
        
        # For each token group, further group by DEX
        result = []
        
        for token_group in token_groups.values():
            # Take top paths from each token group
            top_paths = token_group[:5]
            
            # Add as a group
            if top_paths:
                result.append(top_paths)
        
        # Return groups sorted by best path yield
        result.sort(key=lambda group: max(p.path_yield for p in group), reverse=True)
        return result
    
    async def _ensure_initialized(self) -> None:
        """Ensure the path finder is initialized."""
        if not self._initialized:
            if not await self.initialize():
                raise RuntimeError("Failed to initialize multi-path finder")