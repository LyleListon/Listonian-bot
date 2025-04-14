"""Path finder for arbitrage opportunities."""

import logging
import networkx as nx
from typing import Dict, List, Optional, Set, Tuple, Any

logger = logging.getLogger(__name__)


class PathFinder:
    """Finds arbitrage paths between tokens across multiple DEXs."""
    
    def __init__(self, max_path_length: int = 3):
        """Initialize the path finder.
        
        Args:
            max_path_length: Maximum number of hops in a path.
        """
        self.max_path_length = max_path_length
        self.graph = nx.DiGraph()
    
    def update_graph(self, market_data: Dict[str, Any]) -> None:
        """Update the graph with market data.
        
        Args:
            market_data: Market data containing pairs information.
        """
        # Clear the existing graph
        self.graph.clear()
        
        # Add edges for each pair
        for pair in market_data.get("pairs", []):
            base_token = pair.get("base_token")
            quote_token = pair.get("quote_token")
            dex = pair.get("dex")
            price = pair.get("price")
            liquidity = pair.get("liquidity")
            
            if not all([base_token, quote_token, dex, price is not None, liquidity is not None]):
                logger.warning(f"Skipping pair with missing data: {pair}")
                continue
            
            # Add forward edge (base -> quote)
            self.graph.add_edge(
                base_token,
                quote_token,
                dex=dex,
                price=price,
                liquidity=liquidity,
                direction="forward",
            )
            
            # Add backward edge (quote -> base)
            inverse_price = 1.0 / price if price != 0 else 0.0
            self.graph.add_edge(
                quote_token,
                base_token,
                dex=dex,
                price=inverse_price,
                liquidity=liquidity,
                direction="backward",
            )
        
        logger.info(
            f"Updated graph with {self.graph.number_of_nodes()} nodes and "
            f"{self.graph.number_of_edges()} edges"
        )
    
    def find_arbitrage_paths(
        self, start_token: str, min_liquidity: float = 0.0
    ) -> List[List[Dict[str, Any]]]:
        """Find arbitrage paths starting and ending with the same token.
        
        Args:
            start_token: The token to start and end with.
            min_liquidity: Minimum liquidity required for each edge.
            
        Returns:
            List of paths, where each path is a list of edges.
        """
        if start_token not in self.graph:
            logger.warning(f"Start token {start_token} not in graph")
            return []
        
        # Filter edges by minimum liquidity
        if min_liquidity > 0:
            filtered_graph = nx.DiGraph()
            for u, v, data in self.graph.edges(data=True):
                if data.get("liquidity", 0) >= min_liquidity:
                    filtered_graph.add_edge(u, v, **data)
            graph = filtered_graph
        else:
            graph = self.graph
        
        # Find simple cycles starting and ending with start_token
        arbitrage_paths = []
        
        # Use NetworkX's simple_cycles to find all cycles
        for cycle in nx.simple_cycles(graph):
            # Check if the cycle starts and ends with start_token
            if cycle[0] == start_token and len(cycle) <= self.max_path_length + 1:
                # Convert cycle to path (list of edges)
                path = []
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    edge_data = graph.get_edge_data(u, v)
                    if edge_data:
                        path.append({
                            "from_token": u,
                            "to_token": v,
                            "dex": edge_data.get("dex"),
                            "price": edge_data.get("price"),
                            "liquidity": edge_data.get("liquidity"),
                            "direction": edge_data.get("direction"),
                        })
                
                arbitrage_paths.append(path)
        
        logger.debug(f"Found {len(arbitrage_paths)} arbitrage paths for {start_token}")
        return arbitrage_paths
    
    def find_all_arbitrage_paths(
        self, min_liquidity: float = 0.0
    ) -> Dict[str, List[List[Dict[str, Any]]]]:
        """Find arbitrage paths for all tokens.
        
        Args:
            min_liquidity: Minimum liquidity required for each edge.
            
        Returns:
            Dictionary mapping tokens to lists of arbitrage paths.
        """
        all_paths = {}
        
        for token in self.graph.nodes():
            paths = self.find_arbitrage_paths(token, min_liquidity)
            if paths:
                all_paths[token] = paths
        
        return all_paths
    
    def calculate_path_metrics(
        self, path: List[Dict[str, Any]], input_amount: float = 1.0
    ) -> Dict[str, Any]:
        """Calculate metrics for a path.
        
        Args:
            path: The path to calculate metrics for.
            input_amount: The input amount.
            
        Returns:
            Dictionary with path metrics.
        """
        if not path:
            return {
                "output_amount": 0.0,
                "profit_percentage": 0.0,
                "min_liquidity": 0.0,
                "dexes": [],
                "tokens": [],
            }
        
        # Calculate output amount
        output_amount = input_amount
        for edge in path:
            price = edge.get("price", 0.0)
            output_amount *= price
        
        # Calculate profit percentage
        profit_percentage = ((output_amount / input_amount) - 1.0) * 100.0
        
        # Get minimum liquidity
        min_liquidity = min(edge.get("liquidity", 0.0) for edge in path)
        
        # Get unique DEXes
        dexes = list({edge.get("dex") for edge in path})
        
        # Get tokens in path
        tokens = [edge.get("from_token") for edge in path]
        
        return {
            "output_amount": output_amount,
            "profit_percentage": profit_percentage,
            "min_liquidity": min_liquidity,
            "dexes": dexes,
            "tokens": tokens,
        }
