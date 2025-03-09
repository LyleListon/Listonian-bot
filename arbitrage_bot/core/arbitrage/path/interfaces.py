"""
Multi-Path Arbitrage Interfaces

This module defines the core interfaces and data structures for multi-path
arbitrage, including path representation, multi-path opportunities, and
related components.
"""

import asyncio
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Any, Optional, Set, Tuple, Union


@dataclass
class Pool:
    """
    Represents a liquidity pool on a DEX.
    
    This class encapsulates the data for a trading pair/pool on a
    decentralized exchange, including addresses, reserves, and fees.
    """
    
    address: str
    """The pool's contract address (checksummed)."""
    
    token0: str
    """Address of the first token in the pool (checksummed)."""
    
    token1: str
    """Address of the second token in the pool (checksummed)."""
    
    fee: int = 0
    """The pool's fee in basis points (e.g., 30 = 0.3%)."""
    
    reserves0: Optional[Decimal] = None
    """Reserve of token0 in the pool."""
    
    reserves1: Optional[Decimal] = None
    """Reserve of token1 in the pool."""
    
    liquidity: Optional[Decimal] = None
    """Total liquidity in the pool (may be in USD or another normalized unit)."""
    
    dex: str = ""
    """The DEX this pool belongs to (e.g., "uniswap_v3")."""
    
    version: str = ""
    """The DEX version (e.g., "v2", "v3")."""
    
    pool_type: str = ""
    """The type of pool (e.g., "constant_product", "stable", "weighted")."""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the pool."""
    
    @property
    def tokens(self) -> List[str]:
        """Get the tokens in this pool."""
        return [self.token0, self.token1]
    
    def __hash__(self) -> int:
        """Hash function to use Pool in sets/dicts."""
        return hash(self.address)


@dataclass
class ArbitragePath:
    """
    Represents a single arbitrage path.
    
    A path consists of a sequence of token addresses and the pools used to
    trade between them. A valid arbitrage path starts and ends with the same
    token.
    """
    
    tokens: List[str]
    """Sequence of token addresses in the path (checksummed)."""
    
    pools: List[Pool]
    """Sequence of pools used for trading along the path."""
    
    dexes: List[str]
    """Sequence of DEXs corresponding to each hop in the path."""
    
    swap_data: List[Dict[str, Any]] = field(default_factory=list)
    """Swap data for each hop, including calldata for execution."""
    
    optimal_amount: Optional[Decimal] = None
    """Optimal amount to trade through this path."""
    
    expected_output: Optional[Decimal] = None
    """Expected output amount when trading optimal_amount."""
    
    path_yield: float = 0.0
    """Expected return as percentage (1.0 = 100%)."""
    
    confidence: float = 0.0
    """Confidence level in the expected output (0.0-1.0)."""
    
    estimated_gas: int = 0
    """Estimated gas cost for executing this path."""
    
    estimated_gas_cost: Decimal = Decimal("0")
    """Estimated gas cost in ETH."""
    
    execution_priority: int = 0
    """Priority for execution (lower = higher priority)."""
    
    @property
    def start_token(self) -> str:
        """Get the starting token of the path."""
        return self.tokens[0]
    
    @property
    def end_token(self) -> str:
        """Get the ending token of the path."""
        return self.tokens[-1]
    
    @property
    def is_cyclic(self) -> bool:
        """Check if the path is cyclic (starts and ends with the same token)."""
        return self.start_token == self.end_token
    
    @property
    def length(self) -> int:
        """Get the number of hops in the path."""
        return len(self.pools)
    
    @property
    def profit(self) -> Optional[Decimal]:
        """Calculate the profit from this path (if applicable)."""
        if self.optimal_amount is None or self.expected_output is None:
            return None
        
        if not self.is_cyclic:
            return None
        
        return self.expected_output - self.optimal_amount


@dataclass
class MultiPathOpportunity:
    """
    Represents a multi-path arbitrage opportunity.
    
    A multi-path opportunity consists of multiple arbitrage paths that share
    the same start token, with capital allocated across them to maximize
    overall profit.
    """
    
    paths: List[ArbitragePath]
    """List of arbitrage paths in this opportunity."""
    
    start_token: str
    """Start token for all paths (checksummed)."""
    
    required_amount: Decimal
    """Total amount required for all paths."""
    
    expected_profit: Decimal
    """Expected profit from the opportunity."""
    
    allocations: List[Decimal] = field(default_factory=list)
    """Capital allocation for each path."""
    
    confidence_level: float = 0.0
    """Overall confidence level for the opportunity (0.0-1.0)."""
    
    execution_data: Dict[str, Any] = field(default_factory=dict)
    """Data needed for execution."""
    
    created_at: int = 0
    """Timestamp when the opportunity was created."""
    
    expiration: Optional[int] = None
    """Timestamp when the opportunity expires."""
    
    @property
    def is_valid(self) -> bool:
        """Check if the opportunity is valid."""
        if not self.paths:
            return False
        
        if len(self.paths) != len(self.allocations):
            return False
        
        return all(path.start_token == self.start_token for path in self.paths)
    
    @property
    def expected_output(self) -> Decimal:
        """Calculate the expected output amount."""
        return self.required_amount + self.expected_profit
    
    @property
    def profit_percentage(self) -> float:
        """Calculate the profit as a percentage."""
        if self.required_amount == 0:
            return 0.0
        
        return float(self.expected_profit / self.required_amount * 100)


class GraphExplorer:
    """
    Interface for exploring the DEX ecosystem as a graph.
    
    This class is responsible for maintaining a graph representation of the
    DEX ecosystem, including tokens as nodes and pools as edges.
    """
    
    async def initialize(self) -> bool:
        """
        Initialize the graph explorer.
        
        Returns:
            True if initialization succeeds, False otherwise
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def update_graph(self) -> None:
        """
        Update the graph with the latest pool data.
        
        This method should be called periodically to ensure the graph
        represents the current state of the DEX ecosystem.
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def get_graph(self) -> Any:
        """
        Get the current graph representation.
        
        Returns:
            A graph object (implementation-specific)
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def find_paths(
        self,
        start_token: str,
        end_token: str,
        max_length: int = 4,
        max_paths: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[List[Tuple[str, Pool]]]:
        """
        Find paths between two tokens.
        
        Args:
            start_token: Starting token address (checksummed)
            end_token: Ending token address (checksummed)
            max_length: Maximum path length (number of hops)
            max_paths: Maximum number of paths to return
            filters: Optional filters to apply to path finding
            
        Returns:
            List of paths, where each path is a list of (token, pool) tuples
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def find_cycles(
        self,
        start_token: str,
        max_length: int = 4,
        max_cycles: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[List[Tuple[str, Pool]]]:
        """
        Find cycles starting and ending at the given token.
        
        Args:
            start_token: Starting/ending token address (checksummed)
            max_length: Maximum cycle length (number of hops)
            max_cycles: Maximum number of cycles to return
            filters: Optional filters to apply to cycle finding
            
        Returns:
            List of cycles, where each cycle is a list of (token, pool) tuples
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def close(self) -> None:
        """Close the graph explorer and clean up resources."""
        raise NotImplementedError("Method must be implemented by subclass")


class PathFinder:
    """
    Interface for finding arbitrage paths.
    
    This class is responsible for identifying profitable arbitrage paths
    using the graph explorer.
    """
    
    async def initialize(self) -> bool:
        """
        Initialize the path finder.
        
        Returns:
            True if initialization succeeds, False otherwise
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
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
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def evaluate_path(self, path: ArbitragePath) -> ArbitragePath:
        """
        Evaluate an arbitrage path to determine its profitability.
        
        This method should calculate the optimal input amount, expected output,
        and other metrics for the path.
        
        Args:
            path: Arbitrage path to evaluate
            
        Returns:
            Evaluated arbitrage path
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
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
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def close(self) -> None:
        """Close the path finder and clean up resources."""
        raise NotImplementedError("Method must be implemented by subclass")


class PathOptimizer:
    """
    Interface for optimizing capital allocation across multiple paths.
    
    This class is responsible for determining the optimal distribution of
    capital across multiple arbitrage paths to maximize overall profit.
    """
    
    async def initialize(self) -> bool:
        """
        Initialize the path optimizer.
        
        Returns:
            True if initialization succeeds, False otherwise
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def optimize_allocation(
        self,
        paths: List[ArbitragePath],
        total_capital: Decimal,
        optimization_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Decimal], Decimal]:
        """
        Optimize capital allocation across multiple paths.
        
        Args:
            paths: List of arbitrage paths to allocate capital across
            total_capital: Total capital available for allocation
            optimization_params: Additional parameters for optimization
            
        Returns:
            Tuple of (allocations, expected_profit), where allocations is a
            list of allocated amounts for each path, and expected_profit is
            the expected total profit
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def create_opportunity(
        self,
        paths: List[ArbitragePath],
        allocations: List[Decimal],
        expected_profit: Decimal,
        start_token: str
    ) -> MultiPathOpportunity:
        """
        Create a multi-path opportunity from the optimized allocation.
        
        Args:
            paths: List of arbitrage paths
            allocations: Optimized capital allocations for each path
            expected_profit: Expected total profit
            start_token: Starting token address (checksummed)
            
        Returns:
            Multi-path arbitrage opportunity
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def close(self) -> None:
        """Close the path optimizer and clean up resources."""
        raise NotImplementedError("Method must be implemented by subclass")