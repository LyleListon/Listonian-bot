#!/usr/bin/env python
"""
Glama AI Enhanced Arbitrage Strategy Example

This example demonstrates how to use the Glama AI MCP server to enhance arbitrage strategies
with AI-powered market analysis, path optimization, and execution parameter tuning.

Before running this example:
1. Set up Glama AI credentials using setup_mcp_keys.bat
2. Start the Glama AI MCP server using run_glama_enhanced_strategy.bat

Usage:
    python glama_enhanced_strategy.py
"""

import asyncio
import json
import logging
import datetime
import random
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("glama_enhanced_strategy")


class GlamaAIClient:
    """
    Client for interacting with the Glama AI MCP server.
    
    This class provides methods to leverage AI capabilities for arbitrage:
    1. Market analysis and prediction
    2. Arbitrage path optimization
    3. Risk assessment
    4. Execution parameter optimization
    5. Historical performance analysis
    """
    
    def __init__(self):
        """Initialize the Glama AI client."""
        self.logger = logging.getLogger(__name__)
        
        # In a real implementation, this would connect to the MCP server
        # For this example, we'll simulate the responses
        self.logger.info("Initialized Glama AI client")
    
    async def analyze_market(self, base_token: str, quote_tokens: List[str], 
                            network: str = "ethereum") -> Dict[str, Any]:
        """
        Analyze market conditions for the given tokens.
        
        Args:
            base_token: The base token symbol (e.g., 'WETH')
            quote_tokens: List of quote token symbols (e.g., ['USDC', 'DAI'])
            network: Blockchain network to analyze
            
        Returns:
            Market analysis data
        """
        self.logger.info(f"Analyzing market for {base_token} against {quote_tokens} on {network}")
        
        # In a real implementation, this would call the Glama AI MCP server
        # For this example, we'll simulate the response
        
        # Simulate varying market conditions
        market_sentiment = random.choice(["bullish", "bearish", "neutral", "volatile"])
        
        # Current timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Simulated response
        response = {
            "timestamp": timestamp,
            "network": network,
            "base_token": base_token,
            "quote_tokens": quote_tokens,
            "market_sentiment": market_sentiment,
            "volatility": round(random.uniform(0.1, 0.9), 2),
            "liquidity_trend": random.choice(["increasing", "decreasing", "stable"]),
            "gas_price_recommendation": round(random.uniform(20, 200)),
            "token_analysis": {},
            "dex_analysis": {},
            "arbitrage_conditions": {
                "favorable": random.random() > 0.3,  # 70% chance of favorable conditions
                "optimal_time_window_seconds": random.randint(10, 300),
                "confidence": round(random.uniform(0.5, 0.95), 2)
            },
            "prediction_confidence": round(random.uniform(0.7, 0.98), 2)
        }
        
        # Generate token-specific analysis
        for token in [base_token] + quote_tokens:
            price_trend = random.choice(["upward", "downward", "stable", "volatile"])
            price_movement_prediction = round(random.uniform(-5.0, 5.0), 2)
            
            response["token_analysis"][token] = {
                "price_trend": price_trend,
                "price_movement_prediction_1h": f"{price_movement_prediction}%",
                "liquidity_score": round(random.uniform(0.1, 1.0), 2),
                "volatility_score": round(random.uniform(0.1, 1.0), 2),
                "trading_volume_trend": random.choice(["increasing", "decreasing", "stable"]),
                "whale_activity": random.choice(["high", "medium", "low", "none"]),
                "price_manipulation_risk": random.choice(["high", "medium", "low"])
            }
        
        # Generate DEX-specific analysis
        for dex in ["Uniswap V3", "SushiSwap", "PancakeSwap"]:
            response["dex_analysis"][dex] = {
                "liquidity_score": round(random.uniform(0.5, 1.0), 2),
                "slippage_estimate": f"{round(random.uniform(0.01, 2.0), 2)}%",
                "fee_tier_recommendation": random.choice(["0.05%", "0.3%", "1%"]),
                "price_impact_risk": random.choice(["high", "medium", "low"]),
                "sandwich_attack_risk": random.choice(["high", "medium", "low"])
            }
        
        return response
    
    async def predict_price(self, token: str, timeframe: str = "1h", 
                           network: str = "ethereum") -> Dict[str, Any]:
        """
        Predict price movement for a specific token.
        
        Args:
            token: Token symbol to predict
            timeframe: Timeframe for prediction (e.g., '5m', '1h', '1d')
            network: Blockchain network
            
        Returns:
            Price prediction data
        """
        self.logger.info(f"Predicting {token} price movements for {timeframe} timeframe on {network}")
        
        # In a real implementation, this would call the Glama AI MCP server
        # For this example, we'll simulate the response
        
        # Simulate price prediction
        direction = random.choice(["up", "down"])
        magnitude = round(random.uniform(0.1, 5.0), 2)
        confidence = round(random.uniform(0.6, 0.95), 2)
        
        # Current timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Calculate target timestamp based on timeframe
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            target_timestamp = (datetime.datetime.now() + 
                              datetime.timedelta(minutes=minutes)).isoformat()
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            target_timestamp = (datetime.datetime.now() + 
                              datetime.timedelta(hours=hours)).isoformat()
        elif timeframe.endswith('d'):
            days = int(timeframe[:-1])
            target_timestamp = (datetime.datetime.now() + 
                              datetime.timedelta(days=days)).isoformat()
        else:
            target_timestamp = (datetime.datetime.now() + 
                              datetime.timedelta(hours=1)).isoformat()
        
        # Simulated response
        response = {
            "token": token,
            "network": network,
            "current_timestamp": timestamp,
            "target_timestamp": target_timestamp,
            "timeframe": timeframe,
            "prediction": {
                "direction": direction,
                "magnitude_percent": f"{magnitude}%",
                "confidence": confidence,
                "factors": {
                    "technical_indicators": random.choice(["bullish", "bearish", "neutral"]),
                    "market_sentiment": random.choice(["positive", "negative", "neutral"]),
                    "whale_activity": random.choice(["high", "medium", "low"]),
                    "volume_analysis": random.choice(["increasing", "decreasing", "stable"])
                }
            },
            "supporting_evidence": {
                "recent_trends": f"Token has shown {random.choice(['strong', 'weak', 'moderate'])} momentum in the last {random.randint(1, 24)} hours",
                "technical_factors": f"Moving averages show {random.choice(['bullish', 'bearish', 'neutral'])} crossover pattern",
                "on-chain_metrics": f"Recent {random.choice(['increase', 'decrease'])} in transactions suggests {random.choice(['growing', 'declining'])} interest"
            }
        }
        
        return response
    
    async def optimize_path(self, tokens: List[str], dexes: List[str], 
                           optimization_target: str = "profit") -> Dict[str, Any]:
        """
        Optimize an arbitrage path for maximum profit.
        
        Args:
            tokens: List of tokens to include in the path
            dexes: List of DEXes to consider
            optimization_target: What to optimize for ('profit', 'gas', 'risk', 'balance')
            
        Returns:
            Optimized path data
        """
        self.logger.info(f"Optimizing arbitrage path for {len(tokens)} tokens and {len(dexes)} DEXes")
        self.logger.info(f"Optimization target: {optimization_target}")
        
        # In a real implementation, this would call the Glama AI MCP server
        # For this example, we'll simulate the response
        
        # Simulate path optimization
        path_length = random.randint(2, min(5, len(tokens)))
        selected_tokens = tokens[:path_length] if len(tokens) >= path_length else tokens
        
        # Ensure we have at least the start and end token
        if len(selected_tokens) < 2:
            selected_tokens = tokens[:2] if len(tokens) >= 2 else tokens + [tokens[0]]
        
        # Create a path using the tokens
        path = []
        
        # Start with the first token
        current_token = selected_tokens[0]
        
        # Add intermediate steps using available tokens and DEXes
        used_tokens = {current_token}
        
        for i in range(min(5, len(tokens) + len(dexes) - 1)):
            # Select a token that hasn't been used yet for variety
            next_token_options = [t for t in selected_tokens if t not in used_tokens]
            
            # If all tokens have been used, select from all tokens
            if not next_token_options:
                next_token_options = selected_tokens
            
            next_token = random.choice(next_token_options)
            used_tokens.add(next_token)
            
            # Select a DEX
            dex = random.choice(dexes)
            
            # Add this step to the path
            path.append({
                "from_token": current_token,
                "to_token": next_token,
                "dex": dex,
                "expected_slippage": f"{round(random.uniform(0.01, 0.5), 2)}%",
                "fee_tier": random.choice(["0.05%", "0.3%", "1%"]),
                "gas_estimate": random.randint(50000, 300000)
            })
            
            # Update current token
            current_token = next_token
        
        # Ensure the path ends with the first token for a complete cycle
        if current_token != selected_tokens[0]:
            dex = random.choice(dexes)
            path.append({
                "from_token": current_token,
                "to_token": selected_tokens[0],
                "dex": dex,
                "expected_slippage": f"{round(random.uniform(0.01, 0.5), 2)}%",
                "fee_tier": random.choice(["0.05%", "0.3%", "1%"]),
                "gas_estimate": random.randint(50000, 300000)
            })
        
        # Calculate total gas and expected profit
        total_gas = sum(step["gas_estimate"] for step in path)
        expected_profit_percentage = round(random.uniform(0.1, 5.0), 2)
        
        # Simulated response
        response = {
            "tokens_considered": tokens,
            "dexes_considered": dexes,
            "optimization_target": optimization_target,
            "path_length": len(path),
            "path": path,
            "estimated_metrics": {
                "total_gas": total_gas,
                "expected_profit_percentage": f"{expected_profit_percentage}%",
                "expected_profit_usd": f"${round(random.uniform(10, 1000), 2)}",
                "execution_time_ms": random.randint(500, 5000),
                "success_probability": round(random.uniform(0.7, 0.98), 2),
                "risk_score": round(random.uniform(0.1, 0.8), 2)
            },
            "flash_loan_recommendation": {
                "recommended": random.choice([True, False]),
                "provider": random.choice(["Balancer", "Aave", "dYdX"]),
                "estimated_fee": f"{round(random.uniform(0.01, 0.1), 3)}%"
            },
            "confidence": round(random.uniform(0.7, 0.98), 2),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return response
    
    async def assess_risk(self, tokens: List[str], path: List[Dict[str, Any]], 
                         network: str = "ethereum") -> Dict[str, Any]:
        """
        Assess risks associated with an arbitrage opportunity.
        
        Args:
            tokens: List of tokens involved
            path: The arbitrage path to assess
            network: Blockchain network
            
        Returns:
            Risk assessment data
        """
        self.logger.info(f"Assessing risk for arbitrage path with {len(tokens)} tokens on {network}")
        
        # In a real implementation, this would call the Glama AI MCP server
        # For this example, we'll simulate the response
        
        # Generate risk scores
        frontrunning_risk = round(random.uniform(0.1, 0.9), 2)
        sandwich_risk = round(random.uniform(0.1, 0.9), 2)
        price_movement_risk = round(random.uniform(0.1, 0.9), 2)
        smart_contract_risk = round(random.uniform(0.1, 0.5), 2)
        
        # Overall risk is weighted average
        overall_risk = round(
            (frontrunning_risk * 0.3) + 
            (sandwich_risk * 0.2) + 
            (price_movement_risk * 0.4) + 
            (smart_contract_risk * 0.1), 
            2
        )
        
        # Generate token-specific risks
        token_risks = {}
        for token in tokens:
            token_risks[token] = {
                "liquidity_risk": round(random.uniform(0.1, 0.9), 2),
                "volatility_risk": round(random.uniform(0.1, 0.9), 2),
                "manipulation_risk": round(random.uniform(0.1, 0.9), 2),
                "oracle_reliability": round(random.uniform(0.5, 1.0), 2)
            }
        
        # Generate DEX-specific risks
        dex_risks = {}
        dexes = list(set(step["dex"] for step in path))
        for dex in dexes:
            dex_risks[dex] = {
                "slippage_risk": round(random.uniform(0.1, 0.9), 2),
                "front_running_exposure": round(random.uniform(0.1, 0.9), 2),
                "smart_contract_risk": round(random.uniform(0.1, 0.5), 2)
            }
        
        # Simulated response
        response = {
            "overall_risk_score": overall_risk,
            "risk_category": "high" if overall_risk > 0.7 else "medium" if overall_risk > 0.4 else "low",
            "timestamp": datetime.datetime.now().isoformat(),
            "network": network,
            "specific_risks": {
                "frontrunning_risk": frontrunning_risk,
                "sandwich_attack_risk": sandwich_risk,
                "price_movement_risk": price_movement_risk,
                "smart_contract_risk": smart_contract_risk,
                "execution_failure_risk": round(random.uniform(0.1, 0.5), 2)
            },
            "token_risks": token_risks,
            "dex_risks": dex_risks,
            "mitigations": {
                "recommended_flashbots_inclusion": overall_risk > 0.5,
                "recommended_slippage_tolerance": f"{round(max(0.5, overall_risk * 2), 1)}%",
                "recommended_deadline_seconds": min(600, int(overall_risk * 1000)),
                "recommended_gas_price_strategy": "aggressive" if overall_risk > 0.7 else "moderate" if overall_risk > 0.4 else "conservative"
            },
            "confidence": round(random.uniform(0.7, 0.95), 2)
        }
        
        return response
    
    async def optimize_execution(self, path: List[Dict[str, Any]], 
                               network: str = "ethereum") -> Dict[str, Any]:
        """
        Optimize execution parameters for an arbitrage trade.
        
        Args:
            path: The arbitrage path to execute
            network: Blockchain network
            
        Returns:
            Optimized execution parameters
        """
        self.logger.info(f"Optimizing execution parameters for arbitrage path on {network}")
        
        # In a real implementation, this would call the Glama AI MCP server
        # For this example, we'll simulate the response
        
        # Current network conditions
        gas_price = random.randint(20, 200)
        network_congestion = random.choice(["low", "medium", "high"])
        mev_activity = random.choice(["low", "medium", "high"])
        
        # Determine optimal parameters based on conditions
        optimal_gas_price = int(gas_price * (1.2 if network_congestion == "high" else 1.1 if network_congestion == "medium" else 1.0))
        use_flashbots = mev_activity in ["medium", "high"]
        slippage_tolerance = round(0.5 + (0.5 if mev_activity == "high" else 0.3 if mev_activity == "medium" else 0.1), 1)
        
        # Simulated response
        response = {
            "network": network,
            "timestamp": datetime.datetime.now().isoformat(),
            "current_conditions": {
                "gas_price_gwei": gas_price,
                "network_congestion": network_congestion,
                "mev_activity": mev_activity,
                "block_time_ms": random.randint(12000, 15000),
                "pending_transactions": random.randint(5000, 50000)
            },
            "optimized_parameters": {
                "gas_price_gwei": optimal_gas_price,
                "gas_price_strategy": "aggressive" if network_congestion == "high" else "moderate" if network_congestion == "medium" else "conservative",
                "priority_fee_gwei": random.randint(1, 5),
                "max_fee_gwei": optimal_gas_price + random.randint(5, 20),
                "slippage_tolerance_percent": slippage_tolerance,
                "transaction_deadline_seconds": random.randint(60, 300),
                "use_flashbots": use_flashbots,
                "flash_loan_provider": random.choice(["Balancer", "Aave", "dYdX"]),
                "execution_strategy": random.choice(["atomic", "sequential", "parallel"]),
                "min_profit_threshold_usd": round(random.uniform(5, 50), 2)
            },
            "expected_outcomes": {
                "execution_time_ms": random.randint(500, 5000),
                "success_probability": round(random.uniform(0.7, 0.98), 2),
                "gas_cost_usd": round(random.uniform(5, 100), 2),
                "net_profit_estimate_usd": round(random.uniform(10, 500), 2)
            },
            "confidence": round(random.uniform(0.7, 0.95), 2)
        }
        
        return response
    
    async def analyze_historical_performance(self, strategy_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze historical performance of a strategy with AI insights.
        
        Args:
            strategy_id: ID of the strategy to analyze
            days: Number of days to analyze
            
        Returns:
            Performance analysis and AI insights
        """
        self.logger.info(f"Analyzing historical performance for strategy {strategy_id} over {days} days")
        
        # In a real implementation, this would call the Glama AI MCP server
        # For this example, we'll simulate the response
        
        # Generate daily performance data
        performance_data = []
        
        # Start date
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Random trend factors to create realistic looking data
        base_profit = random.uniform(0.5, 2.0)
        daily_volatility = random.uniform(0.1, 0.5)
        trend_factor = random.uniform(-0.01, 0.02)  # Slight upward or downward trend
        
        # Generate data for each day
        for i in range(days):
            # Calculate date
            date = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            
            # Calculate profit with trend and some randomness
            daily_factor = 1.0 + (i * trend_factor) + (random.uniform(-daily_volatility, daily_volatility))
            daily_profit = round(base_profit * daily_factor, 2)
            
            # Number of trades
            num_trades = random.randint(10, 50)
            success_rate = random.uniform(0.7, 0.95)
            successful_trades = int(num_trades * success_rate)
            
            # Add daily data
            performance_data.append({
                "date": date,
                "trades_executed": num_trades,
                "successful_trades": successful_trades,
                "failed_trades": num_trades - successful_trades,
                "success_rate": round(success_rate * 100, 1),
                "profit_usd": round(daily_profit * 100, 2),
                "gas_cost_usd": round(daily_profit * 100 * random.uniform(0.1, 0.3), 2),
                "net_profit_usd": round(daily_profit * 100 * (1 - random.uniform(0.1, 0.3)), 2),
                "avg_execution_time_ms": random.randint(500, 2000),
                "avg_profit_per_trade_usd": round((daily_profit * 100) / num_trades, 2),
                "most_profitable_token_pair": random.choice(["ETH/USDC", "ETH/DAI", "ETH/USDT", "ETH/WBTC"]),
                "most_used_dex": random.choice(["Uniswap V3", "SushiSwap", "PancakeSwap V3"])
            })
        
        # Calculate overall statistics
        total_trades = sum(day["trades_executed"] for day in performance_data)
        successful_trades = sum(day["successful_trades"] for day in performance_data)
        total_profit = sum(day["profit_usd"] for day in performance_data)
        total_gas_cost = sum(day["gas_cost_usd"] for day in performance_data)
        total_net_profit = sum(day["net_profit_usd"] for day in performance_data)
        
        # Analyze the trend
        profit_values = [day["net_profit_usd"] for day in performance_data]
        early_avg = sum(profit_values[:5]) / 5 if len(profit_values) >= 5 else sum(profit_values) / len(profit_values)
        late_avg = sum(profit_values[-5:]) / 5 if len(profit_values) >= 5 else sum(profit_values) / len(profit_values)
        trend_direction = "improving" if late_avg > early_avg else "declining" if late_avg < early_avg else "stable"
        trend_magnitude = abs(late_avg - early_avg) / early_avg if early_avg > 0 else 0
        
        # AI insights
        top_token_pairs = {}
        for day in performance_data:
            pair = day["most_profitable_token_pair"]
            top_token_pairs[pair] = top_token_pairs.get(pair, 0) + 1
        
        top_dexes = {}
        for day in performance_data:
            dex = day["most_used_dex"]
            top_dexes[dex] = top_dexes.get(dex, 0) + 1
        
        # Get most common token pair and DEX
        most_profitable_pair = max(top_token_pairs.items(), key=lambda x: x[1])[0] if top_token_pairs else "N/A"
        most_used_dex = max(top_dexes.items(), key=lambda x: x[1])[0] if top_dexes else "N/A"
        
        # Simulated response
        response = {
            "strategy_id": strategy_id,
            "analysis_period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "days_analyzed": days
            },
            "overall_statistics": {
                "total_trades": total_trades,
                "successful_trades": successful_trades,
                "success_rate": round((successful_trades / total_trades) * 100, 1) if total_trades > 0 else 0,
                "total_profit_usd": round(total_profit, 2),
                "total_gas_cost_usd": round(total_gas_cost, 2),
                "total_net_profit_usd": round(total_net_profit, 2),
                "average_daily_profit_usd": round(total_net_profit / days, 2),
                "profit_per_trade_usd": round(total_net_profit / total_trades, 2) if total_trades > 0 else 0,
                "most_profitable_token_pair": most_profitable_pair,
                "most_used_dex": most_used_dex
            },
            "trend_analysis": {
                "profit_trend": trend_direction,
                "trend_magnitude_percent": round(trend_magnitude * 100, 1),
                "volatility": round(daily_volatility * 100, 1),
                "consistency_score": round(random.uniform(0.5, 1.0), 2)
            },
            "ai_insights": {
                "performance_factors": {
                    "primary_success_driver": random.choice([
                        "optimal path selection",
                        "effective gas price strategy",
                        "accurate slippage management",
                        "successful MEV protection",
                        "proper timing of trades"
                    ]),
                    "primary_failure_factor": random.choice([
                        "high network congestion",
                        "unexpected price movements",
                        "insufficient liquidity",
                        "MEV attacks",
                        "high gas costs"
                    ])
                },
                "improvement_recommendations": [
                    f"Focus more on {random.choice(['ETH/USDC', 'ETH/DAI', 'ETH/USDT'])} pairs which show higher profitability",
                    f"Consider using {random.choice(['Uniswap V3', 'SushiSwap'])} more frequently for better execution",
                    f"Optimize gas price strategy during {random.choice(['peak', 'off-peak'])} hours",
                    f"Increase slippage tolerance by {random.uniform(0.1, 0.5):.1f}% to improve success rate",
                    f"Implement additional MEV protection for high-value trades"
                ],
                "market_correlations": {
                    "correlation_with_eth_price": round(random.uniform(-0.8, 0.8), 2),
                    "correlation_with_gas_price": round(random.uniform(-0.8, 0.8), 2),
                    "correlation_with_market_volatility": round(random.uniform(-0.8, 0.8), 2)
                },
                "optimal_execution_time": {
                    "day_of_week": random.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),
                    "time_of_day": random.choice(["morning", "afternoon", "evening", "night"]),
                    "reason": random.choice([
                        "lower network congestion",
                        "higher price volatility",
                        "better liquidity conditions",
                        "reduced MEV activity"
                    ])
                }
            },
            "daily_performance": performance_data,
            "confidence": round(random.uniform(0.75, 0.95), 2),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return response


class GlamaEnhancedArbitrageStrategy:
    """
    AI-enhanced arbitrage strategy using Glama AI for optimization.
    
    This strategy leverages AI insights to:
    1. Select optimal trading paths
    2. Predict market movements
    3. Optimize execution parameters
    4. Assess and mitigate risks
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI-enhanced strategy.
        
        Args:
            config: Strategy configuration parameters
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.ai_client = GlamaAIClient()
        
        # AI influence settings
        self.ai_influence = config.get("ai_settings", {}).get("influence_level", 0.8)
        self.risk_tolerance = config.get("ai_settings", {}).get("risk_tolerance", "medium")
        self.confidence_threshold = config.get("ai_settings", {}).get("confidence_threshold", 0.7)
        
        self.logger.info(f"Initialized AI-enhanced strategy with {self.ai_influence} AI influence")
        self.logger.info(f"Risk tolerance: {self.risk_tolerance}")
        self.logger.info(f"Confidence threshold: {self.confidence_threshold}")
    
    async def find_opportunities(self, base_token: str, quote_tokens: List[str]) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities using AI market analysis.
        
        Args:
            base_token: Base token to trade (e.g., 'WETH')
            quote_tokens: Quote tokens to consider for trading pairs
            
        Returns:
            List of arbitrage opportunities
        """
        self.logger.info(f"Finding AI-enhanced opportunities for {base_token} with {quote_tokens}")
        
        # Step 1: Analyze market conditions using AI
        market_analysis = await self.ai_client.analyze_market(
            base_token=base_token,
            quote_tokens=quote_tokens,
            network=self.config.get("network", "ethereum")
        )
        
        self.logger.info(f"Market analysis complete. Sentiment: {market_analysis['market_sentiment']}")
        self.logger.info(f"Arbitrage conditions: {market_analysis['arbitrage_conditions']['favorable']}")
        
        # If conditions aren't favorable, we might return an empty list in a real implementation
        # For this example, we'll always generate some opportunities
        
        # Step 2: Generate potential paths using AI
        paths = await self.generate_potential_paths(base_token, quote_tokens)
        
        # Step 3: Evaluate and rank the paths
        opportunities = await self.evaluate_paths(paths)
        
        # Log the number of opportunities found
        self.logger.info(f"Found {len(opportunities)} potential arbitrage opportunities")
        
        return opportunities
    
    async def generate_potential_paths(self, base_token: str, quote_tokens: List[str]) -> List[Dict[str, Any]]:
        """
        Generate potential arbitrage paths using AI optimization.
        
        Args:
            base_token: Base token to trade
            quote_tokens: Quote tokens to consider
            
        Returns:
            List of potential arbitrage paths
        """
        self.logger.info(f"Generating potential paths for {base_token} with {quote_tokens}")
        
        # Define the dexes to consider
        dexes = self.config.get("dexes", ["Uniswap V3", "SushiSwap", "PancakeSwap V3"])
        
        # Use AI to optimize the path
        path_optimization = await self.ai_client.optimize_path(
            tokens=[base_token] + quote_tokens,
            dexes=dexes,
            optimization_target=self.config.get("optimization_target", "profit")
        )
        
        self.logger.info(f"AI path optimization complete. Found path with {path_optimization['path_length']} steps")
        
        # In a real implementation, we might generate multiple paths
        # For this example, we'll create 3 paths with variations
        
        paths = [
            {
                "id": str(uuid.uuid4()),
                "path": path_optimization["path"],
                "estimated_profit": path_optimization["estimated_metrics"]["expected_profit_percentage"],
                "gas_estimate": path_optimization["estimated_metrics"]["total_gas"],
                "success_probability": path_optimization["estimated_metrics"]["success_probability"],
                "source": "ai_optimized"
            }
        ]
        
        # Create a second path with a variation (for demonstration)
        if len(path_optimization["path"]) > 1:
            # Create a copy with a modified path
            modified_path = path_optimization["path"].copy()
            
            # Swap two DEXes to create a variation
            if len(modified_path) >= 2:
                modified_path[0]["dex"], modified_path[1]["dex"] = modified_path[1]["dex"], modified_path[0]["dex"]
            
            # Adjust the profit estimate slightly
            profit_adjustment = random.uniform(0.8, 1.2)
            
            paths.append({
                "id": str(uuid.uuid4()),
                "path": modified_path,
                "estimated_profit": f"{float(path_optimization['estimated_metrics']['expected_profit_percentage'].strip('%')) * profit_adjustment}%",
                "gas_estimate": int(path_optimization["estimated_metrics"]["total_gas"] * random.uniform(0.9, 1.1)),
                "success_probability": path_optimization["estimated_metrics"]["success_probability"] * random.uniform(0.9, 1.0),
                "source": "ai_variant"
            })
        
        # Create a third path as a simplified version
        if len(path_optimization["path"]) > 2:
            # Create a shorter path
            simplified_path = [path_optimization["path"][0], path_optimization["path"][-1]]
            
            # Adjust the profit estimate for the simplified path
            profit_adjustment = random.uniform(0.7, 0.9)  # Typically less profitable but simpler
            
            paths.append({
                "id": str(uuid.uuid4()),
                "path": simplified_path,
                "estimated_profit": f"{float(path_optimization['estimated_metrics']['expected_profit_percentage'].strip('%')) * profit_adjustment}%",
                "gas_estimate": int(path_optimization["estimated_metrics"]["total_gas"] * random.uniform(0.6, 0.8)),
                "success_probability": path_optimization["estimated_metrics"]["success_probability"] * random.uniform(1.0, 1.05),
                "source": "ai_simplified"
            })
        
        return paths
    
    async def evaluate_paths(self, paths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate and rank arbitrage paths based on AI risk assessment.
        
        Args:
            paths: List of potential paths to evaluate
            
        Returns:
            Ranked list of arbitrage opportunities
        """
        self.logger.info(f"Evaluating {len(paths)} potential paths")
        
        opportunities = []
        
        for path_data in paths:
            path = path_data["path"]
            
            # Get tokens involved in this path
            tokens = list(set([step["from_token"] for step in path] + [step["to_token"] for step in path]))
            
            # Assess risk for this path
            risk_assessment = await self.ai_client.assess_risk(
                tokens=tokens,
                path=path,
                network=self.config.get("network", "ethereum")
            )
            
            # Optimize execution parameters
            execution_params = await self.ai_client.optimize_execution(
                path=path,
                network=self.config.get("network", "ethereum")
            )
            
            # Determine if this opportunity meets our criteria based on risk tolerance
            risk_score = risk_assessment["overall_risk_score"]
            risk_threshold = 0.8 if self.risk_tolerance == "high" else 0.5 if self.risk_tolerance == "medium" else 0.3
            
            if risk_score <= risk_threshold:
                # Create an opportunity with all the AI-enhanced data
                opportunity = {
                    "id": path_data["id"],
                    "path": path,
                    "tokens": tokens,
                    "estimated_profit": path_data["estimated_profit"],
                    "risk_score": risk_score,
                    "risk_category": risk_assessment["risk_category"],
                    "success_probability": path_data["success_probability"],
                    "gas_estimate": path_data["gas_estimate"],
                    "execution_params": execution_params["optimized_parameters"],
                    "specific_risks": risk_assessment["specific_risks"],
                    "mitigations": risk_assessment["mitigations"],
                    "expected_outcomes": execution_params["expected_outcomes"],
                    "confidence": min(risk_assessment["confidence"], execution_params["confidence"]),
                    "source": path_data["source"],
                    "timestamp": datetime.datetime.now().isoformat()
                }
                
                # Only include opportunities with sufficient confidence
                if opportunity["confidence"] >= self.confidence_threshold:
                    opportunities.append(opportunity)
            else:
                self.logger.info(f"Path {path_data['id']} rejected due to high risk score: {risk_score}")
        
        # Sort opportunities by expected profit (considering risk)
        return sorted(
            opportunities,
            key=lambda x: float(x["estimated_profit"].strip("%")) * x["success_probability"] * (1 - x["risk_score"]),
            reverse=True
        )
    
    async def execute(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an arbitrage opportunity with AI-optimized parameters.
        
        Args:
            opportunity: The arbitrage opportunity to execute
            
        Returns:
            Execution result
        """
        self.logger.info(f"Executing opportunity {opportunity['id']}")
        
        # Log the path and expected profit
        path_str = " → ".join([f"{step['from_token']} ({step['dex']}) → {step['to_token']}" for step in opportunity["path"]])
        self.logger.info(f"Path: {path_str}")
        self.logger.info(f"Expected profit: {opportunity['estimated_profit']}")
        self.logger.info(f"Using AI-optimized execution parameters")
        
        # In a real implementation, this would execute the trade on-chain
        # For this example, we'll simulate the execution
        
        # Simulate execution time
        execution_time_ms = random.randint(
            int(opportunity["execution_params"]["execution_time_ms"] * 0.8),
            int(opportunity["execution_params"]["execution_time_ms"] * 1.2)
        )
        
        # Wait to simulate execution
        await asyncio.sleep(execution_time_ms / 1000)
        
        # Determine if the execution was successful based on the success probability
        success = random.random() < opportunity["success_probability"]
        
        # Calculate actual profit (with some deviation from estimate)
        expected_profit_pct = float(opportunity["estimated_profit"].strip("%"))
        actual_profit_deviation = random.uniform(-0.3, 0.2)  # Can be worse or better, but typically worse
        actual_profit_pct = expected_profit_pct * (1 + actual_profit_deviation)
        
        # Calculate gas used (with some deviation from estimate)
        gas_used = int(opportunity["gas_estimate"] * random.uniform(0.9, 1.2))
        
        # Result data
        result = {
            "opportunity_id": opportunity["id"],
            "success": success,
            "execution_time_ms": execution_time_ms,
            "path": opportunity["path"],
            "timestamp": datetime.datetime.now().isoformat(),
            "gas_used": gas_used,
            "gas_price_gwei": opportunity["execution_params"]["gas_price_gwei"],
            "gas_cost_usd": round(random.uniform(5, 100), 2),
            "slippage_used": opportunity["execution_params"]["slippage_tolerance_percent"],
            "used_flashbots": opportunity["execution_params"]["use_flashbots"],
        }
        
        if success:
            # Add successful execution data
            result.update({
                "profit_percentage": f"{actual_profit_pct:.2f}%",
                "profit_usd": round(random.uniform(10, 500), 2),
                "net_profit_usd": round(random.uniform(5, 400), 2),
                "execution_details": {
                    "flash_loan_fee_usd": round(random.uniform(1, 20), 2) if opportunity["execution_params"].get("flash_loan_provider") else 0,
                    "mev_protection_saved_usd": round(random.uniform(1, 50), 2) if opportunity["execution_params"]["use_flashbots"] else 0,
                }
            })
            self.logger.info(f"Execution successful! Profit: {result['profit_percentage']}")
        else:
            # Add failure details
            failure_reason = random.choice([
                "price slippage exceeded tolerance",
                "insufficient liquidity",
                "transaction reverted",
                "gas price too low",
                "timeout waiting for confirmation"
            ])
            result.update({
                "failure_reason": failure_reason,
                "loss_usd": round(random.uniform(1, 30), 2),  # Gas costs lost
            })
            self.logger.info(f"Execution failed: {failure_reason}")
        
        return result


async def demonstrate_market_analysis():
    """Demonstrate AI-powered market analysis."""
    logger.info("Demonstrating AI market analysis...")
    
    # Initialize the Glama AI client
    ai_client = GlamaAIClient()
    
    # Perform market analysis
    analysis = await ai_client.analyze_market(
        base_token="WETH",
        quote_tokens=["USDC", "USDT", "DAI", "WBTC"],
        network="ethereum"
    )
    
    logger.info(f"Market sentiment: {analysis['market_sentiment']}")
    logger.info(f"Volatility: {analysis['volatility']}")
    logger.info(f"Liquidity trend: {analysis['liquidity_trend']}")
    logger.info(f"Gas price recommendation: {analysis['gas_price_recommendation']} gwei")
    
    # Display token-specific analysis
    logger.info("\nToken Analysis:")
    for token, token_data in analysis["token_analysis"].items():
        logger.info(f"- {token}: {token_data['price_trend']} trend, {token_data['price_movement_prediction_1h']} expected movement")
    
    # Display DEX-specific analysis
    logger.info("\nDEX Analysis:")
    for dex, dex_data in analysis["dex_analysis"].items():
        logger.info(f"- {dex}: Liquidity score {dex_data['liquidity_score']}, {dex_data['slippage_estimate']} slippage")
    
    # Display arbitrage conditions
    logger.info("\nArbitrage Conditions:")
    logger.info(f"Favorable: {analysis['arbitrage_conditions']['favorable']}")
    logger.info(f"Optimal time window: {analysis['arbitrage_conditions']['optimal_time_window_seconds']} seconds")
    logger.info(f"Confidence: {analysis['arbitrage_conditions']['confidence']}")


async def demonstrate_price_prediction():
    """Demonstrate AI price prediction capabilities."""
    logger.info("Demonstrating AI price prediction...")
    
    # Initialize the Glama AI client
    ai_client = GlamaAIClient()
    
    # Predict price for ETH
    prediction = await ai_client.predict_price(
        token="WETH",
        timeframe="1h",
        network="ethereum"
    )
    
    logger.info(f"Price prediction for {prediction['token']} over {prediction['timeframe']}:")
    logger.info(f"Direction: {prediction['prediction']['direction']}")
    logger.info(f"Magnitude: {prediction['prediction']['magnitude_percent']}")
    logger.info(f"Confidence: {prediction['prediction']['confidence']}")
    
    # Display prediction factors
    logger.info("\nPrediction Factors:")
    for factor, value in prediction["prediction"]["factors"].items():
        logger.info(f"- {factor}: {value}")
    
    # Display supporting evidence
    logger.info("\nSupporting Evidence:")
    for evidence_type, evidence in prediction["supporting_evidence"].items():
        logger.info(f"- {evidence_type}: {evidence}")


async def demonstrate_path_optimization():
    """Demonstrate AI-powered arbitrage path optimization."""
    logger.info("Demonstrating AI path optimization...")
    
    # Initialize the Glama AI client
    ai_client = GlamaAIClient()
    
    # Define tokens and DEXes
    tokens = ["WETH", "USDC", "USDT", "DAI", "WBTC"]
    dexes = ["Uniswap V3", "SushiSwap", "PancakeSwap V3"]
    
    # Optimize arbitrage path
    path_optimization = await ai_client.optimize_path(
        tokens=tokens,
        dexes=dexes,
        optimization_target="profit"
    )
    
    logger.info(f"Optimized path with {path_optimization['path_length']} steps:")
    
    # Display the path
    for i, step in enumerate(path_optimization["path"]):
        logger.info(f"Step {i+1}: {step['from_token']} → {step['to_token']} via {step['dex']} (Slippage: {step['expected_slippage']})")
    
    # Display estimated metrics
    logger.info("\nEstimated Metrics:")
    for metric, value in path_optimization["estimated_metrics"].items():
        logger.info(f"- {metric}: {value}")
    
    # Display flash loan recommendation
    logger.info("\nFlash Loan Recommendation:")
    flash_loan = path_optimization["flash_loan_recommendation"]
    logger.info(f"Recommended: {flash_loan['recommended']}")
    if flash_loan['recommended']:
        logger.info(f"Provider: {flash_loan['provider']}")
        logger.info(f"Estimated fee: {flash_loan['estimated_fee']}")


async def demonstrate_risk_assessment():
    """Demonstrate AI-powered risk assessment."""
    logger.info("Demonstrating AI risk assessment...")
    
    # Initialize the Glama AI client
    ai_client = GlamaAIClient()
    
    # Create a sample path
    path = [
        {
            "from_token": "WETH",
            "to_token": "USDC",
            "dex": "Uniswap V3",
            "expected_slippage": "0.1%",
            "fee_tier": "0.3%",
            "gas_estimate": 150000
        },
        {
            "from_token": "USDC",
            "to_token": "WBTC",
            "dex": "SushiSwap",
            "expected_slippage": "0.2%",
            "fee_tier": "0.3%",
            "gas_estimate": 180000
        },
        {
            "from_token": "WBTC",
            "to_token": "WETH",
            "dex": "PancakeSwap V3",
            "expected_slippage": "0.15%",
            "fee_tier": "0.3%",
            "gas_estimate": 160000
        }
    ]
    
    # Assess risks
    risk_assessment = await ai_client.assess_risk(
        tokens=["WETH", "USDC", "WBTC"],
        path=path,
        network="ethereum"
    )
    
    logger.info(f"Overall risk score: {risk_assessment['overall_risk_score']} ({risk_assessment['risk_category']} risk)")
    
    # Display specific risks
    logger.info("\nSpecific Risks:")
    for risk_type, score in risk_assessment["specific_risks"].items():
        logger.info(f"- {risk_type}: {score}")
    
    # Display recommended mitigations
    logger.info("\nRecommended Mitigations:")
    for mitigation, value in risk_assessment["mitigations"].items():
        logger.info(f"- {mitigation}: {value}")
    
    # Display token-specific risks
    logger.info("\nToken-Specific Risks:")
    for token, risks in risk_assessment["token_risks"].items():
        logger.info(f"- {token}: liquidity risk {risks['liquidity_risk']}, volatility risk {risks['volatility_risk']}")


async def demonstrate_execution_optimization():
    """Demonstrate AI-powered execution parameter optimization."""
    logger.info("Demonstrating AI execution optimization...")
    
    # Initialize the Glama AI client
    ai_client = GlamaAIClient()
    
    # Create a sample path
    path = [
        {
            "from_token": "WETH",
            "to_token": "USDC",
            "dex": "Uniswap V3",
            "expected_slippage": "0.1%",
            "fee_tier": "0.3%",
            "gas_estimate": 150000
        },
        {
            "from_token": "USDC",
            "to_token": "DAI",
            "dex": "SushiSwap",
            "expected_slippage": "0.05%",
            "fee_tier": "0.3%",
            "gas_estimate": 120000
        },
        {
            "from_token": "DAI",
            "to_token": "WETH",
            "dex": "PancakeSwap V3",
            "expected_slippage": "0.15%",
            "fee_tier": "0.3%",
            "gas_estimate": 160000
        }
    ]
    
    # Optimize execution parameters
    execution_params = await ai_client.optimize_execution(
        path=path,
        network="ethereum"
    )
    
    logger.info("Current Network Conditions:")
    logger.info(f"- Gas price: {execution_params['current_conditions']['gas_price_gwei']} gwei")
    logger.info(f"- Network congestion: {execution_params['current_conditions']['network_congestion']}")
    logger.info(f"- MEV activity: {execution_params['current_conditions']['mev_activity']}")
    
    logger.info("\nOptimized Parameters:")
    for param, value in execution_params["optimized_parameters"].items():
        logger.info(f"- {param}: {value}")
    
    logger.info("\nExpected Outcomes:")
    for outcome, value in execution_params["expected_outcomes"].items():
        logger.info(f"- {outcome}: {value}")


async def demonstrate_ai_enhanced_strategy():
    """Demonstrate the complete AI-enhanced arbitrage strategy."""
    logger.info("Demonstrating AI-enhanced arbitrage strategy...")
    
    # Create configuration for the AI-enhanced strategy
    config = {
        "name": "GlamaEnhancedStrategy",
        "version": "1.0.0",
        "network": "ethereum",
        "dexes": ["Uniswap V3", "SushiSwap", "PancakeSwap V3"],
        "optimization_target": "profit",
        "ai_settings": {
            "influence_level": 0.8,  # 0-1, higher means more AI influence
            "risk_tolerance": "medium",  # low, medium, high
            "prediction_time_horizon": "short_term",  # short_term, medium_term, long_term
            "confidence_threshold": 0.7  # Minimum confidence for AI recommendations
        },
        "optimization_targets": {
            "profit": 0.7,  # Weight for profit maximization
            "gas": 0.2,     # Weight for gas optimization
            "risk": 0.1     # Weight for risk minimization
        }
    }
    
    # Initialize the AI-enhanced strategy
    strategy = GlamaEnhancedArbitrageStrategy(config)
    
    # Find arbitrage opportunities
    opportunities = await strategy.find_opportunities(
        base_token="WETH",
        quote_tokens=["USDC", "USDT", "DAI", "WBTC"]
    )
    
    if opportunities:
        logger.info(f"Found {len(opportunities)} opportunities")
        
        # Display the top opportunity
        top_opportunity = opportunities[0]
        
        logger.info("\nTop Opportunity Details:")
        logger.info(f"ID: {top_opportunity['id']}")
        logger.info(f"Estimated profit: {top_opportunity['estimated_profit']}")
        logger.info(f"Risk score: {top_opportunity['risk_score']} ({top_opportunity['risk_category']})")
        logger.info(f"Success probability: {top_opportunity['success_probability']}")
        
        # Display the path
        logger.info("\nArbitrage Path:")
        for i, step in enumerate(top_opportunity["path"]):
            logger.info(f"Step {i+1}: {step['from_token']} → {step['to_token']} via {step['dex']}")
        
        # Display execution parameters
        logger.info("\nAI-Optimized Execution Parameters:")
        for param, value in top_opportunity["execution_params"].items():
            logger.info(f"- {param}: {value}")
        
        # Execute the opportunity
        logger.info("\nExecuting the opportunity...")
        result = await strategy.execute(top_opportunity)
        
        logger.info("\nExecution Result:")
        logger.info(f"Success: {result['success']}")
        logger.info(f"Execution time: {result['execution_time_ms']} ms")
        logger.info(f"Gas used: {result['gas_used']}")
        
        if result['success']:
            logger.info(f"Profit: {result['profit_percentage']}")
            logger.info(f"Profit (USD): ${result['profit_usd']}")
            logger.info(f"Net profit (USD): ${result['net_profit_usd']}")
        else:
            logger.info(f"Failure reason: {result['failure_reason']}")
            logger.info(f"Loss (USD): ${result['loss_usd']}")
    else:
        logger.info("No profitable opportunities found")


async def main():
    """Main function demonstrating Glama AI enhanced arbitrage."""
    logger.info("Starting Glama AI Enhanced Strategy Example")
    
    try:
        # Demonstrate various AI capabilities
        logger.info("\n" + "="*50)
        logger.info("1. Market Analysis")
        logger.info("="*50)
        await demonstrate_market_analysis()
        
        logger.info("\n" + "="*50)
        logger.info("2. Price Prediction")
        logger.info("="*50)
        await demonstrate_price_prediction()
        
        logger.info("\n" + "="*50)
        logger.info("3. Path Optimization")
        logger.info("="*50)
        await demonstrate_path_optimization()
        
        logger.info("\n" + "="*50)
        logger.info("4. Risk Assessment")
        logger.info("="*50)
        await demonstrate_risk_assessment()
        
        logger.info("\n" + "="*50)
        logger.info("5. Execution Optimization")
        logger.info("="*50)
        await demonstrate_execution_optimization()
        
        logger.info("\n" + "="*50)
        logger.info("6. Complete AI-Enhanced Strategy")
        logger.info("="*50)
        await demonstrate_ai_enhanced_strategy()
        
        logger.info("\nExample completed successfully")
    except Exception as e:
        logger.error(f"Error in example: {str(e)}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())