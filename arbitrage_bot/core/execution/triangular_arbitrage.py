"""Triangular arbitrage detection across multiple DEXes."""

import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

from ...utils.mcp_helper import call_mcp_tool

logger = logging.getLogger(__name__)

class TriangularArbitrage:
    """Triangular arbitrage detector using market analysis."""
    
    def __init__(self, config: Dict[str, Any], dex_interfaces: Dict[str, Any]):
        self.config = config
        self.dex_interfaces = dex_interfaces
        self.min_profit = float(config["trading"]["min_profit_usd"])
        self.base_tokens = [
            "0x4200000000000000000000000000000000000006",  # WETH
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC
            "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"   # USDT
        ]
        
    async def find_triangular_routes(
        self,
        start_token: str,
        depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Find potential triangular arbitrage routes."""
        routes = []
        visited = set()
        
        async def dfs(current_token: str, path: List[Dict[str, Any]], current_depth: int):
            if current_depth == depth:
                if path[-1]["token1"] == start_token:
                    routes.append(path)
                return
                
            visited.add(current_token)
            
            # Get all possible next tokens
            for dex_name, dex in self.dex_interfaces.items():
                for next_token in self.base_tokens:
                    if next_token in visited:
                        continue
                        
                    try:
                        pool_info = await dex.get_pool_info(current_token, next_token)
                        if pool_info:
                            path.append({
                                "dex": dex_name,
                                "token0": current_token,
                                "token1": next_token,
                                "pool_info": pool_info
                            })
                            await dfs(next_token, path, current_depth + 1)
                            path.pop()
                    except Exception as e:
                        logger.debug(f"No pool for {current_token}-{next_token} on {dex_name}: {e}")
                        
            visited.remove(current_token)
            
        await dfs(start_token, [], 0)
        return routes
        
    async def calculate_profit(
        self,
        route: List[Dict[str, Any]],
        amount_in: int
    ) -> Tuple[float, List[int]]:
        """Calculate potential profit for a triangular route."""
        try:
            amounts = [amount_in]
            
            # Calculate amounts through the path
            for hop in route:
                dex = self.dex_interfaces[hop["dex"]]
                
                # Handle different DEX types
                if hop["dex"] == "aerodrome":
                    # Try both stable and volatile pools
                    try:
                        amounts_stable = await dex.get_amounts_out(
                            amounts[-1],
                            [hop["token0"], hop["token1"]],
                            [True]
                        )
                        amounts_volatile = await dex.get_amounts_out(
                            amounts[-1],
                            [hop["token0"], hop["token1"]],
                            [False]
                        )
                        # Use the better rate
                        amount_out = max(amounts_stable[-1], amounts_volatile[-1])
                    except Exception:
                        # Fallback to volatile pool
                        amounts_out = await dex.get_amounts_out(
                            amounts[-1],
                            [hop["token0"], hop["token1"]],
                            [False]
                        )
                        amount_out = amounts_out[-1]
                        
                elif hop["dex"] == "rocketswap":
                    # Account for dynamic fees
                    amounts_out = await dex.get_amounts_out(
                        amounts[-1],
                        [hop["token0"], hop["token1"]]
                    )
                    amount_out = amounts_out[-1]
                    
                else:
                    # Standard V2 pools
                    amounts_out = await dex.get_amounts_out(
                        amounts[-1],
                        [hop["token0"], hop["token1"]]
                    )
                    amount_out = amounts_out[-1]
                    
                amounts.append(amount_out)
                
            # Calculate profit percentage
            profit_percent = (amounts[-1] - amounts[0]) / amounts[0]
            return profit_percent, amounts
            
        except Exception as e:
            logger.error(f"Failed to calculate profit: {e}")
            return 0, []
            
    async def find_opportunities(
        self,
        start_amount: int = 10**18  # 1 token
    ) -> List[Dict[str, Any]]:
        """Find triangular arbitrage opportunities."""
        opportunities = []
        
        try:
            # Start with WETH
            routes = await self.find_triangular_routes(self.base_tokens[0])
            
            for route in routes:
                profit_percent, amounts = await self.calculate_profit(route, start_amount)
                
                if profit_percent > self.min_profit:
                    # Validate with market analysis
                    analysis = await call_mcp_tool(
                        "market-analysis",
                        "analyze_opportunities",
                        {
                            "token": route[0]["token0"],
                            "days": 1
                        }
                    )
                    
                    if analysis and analysis.get("success_probability", 0) > 0.8:
                        path_description = " -> ".join([
                            f"{hop['token0']}->{hop['token1']} ({hop['dex']})"
                            for hop in route
                        ])
                        
                        logger.info(
                            f"Found triangular opportunity:\n"
                            f"  Path: {path_description}\n"
                            f"  Profit: {profit_percent*100:.2f}%\n"
                            f"  Input: {start_amount / 10**18:.6f}\n"
                            f"  Output: {amounts[-1] / 10**18:.6f}"
                        )
                        
                        opportunities.append({
                            "route": route,
                            "profit_percent": profit_percent,
                            "amounts": amounts,
                            "market_conditions": analysis.get("market_conditions", {}),
                            "confidence": analysis.get("success_probability", 0)
                        })
            
            return sorted(
                opportunities,
                key=lambda x: x["profit_percent"],
                reverse=True
            )
            
        except Exception as e:
            logger.error(f"Failed to find opportunities: {e}")
            return []
            
    async def validate_opportunity(
        self,
        opportunity: Dict[str, Any]
    ) -> bool:
        """Validate a triangular opportunity."""
        try:
            # Check liquidity on each hop
            for hop in opportunity["route"]:
                liquidity_check = await call_mcp_tool(
                    "market-analysis",
                    "assess_market_conditions",
                    {
                        "token": hop["token0"],
                        "metrics": ["liquidity"]
                    }
                )
                
                if not liquidity_check or liquidity_check.get("liquidity_score", 0) < 0.5:
                    logger.warning(f"Insufficient liquidity for {hop['token0']} on {hop['dex']}")
                    return False
                    
            # Check market conditions
            market_check = opportunity.get("market_conditions", {})
            if (
                market_check.get("volatility", 1.0) > 0.1 or  # High volatility
                market_check.get("volume_trend", 0) < 0 or    # Declining volume
                market_check.get("liquidity_score", 0) < 0.5  # Low liquidity
            ):
                logger.warning("Unfavorable market conditions")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate opportunity: {e}")
            return False
