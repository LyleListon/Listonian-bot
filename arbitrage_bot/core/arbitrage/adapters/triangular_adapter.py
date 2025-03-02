"""
Triangular Arbitrage Adapter

This module contains adapters to integrate the existing Triangular Arbitrage
logic with the new arbitrage system architecture.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional

from ..interfaces import OpportunityDetector
from ..models import (
    ArbitrageOpportunity, 
    ArbitrageRoute, 
    RouteStep, 
    MarketCondition,
    OpportunityStatus,
    StrategyType,
    GasEstimate
)
from ...execution.triangular_arbitrage import TriangularArbitrage

logger = logging.getLogger(__name__)


class TriangularArbitrageDetector(OpportunityDetector):
    """
    Adapter that converts the existing TriangularArbitrage implementation
    to work with the new OpportunityDetector interface.
    """
    
    def __init__(
        self,
        triangular_arbitrage: TriangularArbitrage,
        web3_manager: Any,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the detector.
        
        Args:
            triangular_arbitrage: Existing TriangularArbitrage instance
            web3_manager: Web3Manager instance for blockchain interactions
            config: Configuration dictionary
        """
        self.triangular_arbitrage = triangular_arbitrage
        self.web3_manager = web3_manager
        self.config = config or {}
        
        # Get token metadata (for symbols)
        self.token_metadata = self.config.get("tokens", {})
        
        logger.info("TriangularArbitrageDetector initialized")
    
    async def detect_opportunities(
        self,
        market_condition: MarketCondition,
        max_results: int = 10,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Detect triangular arbitrage opportunities.
        
        Args:
            market_condition: Current market conditions
            max_results: Maximum number of opportunities to return
            **kwargs: Additional detector-specific parameters
            
        Returns:
            List of detected arbitrage opportunities
        """
        logger.info("Detecting triangular arbitrage opportunities")
        
        try:
            # Get start amount based on market conditions (gas price)
            eth_price_usd = market_condition.eth_price_usd or 3000.0  # Default if not available
            
            # Adjust start amount based on gas price
            base_amount = 10**18  # 1 ETH in wei
            if market_condition.gas_price_gwei > 100:
                # Increase amount for high gas prices
                base_amount = 2 * 10**18  # 2 ETH
            
            # Find opportunities using existing implementation
            results = await self.triangular_arbitrage.find_opportunities(
                start_amount=base_amount
            )
            
            # Convert to new model format
            opportunities = []
            for idx, result in enumerate(results[:max_results]):
                opportunity = self._convert_to_opportunity(result, eth_price_usd)
                
                # Adjust opportunity based on market conditions
                self._adjust_for_market_conditions(opportunity, market_condition)
                
                opportunities.append(opportunity)
            
            logger.info(f"Found {len(opportunities)} triangular arbitrage opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error detecting triangular arbitrage opportunities: {e}")
            return []
    
    def _convert_to_opportunity(
        self,
        result: Dict[str, Any],
        eth_price_usd: float
    ) -> ArbitrageOpportunity:
        """Convert triangular arbitrage result to ArbitrageOpportunity."""
        # Extract route information
        route_data = result.get("route", [])
        
        # Create route steps
        steps = []
        for hop in route_data:
            # Extract token addresses
            token0 = hop.get("token0", "")
            token1 = hop.get("token1", "")
            
            # Create route step
            step = RouteStep(
                dex_id=hop.get("dex", "unknown"),
                token_in_address=token0,
                token_out_address=token1,
                pool_address=hop.get("pool_info", {}).get("address"),
                pool_fee=hop.get("pool_info", {}).get("fee"),
                pool_type=hop.get("pool_info", {}).get("type")
            )
            steps.append(step)
        
        # Create full route
        if steps:
            route = ArbitrageRoute(
                steps=steps,
                input_token_address=steps[0].token_in_address,
                output_token_address=steps[-1].token_out_address
            )
        else:
            # Create empty route if no steps
            route = ArbitrageRoute(
                steps=[],
                input_token_address="",
                output_token_address=""
            )
        
        # Extract financial details
        amounts = result.get("amounts", [])
        input_amount = amounts[0] if amounts else 0
        expected_output = amounts[-1] if len(amounts) > 1 else 0
        profit = expected_output - input_amount if input_amount > 0 else 0
        
        # Get token symbols if available
        input_token_symbol = self._get_token_symbol(route.input_token_address)
        output_token_symbol = self._get_token_symbol(route.output_token_address)
        
        # Calculate USD values
        if eth_price_usd and input_amount > 0:
            input_amount_eth = input_amount / 10**18
            input_amount_usd = input_amount_eth * eth_price_usd
            
            profit_eth = profit / 10**18
            profit_usd = profit_eth * eth_price_usd
        else:
            input_amount_usd = None
            profit_usd = None
        
        # Create gas estimate
        gas_limit = self.config.get("triangular_gas_limit", 600000)
        gas_price = result.get("gas_price", 0)
        if gas_price == 0:
            gas_price = int(50e9)  # Default 50 Gwei
        
        gas_estimate = GasEstimate(
            gas_limit=gas_limit,
            gas_price=gas_price,
            total_cost_wei=gas_limit * gas_price
        )
        
        # Create opportunity
        opportunity = ArbitrageOpportunity(
            id=str(uuid.uuid4()),
            strategy_type=StrategyType.TRIANGULAR,
            status=OpportunityStatus.DISCOVERED,
            route=route,
            input_amount=input_amount,
            expected_output=expected_output,
            expected_profit=profit,
            gas_estimate=gas_estimate,
            profit_margin=result.get("profit_percent", 0),
            input_token_symbol=input_token_symbol,
            output_token_symbol=output_token_symbol,
            input_amount_usd=input_amount_usd,
            expected_profit_usd=profit_usd,
            confidence_score=result.get("confidence", 0.5),
            source_component="triangular_arbitrage"
        )
        
        return opportunity
    
    def _adjust_for_market_conditions(
        self,
        opportunity: ArbitrageOpportunity,
        market_condition: MarketCondition
    ) -> None:
        """Adjust opportunity confidence based on market conditions."""
        # Start with base confidence
        base_confidence = opportunity.confidence_score
        
        # Adjust for network congestion (lower confidence in congested network)
        congestion_factor = 1.0 - market_condition.network_congestion * 0.5
        
        # Adjust for volatility (lower confidence in high volatility)
        volatility_factor = 1.0 - market_condition.volatility_index * 0.7
        
        # Adjust for token liquidity
        liquidity_factor = 1.0
        input_token = opportunity.route.input_token_address.lower()
        if input_token in market_condition.liquidity_levels:
            liquidity_factor = 0.3 + 0.7 * market_condition.liquidity_levels[input_token]
        
        # Calculate final confidence
        final_confidence = base_confidence * congestion_factor * volatility_factor * liquidity_factor
        
        # Update opportunity
        opportunity.confidence_score = max(0.0, min(1.0, final_confidence))
    
    def _get_token_symbol(self, token_address: str) -> Optional[str]:
        """Get token symbol from token metadata."""
        token_address = token_address.lower()
        
        # Check well-known tokens
        if token_address == "0x4200000000000000000000000000000000000006":
            return "WETH"
        elif token_address == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913":
            return "USDC"
        elif token_address == "0x50c5725949a6f0c72e6c4a641f24049a917db0cb":
            return "USDT"
        
        # Check token metadata
        for symbol, data in self.token_metadata.items():
            if data.get("address", "").lower() == token_address:
                return symbol
        
        return None


async def create_triangular_arbitrage_detector(
    dex_manager: Any,
    web3_manager: Any,
    config: Dict[str, Any] = None
) -> TriangularArbitrageDetector:
    """
    Create and initialize a triangular arbitrage detector.
    
    Args:
        dex_manager: DexManager instance for DEX interactions
        web3_manager: Web3Manager instance for blockchain interactions
        config: Configuration dictionary
        
    Returns:
        Initialized triangular arbitrage detector
    """
    from ...execution.triangular_arbitrage import TriangularArbitrage
    
    # Create triangular arbitrage instance
    triangular_arbitrage = TriangularArbitrage(
        config=config or {},
        dex_interfaces=dex_manager.get_dex_interfaces()
    )
    
    # Create detector
    detector = TriangularArbitrageDetector(
        triangular_arbitrage=triangular_arbitrage,
        web3_manager=web3_manager,
        config=config
    )
    
    return detector