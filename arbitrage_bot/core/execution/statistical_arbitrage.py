"""Statistical arbitrage strategies using MCP market analysis."""

import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal

from ...utils.mcp_helper import call_mcp_tool

logger = logging.getLogger(__name__)

class StatisticalArbitrage:
    """Statistical arbitrage detector using market analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_confidence = 0.8
        self.min_profit = float(config["trading"]["min_profit_usd"])
        
    async def analyze_price_patterns(
        self,
        token: str,
        prices: Dict[str, Dict[str, float]]
    ) -> Optional[Dict[str, Any]]:
        """Analyze price patterns across DEXes."""
        try:
            # Get market analysis
            analysis = await call_mcp_tool(
                "market-analysis",
                "analyze_opportunities",
                {
                    "token": token,
                    "days": 1,
                    "min_profit_threshold": self.min_profit
                }
            )
            
            if not analysis:
                return None
                
            # Extract market conditions
            volatility = analysis["market_conditions"]["volatility"]
            volume_trend = analysis["market_conditions"]["volume_trend"]
            liquidity = analysis["market_conditions"]["liquidity_score"]
            
            # Calculate price deviations
            price_points = []
            for dex, pools in prices.items():
                for pool_type, price in pools.items():
                    price_points.append({
                        "dex": dex,
                        "pool": pool_type,
                        "price": price
                    })
            
            if len(price_points) < 2:
                return None
                
            # Calculate mean and standard deviation
            mean_price = sum(p["price"] for p in price_points) / len(price_points)
            std_dev = (
                sum((p["price"] - mean_price) ** 2 for p in price_points) 
                / len(price_points)
            ) ** 0.5
            
            # Find outliers (potential opportunities)
            opportunities = []
            for p1 in price_points:
                for p2 in price_points:
                    if p1["dex"] == p2["dex"]:
                        continue
                        
                    price_diff = abs(p1["price"] - p2["price"])
                    z_score = price_diff / std_dev if std_dev > 0 else 0
                    
                    # Check if difference is statistically significant
                    if z_score > 2.0:  # 95% confidence interval
                        profit_potential = price_diff / mean_price
                        if profit_potential > self.min_profit:
                            opportunities.append({
                                "buy_dex": p1["dex"] if p1["price"] < p2["price"] else p2["dex"],
                                "buy_pool": p1["pool"] if p1["price"] < p2["price"] else p2["pool"],
                                "sell_dex": p2["dex"] if p1["price"] < p2["price"] else p1["dex"],
                                "sell_pool": p2["pool"] if p1["price"] < p2["price"] else p1["pool"],
                                "profit_potential": profit_potential,
                                "z_score": z_score,
                                "confidence": 0.95
                            })
            
            if not opportunities:
                return None
                
            # Return best opportunity
            return {
                "opportunities": sorted(
                    opportunities,
                    key=lambda x: x["profit_potential"],
                    reverse=True
                ),
                "market_conditions": {
                    "volatility": volatility,
                    "volume_trend": volume_trend,
                    "liquidity": liquidity,
                    "mean_price": mean_price,
                    "std_dev": std_dev
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze price patterns: {e}")
            return None
            
    async def detect_mean_reversion(
        self,
        token: str,
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """Detect mean reversion opportunities."""
        try:
            # Get historical opportunities
            analysis = await call_mcp_tool(
                "market-analysis",
                "analyze_opportunities",
                {
                    "token": token,
                    "days": 1
                }
            )
            
            if not analysis or "opportunities" not in analysis:
                return None
                
            # Calculate historical mean
            prices = [opp["price"] for opp in analysis["opportunities"]]
            if not prices:
                return None
                
            mean_price = sum(prices) / len(prices)
            std_dev = (
                sum((p - mean_price) ** 2 for p in prices) 
                / len(prices)
            ) ** 0.5
            
            # Check for mean reversion opportunity
            price_diff = abs(current_price - mean_price)
            z_score = price_diff / std_dev if std_dev > 0 else 0
            
            if z_score > 2.0:  # Statistically significant deviation
                return {
                    "type": "mean_reversion",
                    "current_price": current_price,
                    "mean_price": mean_price,
                    "z_score": z_score,
                    "expected_direction": "up" if current_price < mean_price else "down",
                    "confidence": 0.95 if z_score > 3.0 else 0.90
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to detect mean reversion: {e}")
            return None
