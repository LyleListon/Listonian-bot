"""
Graph Explorer Implementation

This module provides a concrete implementation of the GraphExplorer interface
using NetworkX for efficient graph operations and path finding.
"""

import asyncio
import logging
import time
from math import log
from decimal import Decimal
from typing import List, Dict, Any, Optional, Set, Tuple, Union, Iterable, cast

import networkx as nx
from web3 import Web3

from ...utils.cache import TTLCache
from ...dex.interfaces import DexManager
from ...price.interfaces import PriceFetcher
from .interfaces import GraphExplorer, Pool

logger = logging.getLogger(__name__)


class NetworkXGraphExplorer(GraphExplorer):
    """
    Graph explorer implementation using NetworkX.
    
    This class maintains a graph of the DEX ecosystem using NetworkX, with
    tokens as nodes and pools as edges, enabling efficient path finding and
    arbitrage detection.
    """
    
    def __init__(
        self,
        dex_manager: DexManager,
        price_fetcher: Optional[PriceFetcher] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the NetworkX graph explorer.
        
        Args:
            dex_manager: Manager for DEX interactions
            price_fetcher: Optional price fetcher for price data
            config: Configuration parameters
        """
        self.dex_manager = dex_manager
        self.price_fetcher = price_fetcher
        self.config = config or {}
        
        # Extract configuration parameters
        self.graph_ttl = self.config.get("graph_ttl", 60)  # seconds
        self.max_pools_per_dex = self.config.get("max_pools_per_dex", 1000)
        self.min_liquidity = Decimal(self.config.get("min_liquidity", "1000"))  # $1000 minimum liquidity
        self.include_stable_tokens = self.config.get("include_stable_tokens", True)
        self.include_wrapped_tokens = self.config.get("include_wrapped_tokens", True)
        self.max_path_length = self.config.get("max_path_length", 4)
        
        # Token filters
        self.excluded_tokens = set(self.config.get("excluded_tokens", []))
        self.included_tokens = set(self.config.get("included_tokens", []))
        
        # Initialize graph
        self.graph = nx.DiGraph()
        
        # Cache for pool data
        self.pool_cache = TTLCache(ttl=self.graph_ttl)
        
        # State
        self._initialized = False
        self._initialization_lock = asyncio.Lock()
        self._last_update = 0
    
    async def initialize(self) -> bool:
        """
        Initialize the graph explorer.
        
        Returns:
            True if initialization succeeds, False otherwise
        """
        async with self._initialization_lock:
            if self._initialized:
                return True
            
            try:
                logger.info("Initializing graph explorer")
                
                # Initialize DEX manager
                if not await self.dex_manager.is_initialized():
                    if not await self.dex_manager.initialize():
                        logger.error("Failed to initialize DEX manager")
                        return False
                
                # Get list of supported DEXes
                dexes = await self.dex_manager.get_supported_dexes()
                logger.info(f"Found {len(dexes)} supported DEXes")
                
                # Build initial graph
                await self.update_graph()
                
                self._initialized = True
                logger.info(f"Graph explorer initialized with {len(self.graph.nodes)} tokens and {len(self.graph.edges)} pools")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize graph explorer: {e}")
                return False
    
    async def update_graph(self) -> None:
        """
        Update the graph with the latest pool data.
        
        This method fetches the latest pool data from all supported DEXes
        and updates the graph accordingly.
        """
        try:
            # Check if update is needed
            current_time = time.time()
            if current_time - self._last_update < self.graph_ttl:
                logger.debug("Graph is still fresh, skipping update")
                return
            
            logger.info("Updating graph with latest pool data")
            
            # Get list of supported DEXes
            dexes = await self.dex_manager.get_supported_dexes()
            
            # Fetch pools from all DEXes concurrently
            all_pools = []
            fetch_tasks = []
            
            for dex_name in dexes:
                dex = await self.dex_manager.get_dex(dex_name)
                if dex:
                    task = asyncio.create_task(
                        dex.get_pools(limit=self.max_pools_per_dex)
                    )
                    fetch_tasks.append((dex_name, task))
            
            # Wait for all fetches to complete
            for dex_name, task in fetch_tasks:
                try:
                    pools = await task
                    logger.debug(f"Fetched {len(pools)} pools from {dex_name}")
                    
                    # Add DEX name to each pool
                    for pool in pools:
                        pool.dex = dex_name
                        all_pools.append(pool)
                        
                except Exception as e:
                    logger.error(f"Failed to fetch pools from {dex_name}: {e}")
            
            # Filter pools
            filtered_pools = self._filter_pools(all_pools)
            logger.info(f"Using {len(filtered_pools)} out of {len(all_pools)} pools after filtering")
            
            # Build new graph
            new_graph = nx.DiGraph()
            
            # Add nodes and edges
            for pool in filtered_pools:
                # Add token nodes if they don't exist
                if pool.token0 not in new_graph:
                    new_graph.add_node(pool.token0, is_token=True)
                
                if pool.token1 not in new_graph:
                    new_graph.add_node(pool.token1, is_token=True)
                
                # Calculate edge weights based on liquidity and fee
                # Weight is -log of (1 - fee), so lower fee = lower weight
                fee_factor = 1 - (pool.fee / 10000)  # Convert basis points to decimal
                weight = -log(fee_factor) if fee_factor > 0 else 99999
                
                # Add bidirectional edges
                new_graph.add_edge(
                    pool.token0,
                    pool.token1,
                    weight=weight,
                    pool=pool,
                    fee=pool.fee,
                    liquidity=pool.liquidity or 0,
                    dex=pool.dex
                )
                
                new_graph.add_edge(
                    pool.token1,
                    pool.token0,
                    weight=weight,
                    pool=pool,
                    fee=pool.fee,
                    liquidity=pool.liquidity or 0,
                    dex=pool.dex
                )
            
            # Update the graph
            self.graph = new_graph
            self._last_update = current_time
            
            logger.info(f"Graph updated with {len(self.graph.nodes)} tokens and {len(self.graph.edges)} edges")
            
        except Exception as e:
            logger.error(f"Failed to update graph: {e}")
    
    async def get_graph(self) -> nx.DiGraph:
        """
        Get the current graph representation.
        
        Returns:
            The NetworkX directed graph
        """
        await self._ensure_initialized()
        
        # Ensure graph is up to date
        await self.update_graph()
        
        return self.graph
    
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
        await self._ensure_initialized()
        
        # Ensure tokens are checksummed
        start_token = Web3.to_checksum_address(start_token)
        end_token = Web3.to_checksum_address(end_token)
        
        # Ensure graph is up to date
        await self.update_graph()
        
        # Apply filters
        filters = filters or {}
        graph = self._apply_filters_to_graph(self.graph, filters)
        
        # Check if tokens exist in graph
        if start_token not in graph or end_token not in graph:
            logger.warning(f"One or both tokens not found in graph: {start_token}, {end_token}")
            return []
        
        try:
            # Use NetworkX to find simple paths
            paths: Iterable = nx.all_simple_paths(
                graph,
                source=start_token,
                target=end_token,
                cutoff=max_length
            )
            
            # Convert paths to list of (token, pool) tuples
            result = []
            path_count = 0
            
            for path in paths:
                if path_count >= max_paths:
                    break
                
                # Convert token path to (token, pool) path
                token_pool_path = []
                
                for i in range(len(path) - 1):
                    token_from = path[i]
                    token_to = path[i + 1]
                    
                    edge_data = graph.get_edge_data(token_from, token_to)
                    if not edge_data:
                        logger.warning(f"Missing edge data for {token_from} -> {token_to}")
                        continue
                    
                    pool = edge_data.get('pool')
                    if not pool:
                        logger.warning(f"Missing pool for {token_from} -> {token_to}")
                        continue
                    
                    token_pool_path.append((token_from, pool))
                
                # Add final token
                token_pool_path.append((path[-1], None))
                
                result.append(token_pool_path)
                path_count += 1
            
            logger.debug(f"Found {len(result)} paths from {start_token} to {end_token}")
            return result
            
        except Exception as e:
            logger.error(f"Error finding paths: {e}")
            return []
    
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
        await self._ensure_initialized()
        
        # Ensure token is checksummed
        start_token = Web3.to_checksum_address(start_token)
        
        # Ensure graph is up to date
        await self.update_graph()
        
        # Apply filters
        filters = filters or {}
        graph = self._apply_filters_to_graph(self.graph, filters)
        
        # Check if token exists in graph
        if start_token not in graph:
            logger.warning(f"Token not found in graph: {start_token}")
            return []
        
        try:
            # Find cycles using a custom approach since NetworkX's simple_cycles
            # doesn't let us specify a start node
            cycles = self._find_cycles_from_node(
                graph,
                start_token,
                max_length,
                max_cycles
            )
            
            logger.debug(f"Found {len(cycles)} cycles from {start_token}")
            return cycles
            
        except Exception as e:
            logger.error(f"Error finding cycles: {e}")
            return []
    
    async def close(self) -> None:
        """Close the graph explorer and clean up resources."""
        logger.info("Closing graph explorer")
        self._initialized = False
        self.graph = nx.DiGraph()
        self.pool_cache.clear()
    
    def _filter_pools(self, pools: List[Pool]) -> List[Pool]:
        """
        Filter pools based on configuration.
        
        Args:
            pools: List of pools to filter
            
        Returns:
            Filtered list of pools
        """
        filtered_pools = []
        
        for pool in pools:
            # Skip pools with excluded tokens
            if pool.token0 in self.excluded_tokens or pool.token1 in self.excluded_tokens:
                continue
            
            # Skip pools with insufficient liquidity
            if pool.liquidity is not None and pool.liquidity < self.min_liquidity:
                continue
            
            # Include pool if it contains any of the included tokens
            if self.included_tokens and (pool.token0 not in self.included_tokens and pool.token1 not in self.included_tokens):
                continue
            
            filtered_pools.append(pool)
        
        return filtered_pools
    
    def _apply_filters_to_graph(
        self,
        graph: nx.DiGraph,
        filters: Dict[str, Any]
    ) -> nx.DiGraph:
        """
        Apply filters to a graph for path finding.
        
        Args:
            graph: The graph to filter
            filters: Filters to apply
            
        Returns:
            Filtered graph
        """
        # Create a copy of the graph to avoid modifying the original
        filtered_graph = graph.copy()
        
        # Filter by DEX
        dex_filter = filters.get("dex")
        if dex_filter:
            if isinstance(dex_filter, str):
                dex_filter = [dex_filter]
            
            # Create a list of edges to remove
            edges_to_remove = []
            
            for u, v, data in filtered_graph.edges(data=True):
                if data.get("dex") not in dex_filter:
                    edges_to_remove.append((u, v))
            
            # Remove filtered edges
            for u, v in edges_to_remove:
                filtered_graph.remove_edge(u, v)
        
        # Filter by minimum liquidity
        min_liquidity = filters.get("min_liquidity")
        if min_liquidity is not None:
            min_liquidity = Decimal(str(min_liquidity))
            
            # Create a list of edges to remove
            edges_to_remove = []
            
            for u, v, data in filtered_graph.edges(data=True):
                liquidity = data.get("liquidity", 0)
                if liquidity < min_liquidity:
                    edges_to_remove.append((u, v))
            
            # Remove filtered edges
            for u, v in edges_to_remove:
                filtered_graph.remove_edge(u, v)
        
        # Remove isolated nodes (tokens with no connections)
        for node in list(filtered_graph.nodes()):
            if filtered_graph.degree(node) == 0:
                filtered_graph.remove_node(node)
        
        return filtered_graph
    
    def _find_cycles_from_node(
        self,
        graph: nx.DiGraph,
        start_node: str,
        max_length: int,
        max_cycles: int
    ) -> List[List[Tuple[str, Pool]]]:
        """
        Find cycles starting and ending at the given node.
        
        Args:
            graph: Graph to search
            start_node: Starting node
            max_length: Maximum cycle length
            max_cycles: Maximum number of cycles to return
            
        Returns:
            List of cycles, where each cycle is a list of (token, pool) tuples
        """
        cycles: List[List[Tuple[str, Pool]]] = []
        visited: Dict[str, bool] = {node: False for node in graph.nodes()}
        path: List[str] = []
        
        def dfs(node: str, depth: int) -> None:
            # Mark the current node as visited
            visited[node] = True
            path.append(node)
            
            # If we've reached the maximum depth, check if we can return to start
            if depth == max_length:
                if start_node in graph.successors(node):
                    # Convert the path to a cycle
                    cycle = self._path_to_cycle(graph, path + [start_node])
                    cycles.append(cycle)
                
                visited[node] = False
                path.pop()
                return
            
            # Continue DFS with neighbors
            for neighbor in graph.successors(node):
                # Skip the start node except at the end of the path
                if neighbor == start_node and depth < max_length - 1:
                    continue
                
                # Skip visited nodes
                if visited.get(neighbor, True):
                    continue
                
                # Skip if we've found enough cycles
                if len(cycles) >= max_cycles:
                    break
                
                dfs(neighbor, depth + 1)
            
            # Backtrack
            visited[node] = False
            path.pop()
        
        # Start DFS from the start node
        dfs(start_node, 0)
        
        return cycles[:max_cycles]
    
    def _path_to_cycle(
        self,
        graph: nx.DiGraph,
        path: List[str]
    ) -> List[Tuple[str, Pool]]:
        """
        Convert a path of tokens to a cycle of (token, pool) tuples.
        
        Args:
            graph: Graph containing the path
            path: List of tokens forming a path
            
        Returns:
            Cycle as a list of (token, pool) tuples
        """
        cycle = []
        
        for i in range(len(path) - 1):
            token_from = path[i]
            token_to = path[i + 1]
            
            edge_data = graph.get_edge_data(token_from, token_to)
            if not edge_data:
                logger.warning(f"Missing edge data for {token_from} -> {token_to}")
                continue
            
            pool = edge_data.get('pool')
            if not pool:
                logger.warning(f"Missing pool for {token_from} -> {token_to}")
                continue
            
            cycle.append((token_from, pool))
        
        return cycle
    
    async def _ensure_initialized(self) -> None:
        """Ensure the graph explorer is initialized."""
        if not self._initialized:
            if not await self.initialize():
                raise RuntimeError("Failed to initialize graph explorer")