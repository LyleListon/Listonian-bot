"""Detect arbitrage opportunities."""

import logging
import asyncio
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal

from ...utils.mcp_client import (
    validate_prices,
    assess_opportunity,
    evaluate_risk,
    use_market_analysis
)
from ..dex.aerodrome import AerodromeDEX
from ..dex.swapbased import SwapBasedDEX
from ..dex.rocketswap import RocketSwapDEX

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""
    buy_dex: str
    sell_dex: str
    token_pair: str
    profit_percent: float
    buy_amount: float
    sell_amount: float
    estimated_gas: float
    net_profit: float
    priority: float
    route_type: str = "direct"  # "direct", "triangular", or "cross_dex"
    intermediate_token: str = None
    intermediate_dex: str = None
    confidence_score: float = 0.0
    market_conditions: Dict[str, Any] = None

class OpportunityDetector:
    """Detects arbitrage opportunities across DEXes."""
    
    def __init__(self, config, web3_manager, balance_manager=None):
        self.config = config
        self.w3 = web3_manager
        self.balance_manager = None  # Will be set during initialization
        self.min_profit = float(config["trading"]["min_profit_usd"])
        self.max_slippage = float(config["trading"]["safety"]["protection_limits"]["max_slippage_percent"]) / 100
        self.max_trade_size = float(config["trading"]["max_trade_size_usd"])
        
        # Initialize DEX interfaces
        self.dex_interfaces = {}
        self.initialized = False
        
        logger.info("OpportunityDetector instance created")

    async def initialize(self):
        """Initialize DEX interfaces and get balance manager instance."""
        if self.initialized:
            return
            
        try:
            # Get balance manager singleton instance
            from ..balance_manager import BalanceManager
            self.balance_manager = await BalanceManager.get_instance(
                web3_manager=self.w3,
                analytics=None,  # These will be set by the first instance
                ml_system=None,
                monitor=None,
                dex_manager=None
            )
            
            if not self.balance_manager:
                raise ValueError("Failed to get balance manager instance")
                
            if not hasattr(self.balance_manager, 'check_pair_balance'):
                raise ValueError("Balance manager missing check_pair_balance method")
                
            # Initialize DEX interfaces
            dex_classes = {
                "aerodrome": AerodromeDEX,
                "swapbased": SwapBasedDEX,
                "rocketswap": RocketSwapDEX
            }
            
            # Initialize all configured DEXes
            for dex_name, dex_config in self.config.get("dexes", {}).items():
                if dex_name in dex_classes:
                    dex = dex_classes[dex_name](self.w3, dex_config)
                    if await dex.initialize():
                        self.dex_interfaces[dex_name] = dex
                        logger.info(f"Initialized {dex_name} interface")
                        
            # Test balance manager functionality
            test_token0 = self.config["tokens"]["WETH"]["address"]
            test_token1 = self.config["tokens"]["USDC"]["address"]
            try:
                await self.balance_manager.check_pair_balance(test_token0, test_token1)
                logger.info("Balance manager check_pair_balance test successful")
            except Exception as e:
                logger.error(f"Balance manager check_pair_balance test failed: {e}")
                raise
                
            self.initialized = True
            logger.info("OpportunityDetector initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpportunityDetector: {e}")
            raise

    async def verify_liquidity(self, token: str, dex: str) -> bool:
        """Verify liquidity conditions using Market Analysis Server."""
        try:
            conditions = await use_market_analysis("assess_market_conditions", {
                "token": token,
                "metrics": ["liquidity", "volume"]
            })
            
            liquidity = conditions.get("liquidity", {})
            volume = conditions.get("volume", {})
            
            liquidity_config = self.config["trading"]["liquidity"]
            min_liquidity = liquidity_config["min_pool_depth_usd"]
            min_volume = liquidity_config["min_volume_24h_usd"]
            min_confidence = liquidity_config["min_confidence"]
            
            has_sufficient_liquidity = liquidity.get("value", 0) >= min_liquidity
            has_sufficient_volume = volume.get("value", 0) >= min_volume
            confidence = volume.get("confidence", 0)
            
            logger.debug(
                f"Liquidity metrics for {token} on {dex}:\n"
                f"  Liquidity: ${liquidity.get('value', 0):,.2f} (min: ${min_liquidity:,.2f})\n"
                f"  Volume: ${volume.get('value', 0):,.2f} (min: ${min_volume:,.2f})\n"
                f"  Confidence: {confidence:.2f} (min: {min_confidence:.2f})"
            )
            
            conditions_met = (
                has_sufficient_liquidity and 
                has_sufficient_volume and 
                confidence >= min_confidence
            )
            
            if not conditions_met:
                if not has_sufficient_liquidity:
                    logger.warning(f"Insufficient liquidity for {token} on {dex}")
                if not has_sufficient_volume:
                    logger.warning(f"Insufficient volume for {token} on {dex}")
                if confidence < min_confidence:
                    logger.warning(f"Low confidence for {token} on {dex}")
            
            return conditions_met
            
        except Exception as e:
            logger.error(f"Failed to verify liquidity for {token} on {dex}: {e}")
            return False

    async def get_prices_parallel(self, pair: Dict, dexes: Dict) -> Dict[str, Dict[str, float]]:
        """Fetch prices from all DEXes in parallel."""
        async def fetch_price(dex_name: str, dex_config: Dict) -> Tuple[str, Dict[str, float]]:
            try:
                if dex_name in self.dex_interfaces:
                    dex = self.dex_interfaces[dex_name]
                    pool_info = await dex.get_pool_info(pair["token0"], pair["token1"])
                    
                    if dex_name == "aerodrome":
                        # Get both stable and volatile pool prices
                        prices = {}
                        try:
                            amounts_stable = await dex.get_amounts_out(
                                10**18,
                                [pair["token0"], pair["token1"]],
                                [True]
                            )
                            prices["stable"] = amounts_stable[-1] / 10**18
                        except Exception as e:
                            logger.debug(f"No stable pool price: {e}")
                            
                        try:
                            amounts_volatile = await dex.get_amounts_out(
                                10**18,
                                [pair["token0"], pair["token1"]],
                                [False]
                            )
                            prices["volatile"] = amounts_volatile[-1] / 10**18
                        except Exception as e:
                            logger.debug(f"No volatile pool price: {e}")
                            
                    elif dex_name == "swapbased":
                        # SwapBased uses standard V2 pools
                        amounts = await dex.get_amounts_out(
                            10**18,
                            [pair["token0"], pair["token1"]]
                        )
                        prices = {"v2": amounts[-1] / 10**18}
                        
                    elif dex_name == "rocketswap":
                        # RocketSwap with dynamic fees
                        amounts = await dex.get_amounts_out(
                            10**18,
                            [pair["token0"], pair["token1"]]
                        )
                        prices = {"dynamic": amounts[-1] / 10**18}
                        
                    return dex_name, prices
                    
            except Exception as e:
                logger.debug(f"Failed to get price from {dex_name}: {e}")
                return dex_name, None

        tasks = [
            fetch_price(dex_name, dex_config)
            for dex_name, dex_config in dexes.items()
        ]
        results = await asyncio.gather(*tasks)
        return {
            dex_name: price
            for dex_name, price in results
            if price is not None
        }

    async def detect_opportunities(self) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities across configured DEXes."""
        try:
            await self.ensure_initialized()
            opportunities = []
            
            if not self.balance_manager:
                logger.error("Balance manager not initialized")
                await self.cleanup()
                return []
                
            if not self.initialized:
                logger.error("OpportunityDetector not properly initialized")
                await self.cleanup()
                return []
                
            pairs = sorted(
                self.config.get("pairs", []),
                key=lambda x: (x.get("priority", 0), x.get("historical_profit", 0)),
                reverse=True
            )
            dexes = self.config.get("dexes", {})

            for pair in pairs:
                try:
                    # Get token addresses from config
                    token0_addr = self.config["tokens"][pair["token0"]]["address"]
                    token1_addr = self.config["tokens"][pair["token1"]]["address"]
                    
                    if not await self.balance_manager.check_pair_balance(
                        token0_addr, token1_addr
                    ):
                        continue
                except Exception as e:
                    logger.error(f"Error checking pair balance: {e}")
                    continue

                # Verify liquidity across all DEXes
                liquidity_checks = await asyncio.gather(*[
                    self.verify_liquidity(pair["token0"], dex_name)
                    for dex_name in dexes
                ])
                
                if not any(liquidity_checks):
                    logger.info(f"Skipping pair {pair['token0']}/{pair['token1']} due to insufficient liquidity")
                    continue

                # Validate prices with MCP
                token_prices = await validate_prices([pair["token0"], pair["token1"]])
                if not token_prices:
                    logger.warning(f"Could not validate prices for {pair['token0']}/{pair['token1']}")
                    continue

                # Get prices from all DEXes
                prices = await self.get_prices_parallel(pair, dexes)

                # Check for cross-DEX opportunities
                for buy_dex, buy_prices in prices.items():
                    for sell_dex, sell_prices in prices.items():
                        if buy_dex == sell_dex:
                            continue
                            
                        for buy_pool, buy_price in buy_prices.items():
                            for sell_pool, sell_price in sell_prices.items():
                                profit_percent = (sell_price - buy_price) / buy_price
                                
                                if profit_percent > self.min_profit / self.max_trade_size:
                                    logger.info(
                                        f"Found cross-DEX opportunity:\n"
                                        f"  Buy: {buy_dex} ({buy_pool})\n"
                                        f"  Sell: {sell_dex} ({sell_pool})\n"
                                        f"  Profit: {profit_percent*100:.2f}%"
                                    )
                                    
                                    # Validate with market analysis
                                    assessment = await use_market_analysis(
                                        "analyze_opportunities",
                                        {
                                            "token": pair["token0"],
                                            "days": 1
                                        }
                                    )
                                    
                                    if assessment.get("success_probability", 0) > 0.8:
                                        gas_estimate = await self._estimate_gas_cost(buy_dex, sell_dex)
                                        gas_cost = gas_estimate * await self.w3.eth.gas_price
                                        net_profit = profit_percent * self.max_trade_size - gas_cost
                                        
                                        if net_profit > self.min_profit:
                                            opportunities.append(
                                                ArbitrageOpportunity(
                                                    buy_dex=f"{buy_dex}_{buy_pool}",
                                                    sell_dex=f"{sell_dex}_{sell_pool}",
                                                    token_pair=f"{pair['token0']}/{pair['token1']}",
                                                    profit_percent=profit_percent,
                                                    buy_amount=self.max_trade_size,
                                                    sell_amount=self.max_trade_size * (1 - self.max_slippage),
                                                    estimated_gas=gas_estimate,
                                                    net_profit=net_profit,
                                                    priority=assessment.get("priority", 0),
                                                    route_type="cross_dex",
                                                    confidence_score=assessment.get("confidence", 0),
                                                    market_conditions=assessment
                                                )
                                            )

            # Sort opportunities by priority
            opportunities.sort(key=lambda x: x.priority, reverse=True)
            
            if opportunities:
                logger.info(f"Found {len(opportunities)} opportunities")
            return opportunities

        except Exception as e:
            logger.error(f"Error detecting opportunities: {e}", exc_info=True)
            return []

    async def ensure_initialized(self):
        """Ensure detector is initialized."""
        if not self.initialized:
            await self.initialize()
            
    async def cleanup(self):
        """Cleanup resources."""
        try:
            # Cancel any ongoing tasks
            if hasattr(self, '_tasks'):
                for task in self._tasks:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                        
            # Clear references
            self.balance_manager = None
            self.dex_interfaces.clear()
            self.initialized = False
            
            logger.info("OpportunityDetector cleanup complete")
        except Exception as e:
            logger.error(f"Error during OpportunityDetector cleanup: {e}")
            
    async def _estimate_gas_cost(self, buy_dex: str, sell_dex: str) -> int:
        """Estimate gas cost for arbitrage."""
        try:
            base_gas = 100000
            
            dex_gas = {
                "swapbased": 150000,
                "rocketswap": 160000,
                "aerodrome": 200000
            }
            
            total_gas = base_gas
            if buy_dex in dex_gas:
                total_gas += dex_gas[buy_dex]
            if sell_dex in dex_gas and sell_dex != buy_dex:
                total_gas += dex_gas[sell_dex]
                
            return total_gas
            
        except Exception as e:
            logger.error(f"Error estimating gas cost: {e}")
            return 500000  # Conservative fallback
            
    def _calculate_priority_score(
        self,
        profit_percent: float,
        net_profit: float,
        gas_cost: float,
        historical_success_rate: float,
        confidence_score: float
    ) -> float:
        """Calculate priority score for an opportunity."""
        profit_factor = min(net_profit / self.min_profit, 10.0)
        gas_factor = 1.0 / (1.0 + gas_cost / net_profit)
        success_factor = historical_success_rate
        confidence_factor = confidence_score
        
        profit_weight = 0.4
        gas_weight = 0.2
        success_weight = 0.2
        confidence_weight = 0.2
        
        return (
            profit_factor * profit_weight +
            gas_factor * gas_weight +
            success_factor * success_weight +
            confidence_factor * confidence_weight
        )
