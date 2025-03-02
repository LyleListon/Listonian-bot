"""
Flashbots Bundle Simulator

This module contains components for simulating Flashbots transaction
bundles to validate their execution and calculate expected profit.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from decimal import Decimal

from ..interfaces import Web3Client, Transaction

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """
    Result of a bundle simulation.
    
    Contains information about execution success, gas used,
    expected profit, and other simulation details.
    """
    success: bool
    gas_used: int
    profit_wei: int
    cost_wei: int
    profit_ratio: float
    error: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    coinbase_diff: Optional[int] = None
    state_block: Optional[str] = None
    block_number: Optional[int] = None
    timestamp: int = 0
    
    @property
    def is_profitable(self) -> bool:
        """Check if the simulation indicates profitability."""
        return self.success and self.profit_wei > 0 and self.profit_ratio > 0
    
    @property
    def net_profit_wei(self) -> int:
        """Calculate net profit after costs."""
        return self.profit_wei - self.cost_wei
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = int(time.time())


class BundleSimulator:
    """
    Simulator for Flashbots transaction bundles.
    
    Validates execution and calculates expected profits for
    transaction bundles before submission.
    """
    
    def __init__(
        self,
        web3_client: Web3Client,
        flashbots_provider: Any,  # Avoid circular import
        config: Dict[str, Any] = None
    ):
        """
        Initialize the bundle simulator.
        
        Args:
            web3_client: Web3 client for blockchain interactions
            flashbots_provider: Flashbots provider for simulations
            config: Configuration dictionary
        """
        self.web3_client = web3_client
        self.flashbots_provider = flashbots_provider
        self.config = config or {}
        
        # Configuration
        self.min_profit_wei = int(self.config.get("min_profit_wei", 0))
        self.min_profit_ratio = float(self.config.get("min_profit_ratio", 0.0))
        self.gas_price_buffer = float(self.config.get("gas_price_buffer", 1.1))  # 10% buffer
        self.state_block_offset = int(self.config.get("state_block_offset", 0))
        self.max_tries = int(self.config.get("max_tries", 3))
        self.retry_delay = float(self.config.get("retry_delay", 1.0))
        
        # State
        self._simulation_lock = asyncio.Lock()
        self._simulation_cache: Dict[str, SimulationResult] = {}
        self._cache_ttl = float(self.config.get("cache_ttl", 2.0))  # Cache TTL in seconds
        self._simulation_stats = {
            "total": 0,
            "successful": 0,
            "profitable": 0,
            "failed": 0,
            "errors": {}
        }
        
        logger.info("BundleSimulator initialized")
    
    async def simulate_bundle(
        self,
        bundle: List[Dict[str, Any]],
        block_number: Optional[Union[int, str]] = None,
        state_block_number: Optional[Union[int, str]] = None,
        cache_key: Optional[str] = None
    ) -> SimulationResult:
        """
        Simulate a transaction bundle and analyze the results.
        
        Args:
            bundle: List of transaction objects to simulate
            block_number: Block number to simulate on
            state_block_number: Block to use for state
            cache_key: Optional cache key for storing/retrieving results
            
        Returns:
            Simulation result including success, gas used, and profit metrics
        """
        # Update statistics
        self._simulation_stats["total"] += 1
        
        # Check cache if key provided
        if cache_key and cache_key in self._simulation_cache:
            cached_result = self._simulation_cache[cache_key]
            cache_age = time.time() - cached_result.timestamp
            
            if cache_age < self._cache_ttl:
                logger.info(f"Using cached simulation result for {cache_key} ({cache_age:.2f}s old)")
                return cached_result
        
        async with self._simulation_lock:
            logger.info(f"Simulating bundle with {len(bundle)} transactions")
            
            # Set default block numbers if not provided
            try:
                if not block_number:
                    current_block = await self.web3_client.get_block_number()
                    block_number = current_block
                
                if not state_block_number:
                    if isinstance(block_number, int):
                        state_block_number = block_number - self.state_block_offset
                    elif block_number == "latest":
                        current_block = await self.web3_client.get_block_number()
                        state_block_number = current_block - self.state_block_offset
                    else:
                        state_block_number = block_number
            
            except Exception as e:
                logger.error(f"Error getting block numbers for simulation: {e}")
                self._simulation_stats["failed"] += 1
                self._simulation_stats["errors"][str(e)] = self._simulation_stats["errors"].get(str(e), 0) + 1
                
                return SimulationResult(
                    success=False,
                    gas_used=0,
                    profit_wei=0,
                    cost_wei=0,
                    profit_ratio=0.0,
                    error=f"Block number error: {e}"
                )
            
            # Retry simulation a few times if it fails
            for attempt in range(1, self.max_tries + 1):
                try:
                    # Run simulation through Flashbots provider
                    simulation_data = await self.flashbots_provider.simulate_bundle(
                        bundle, 
                        block_number=block_number,
                        state_block_number=state_block_number
                    )
                    
                    if not simulation_data:
                        if attempt < self.max_tries:
                            logger.warning(f"Simulation attempt {attempt} returned no data, retrying...")
                            await asyncio.sleep(self.retry_delay)
                            continue
                        
                        self._simulation_stats["failed"] += 1
                        return SimulationResult(
                            success=False,
                            gas_used=0,
                            profit_wei=0,
                            cost_wei=0,
                            profit_ratio=0.0,
                            error="Simulation returned no data"
                        )
                    
                    # Analyze simulation results
                    result = self._analyze_simulation_result(simulation_data)
                    
                    # Update statistics
                    if result.success:
                        self._simulation_stats["successful"] += 1
                        if result.is_profitable:
                            self._simulation_stats["profitable"] += 1
                    else:
                        self._simulation_stats["failed"] += 1
                        if result.error:
                            self._simulation_stats["errors"][result.error] = self._simulation_stats["errors"].get(result.error, 0) + 1
                    
                    # Cache result if key provided
                    if cache_key:
                        self._simulation_cache[cache_key] = result
                        
                        # Cleanup old cache entries
                        self._cleanup_cache()
                    
                    return result
                
                except Exception as e:
                    if attempt < self.max_tries:
                        logger.warning(f"Simulation attempt {attempt} failed with error: {e}, retrying...")
                        await asyncio.sleep(self.retry_delay)
                    else:
                        logger.error(f"All simulation attempts failed: {e}")
                        self._simulation_stats["failed"] += 1
                        self._simulation_stats["errors"][str(e)] = self._simulation_stats["errors"].get(str(e), 0) + 1
                        
                        return SimulationResult(
                            success=False,
                            gas_used=0,
                            profit_wei=0,
                            cost_wei=0,
                            profit_ratio=0.0,
                            error=f"Simulation error: {e}"
                        )
    
    def _analyze_simulation_result(
        self,
        simulation_data: Dict[str, Any]
    ) -> SimulationResult:
        """
        Analyze simulation data to determine profit and success.
        
        Args:
            simulation_data: Raw simulation data from Flashbots
            
        Returns:
            Analyzed simulation result
        """
        # Default values
        success = True
        gas_used = 0
        profit_wei = 0
        cost_wei = 0
        profit_ratio = 0.0
        error = None
        tx_results = []
        coinbase_diff = 0
        block_number = None
        
        # Check for simulation error
        if "error" in simulation_data:
            success = False
            error = simulation_data["error"]
            logger.error(f"Simulation error: {error}")
            return SimulationResult(
                success=success,
                gas_used=gas_used,
                profit_wei=profit_wei,
                cost_wei=cost_wei,
                profit_ratio=profit_ratio,
                error=error
            )
        
        # Extract block number
        if "blockNumber" in simulation_data:
            try:
                block_number = int(simulation_data["blockNumber"], 16) if isinstance(simulation_data["blockNumber"], str) else int(simulation_data["blockNumber"])
            except (ValueError, TypeError):
                logger.warning(f"Could not parse block number: {simulation_data.get('blockNumber')}")
        
        # Extract transaction results
        if "results" in simulation_data:
            tx_results = simulation_data["results"]
            
            # Check if any transactions failed
            for i, tx_result in enumerate(tx_results):
                if not tx_result.get("success", True):
                    success = False
                    tx_error = tx_result.get("error", f"Transaction {i} failed")
                    error = f"Transaction failure: {tx_error}"
                    logger.warning(f"Transaction {i} failed: {tx_error}")
                
                # Sum up gas used
                if "gasUsed" in tx_result:
                    tx_gas_used = int(tx_result["gasUsed"], 16) if isinstance(tx_result["gasUsed"], str) else int(tx_result["gasUsed"])
                    gas_used += tx_gas_used
        
        # Extract coinbase difference (miner payment)
        if "coinbaseDiff" in simulation_data:
            try:
                coinbase_diff = int(simulation_data["coinbaseDiff"], 16) if isinstance(simulation_data["coinbaseDiff"], str) else int(simulation_data["coinbaseDiff"])
                profit_wei += coinbase_diff
            except (ValueError, TypeError):
                logger.warning(f"Could not parse coinbase diff: {simulation_data.get('coinbaseDiff')}")
        
        # Calculate gas cost
        if success and gas_used > 0:
            # Get gas price - prefer value from simulation, but fall back to estimation
            gas_price = 0
            
            try:
                if tx_results and "gasPrice" in tx_results[0]:
                    gas_price = int(tx_results[0]["gasPrice"], 16) if isinstance(tx_results[0]["gasPrice"], str) else int(tx_results[0]["gasPrice"])
                else:
                    # Try to get current gas price and add buffer
                    gas_price_wei = self.web3_client.get_gas_price()
                    if isinstance(gas_price_wei, int):
                        gas_price = int(gas_price_wei * self.gas_price_buffer)
                    else:
                        # Convert from async result if needed
                        if hasattr(gas_price_wei, "result"):
                            gas_price = int(gas_price_wei.result() * self.gas_price_buffer)
                
                cost_wei = gas_used * gas_price
                
                # Calculate profit metrics
                net_profit = profit_wei - cost_wei
                profit_wei = net_profit
                
                if cost_wei > 0:
                    profit_ratio = net_profit / cost_wei
                
                # Check profitability against thresholds
                if self.min_profit_wei > 0 and net_profit < self.min_profit_wei:
                    logger.warning(f"Bundle not profitable enough. Profit: {net_profit} wei, Minimum: {self.min_profit_wei} wei")
                    success = False
                    error = f"Insufficient profit: {net_profit} wei < {self.min_profit_wei} wei"
                
                if self.min_profit_ratio > 0 and profit_ratio < self.min_profit_ratio:
                    logger.warning(f"Bundle profit ratio too low. Ratio: {profit_ratio}, Minimum: {self.min_profit_ratio}")
                    success = False
                    error = f"Insufficient profit ratio: {profit_ratio} < {self.min_profit_ratio}"
                
            except Exception as e:
                logger.error(f"Error calculating gas cost: {e}")
                success = False
                error = f"Gas calculation error: {e}"
        
        # Create result object
        simulation_result = SimulationResult(
            success=success,
            gas_used=gas_used,
            profit_wei=profit_wei,
            cost_wei=cost_wei,
            profit_ratio=profit_ratio,
            error=error,
            results=tx_results,
            coinbase_diff=coinbase_diff,
            block_number=block_number,
            timestamp=int(time.time())
        )
        
        # Log summary
        if success:
            logger.info(
                f"Simulation successful: Gas used={gas_used}, "
                f"Profit={profit_wei} wei, "
                f"Ratio={profit_ratio:.3f}"
            )
        else:
            logger.warning(f"Simulation unsuccessful: {error}")
        
        return simulation_result
    
    def _cleanup_cache(self) -> None:
        """Clean up expired entries from the simulation cache."""
        current_time = time.time()
        expired_keys = [
            key for key, result in self._simulation_cache.items()
            if current_time - result.timestamp > self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._simulation_cache[key]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about simulation runs.
        
        Returns:
            Dictionary of simulation statistics
        """
        stats = self._simulation_stats.copy()
        
        # Add success rate
        if stats["total"] > 0:
            stats["success_rate"] = stats["successful"] / stats["total"]
            stats["profit_rate"] = stats["profitable"] / stats["total"]
        else:
            stats["success_rate"] = 0.0
            stats["profit_rate"] = 0.0
        
        # Add cache info
        stats["cache_size"] = len(self._simulation_cache)
        stats["cache_ttl"] = self._cache_ttl
        
        return stats
    
    def clear_cache(self) -> None:
        """Clear the simulation cache."""
        self._simulation_cache.clear()
        logger.info("Simulation cache cleared")
    
    def set_min_profit(
        self,
        min_profit_wei: Optional[int] = None,
        min_profit_ratio: Optional[float] = None
    ) -> None:
        """
        Set minimum profit thresholds for simulations.
        
        Args:
            min_profit_wei: Minimum profit in wei
            min_profit_ratio: Minimum profit to cost ratio
        """
        if min_profit_wei is not None:
            self.min_profit_wei = min_profit_wei
            logger.info(f"Set minimum profit threshold to {min_profit_wei} wei")
        
        if min_profit_ratio is not None:
            self.min_profit_ratio = min_profit_ratio
            logger.info(f"Set minimum profit ratio to {min_profit_ratio}")


async def create_bundle_simulator(
    web3_client: Web3Client,
    flashbots_provider: Any,
    config: Dict[str, Any] = None
) -> BundleSimulator:
    """
    Factory function to create a bundle simulator.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        flashbots_provider: Flashbots provider for simulations
        config: Configuration parameters
        
    Returns:
        Initialized bundle simulator
    """
    return BundleSimulator(
        web3_client=web3_client,
        flashbots_provider=flashbots_provider,
        config=config
    )