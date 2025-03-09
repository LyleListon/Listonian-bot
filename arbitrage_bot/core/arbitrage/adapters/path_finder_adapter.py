"""
PathFinder Adapter

This module contains adapters to integrate the existing PathFinder
logic with the new arbitrage system architecture.
"""

import logging
import uuid
import time
from typing import Dict, List, Any, Optional, Tuple

from ..interfaces import OpportunityDetector, OpportunityValidator
from ..models import (
    ArbitrageOpportunity, 
    ArbitrageRoute, 
    RouteStep, 
    MarketCondition,
    OpportunityStatus,
    StrategyType,
    GasEstimate
)
from ...path_finder import PathFinder, ArbitragePath

logger = logging.getLogger(__name__)


class PathFinderDetector(OpportunityDetector):
    """
    Adapter that converts the existing PathFinder implementation
    to work with the new OpportunityDetector interface.
    """
    
    def __init__(
        self,
        path_finder: PathFinder,
        web3_manager: Any,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the detector.
        
        Args:
            path_finder: Existing PathFinder instance
            web3_manager: Web3Manager instance for blockchain interactions
            config: Configuration dictionary
        """
        self.path_finder = path_finder
        self.web3_manager = web3_manager
        self.config = config or {}
        
        # Base tokens to consider for arbitrage
        self.base_tokens = self.config.get("base_tokens", [
            "0x4200000000000000000000000000000000000006",  # WETH
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC
            "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"   # USDT
        ])
        
        # Token metadata (for symbols)
        self.token_metadata = self.config.get("tokens", {})
        
        logger.info("PathFinderDetector initialized")
    
    async def detect_opportunities(
        self,
        market_condition: MarketCondition,
        max_results: int = 10,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Detect arbitrage opportunities using PathFinder.
        
        Args:
            market_condition: Current market conditions
            max_results: Maximum number of opportunities to return
            **kwargs: Additional detector-specific parameters
            
        Returns:
            List of detected arbitrage opportunities
        """
        logger.info("Detecting arbitrage opportunities with PathFinder")
        
        try:
            # Set initial amount based on market conditions
            base_amount = self._calculate_base_amount(market_condition)
            
            all_opportunities = []
            
            # Try finding paths for each base token
            for token_address in self.base_tokens:
                try:
                    # Find arbitrage paths
                    arbitrage_paths = await self.path_finder.find_arbitrage_paths(
                        start_token_address=token_address,
                        amount_in=base_amount,
                        max_paths=max_results,
                        min_profit_threshold=kwargs.get("min_profit_threshold")
                    )
                    
                    # Convert each path to an opportunity
                    for path_data in arbitrage_paths:
                        opportunity = await self._convert_to_opportunity(
                            path_data, 
                            market_condition
                        )
                        all_opportunities.append(opportunity)
                
                except Exception as e:
                    logger.error(f"Error finding paths for token {token_address}: {e}")
            
            # Sort by profit and limit results
            sorted_opportunities = sorted(
                all_opportunities,
                key=lambda x: x.expected_profit,
                reverse=True
            )
            
            result = sorted_opportunities[:max_results]
            logger.info(f"Found {len(result)} arbitrage opportunities with PathFinder")
            return result
            
        except Exception as e:
            logger.error(f"Error detecting opportunities with PathFinder: {e}")
            return []
    
    def _calculate_base_amount(self, market_condition: MarketCondition) -> int:
        """Calculate base amount for arbitrage based on market conditions."""
        # Default base amount (1 ETH in wei)
        base_amount = 10**18
        
        # Adjust based on gas price
        gas_price_factor = 1.0
        if market_condition.gas_price_gwei < 30:
            gas_price_factor = 0.8  # Lower amount for low gas
        elif market_condition.gas_price_gwei > 100:
            gas_price_factor = 2.0  # Higher amount for high gas
        
        # Adjust based on congestion
        congestion_factor = 1.0 + market_condition.network_congestion
        
        # Calculate final amount
        adjusted_amount = int(base_amount * gas_price_factor * congestion_factor)
        
        # Ensure amount is at least 0.5 ETH and at most 5 ETH
        min_amount = 5 * 10**17  # 0.5 ETH
        max_amount = 5 * 10**18  # 5 ETH
        
        return max(min_amount, min(adjusted_amount, max_amount))
    
    async def _convert_to_opportunity(
        self,
        path_data: Dict[str, Any],
        market_condition: MarketCondition
    ) -> ArbitrageOpportunity:
        """Convert PathFinder result to ArbitrageOpportunity."""
        # Extract data from path_data
        path_id = path_data.get("id", str(uuid.uuid4()))
        input_token = path_data.get("input_token", "")
        output_token = path_data.get("output_token", "")
        amount_in = path_data.get("amount_in", 0)
        expected_output = path_data.get("expected_output", 0)
        profit = path_data.get("profit", 0)
        profit_margin = path_data.get("profit_margin", 0)
        gas_estimate_value = path_data.get("gas_estimate", 500000)
        route_data = path_data.get("route", [])
        
        # Create route steps
        steps = []
        for hop in route_data:
            # Create route step
            step = RouteStep(
                dex_id=hop.get("dex", "unknown"),
                token_in_address=hop.get("token_in", ""),
                token_out_address=hop.get("token_out", ""),
                pool_address=hop.get("pool_address"),
                pool_fee=hop.get("fee"),
                pool_type=hop.get("pool_type")
            )
            steps.append(step)
        
        # Create route
        route = ArbitrageRoute(
            steps=steps,
            input_token_address=input_token,
            output_token_address=output_token
        )
        
        # Get token symbols
        input_token_symbol = self._get_token_symbol(input_token)
        output_token_symbol = self._get_token_symbol(output_token)
        
        # Calculate USD values
        eth_price_usd = market_condition.eth_price_usd or 3000.0
        
        if amount_in > 0:
            input_amount_eth = amount_in / 10**18
            input_amount_usd = input_amount_eth * eth_price_usd
            
            profit_eth = profit / 10**18
            profit_usd = profit_eth * eth_price_usd
        else:
            input_amount_usd = None
            profit_usd = None
        
        # Create gas estimate
        gas_price = int(market_condition.gas_price_gwei * 1e9)  # Convert Gwei to wei
        gas_estimate = GasEstimate(
            gas_limit=gas_estimate_value,
            gas_price=gas_price,
            total_cost_wei=gas_estimate_value * gas_price
        )
        
        # Calculate confidence score based on market conditions
        confidence_score = self._calculate_confidence_score(
            profit_margin=profit_margin,
            market_condition=market_condition,
            input_token=input_token
        )
        
        # Create opportunity
        opportunity = ArbitrageOpportunity(
            id=path_id,
            strategy_type=StrategyType.CROSS_DEX,
            status=OpportunityStatus.DISCOVERED,
            route=route,
            input_amount=amount_in,
            expected_output=expected_output,
            expected_profit=profit,
            gas_estimate=gas_estimate,
            profit_margin=profit_margin,
            input_token_symbol=input_token_symbol,
            output_token_symbol=output_token_symbol,
            input_amount_usd=input_amount_usd,
            expected_profit_usd=profit_usd,
            confidence_score=confidence_score,
            source_component="path_finder"
        )
        
        return opportunity
    
    def _calculate_confidence_score(
        self,
        profit_margin: float,
        market_condition: MarketCondition,
        input_token: str
    ) -> float:
        """Calculate confidence score for opportunity based on market conditions."""
        # Base confidence based on profit margin
        # Scale from 0-1 with 0.05 (5%) margin being 1.0 confidence
        profit_confidence = min(1.0, profit_margin / 0.05) * 0.5
        
        # Adjust for network congestion (lower confidence in congested network)
        congestion_factor = 1.0 - market_condition.network_congestion * 0.5
        
        # Adjust for volatility (lower confidence in high volatility)
        volatility_factor = 1.0 - market_condition.volatility_index * 0.7
        
        # Adjust for token liquidity
        liquidity_factor = 1.0
        token_lower = input_token.lower()
        if token_lower in market_condition.liquidity_levels:
            liquidity_factor = 0.3 + 0.7 * market_condition.liquidity_levels[token_lower]
        
        # Calculate final confidence
        # Profit is 50%, market conditions are 50% of overall confidence
        market_confidence = (congestion_factor * 0.3 + 
                            volatility_factor * 0.3 + 
                            liquidity_factor * 0.4) * 0.5
        
        final_confidence = profit_confidence + market_confidence
        
        return max(0.0, min(1.0, final_confidence))
    
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


class PathFinderValidator(OpportunityValidator):
    """
    Adapter that uses PathFinder's simulation to validate arbitrage opportunities.
    """
    
    def __init__(
        self,
        path_finder: PathFinder,
        web3_manager: Any,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the validator.
        
        Args:
            path_finder: Existing PathFinder instance
            web3_manager: Web3Manager instance for blockchain interactions
            config: Configuration dictionary
        """
        self.path_finder = path_finder
        self.web3_manager = web3_manager
        self.config = config or {}
        
        # Minimum profit threshold in ETH
        self.min_profit_threshold = self.config.get("min_profit_threshold_eth", 0.001)
        
        logger.info("PathFinderValidator initialized")
    
    async def validate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        market_condition: MarketCondition,
        **kwargs
    ) -> ArbitrageOpportunity:
        """
        Validate an arbitrage opportunity.
        
        Args:
            opportunity: Opportunity to validate
            market_condition: Current market conditions
            **kwargs: Additional validator-specific parameters
            
        Returns:
            Updated opportunity with validation results
        """
        logger.info(f"Validating opportunity {opportunity.id}")
        
        try:
            # Convert to format expected by PathFinder
            path_data = self._convert_to_path_data(opportunity)
            
            # Simulate execution using PathFinder
            simulation_result = await self.path_finder.simulate_execution(path_data)
            
            # Check if simulation was successful
            if not simulation_result.get("success", False):
                logger.warning(f"Simulation failed for opportunity {opportunity.id}")
                opportunity.status = OpportunityStatus.REJECTED
                return opportunity
            
            # Update profit based on simulation
            simulated_profit = simulation_result.get("profit_realized", 0)
            
            # If simulated profit is significantly less than expected, reject
            profit_deviation = abs(simulated_profit - opportunity.expected_profit) / max(1, opportunity.expected_profit)
            if profit_deviation > 0.1:  # More than 10% deviation
                logger.warning(f"Profit deviation too high for opportunity {opportunity.id}: {profit_deviation:.2%}")
                opportunity.status = OpportunityStatus.REJECTED
                return opportunity
            
            # Update gas estimate based on simulation
            gas_used = simulation_result.get("gas_used", opportunity.gas_estimate.gas_limit)
            opportunity.gas_estimate.gas_limit = gas_used
            opportunity.gas_estimate.total_cost_wei = gas_used * opportunity.gas_estimate.gas_price
            
            # Check if profit covers gas cost with sufficient margin
            profit_wei = opportunity.expected_profit
            gas_cost_wei = opportunity.gas_estimate.total_cost_wei
            
            if profit_wei <= gas_cost_wei * 1.2:  # Require 20% margin over gas cost
                logger.warning(f"Insufficient profit margin over gas cost for opportunity {opportunity.id}")
                opportunity.status = OpportunityStatus.REJECTED
                return opportunity
            
            # Check absolute minimum profit threshold
            min_profit_wei = int(self.min_profit_threshold * 10**18)
            if profit_wei < min_profit_wei:
                logger.warning(f"Profit below threshold for opportunity {opportunity.id}")
                opportunity.status = OpportunityStatus.REJECTED
                return opportunity
            
            # Mark as validated
            opportunity.status = OpportunityStatus.VALIDATED
            
            # Add any state changes to metadata
            opportunity.metadata["state_changes"] = simulation_result.get("state_changes", [])
            
            logger.info(f"Successfully validated opportunity {opportunity.id}")
            return opportunity
            
        except Exception as e:
            logger.error(f"Error validating opportunity {opportunity.id}: {e}")
            opportunity.status = OpportunityStatus.REJECTED
            return opportunity
    
    def _convert_to_path_data(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Convert ArbitrageOpportunity to format expected by PathFinder."""
        # Create path data dictionary
        path_data = {
            "id": opportunity.id,
            "input_token": opportunity.route.input_token_address,
            "output_token": opportunity.route.output_token_address,
            "amount_in": opportunity.input_amount,
            "expected_output": opportunity.expected_output,
            "profit": opportunity.expected_profit,
            "profit_margin": opportunity.profit_margin,
            "gas_estimate": opportunity.gas_estimate.gas_limit,
            "route": []
        }
        
        # Convert route steps
        for step in opportunity.route.steps:
            path_data["route"].append({
                "dex": step.dex_id,
                "token0": step.token_in_address,
                "token1": step.token_out_address,
                "pool_address": step.pool_address,
                "fee": step.pool_fee,
                "pool_type": step.pool_type
            })
        
        return path_data


async def create_path_finder_detector(
    path_finder: Optional[PathFinder] = None,
    dex_manager: Optional[Any] = None,
    web3_manager: Optional[Any] = None,
    config: Dict[str, Any] = None
) -> PathFinderDetector:
    """
    Create and initialize a path finder detector.
    
    Args:
        path_finder: Existing PathFinder instance, or None to create new
        dex_manager: DexManager instance for DEX interactions
        web3_manager: Web3Manager instance for blockchain interactions
        config: Configuration dictionary
        
    Returns:
        Initialized path finder detector
    """
    from ...path_finder import create_path_finder
    
    # Create path finder if not provided
    if path_finder is None:
        if dex_manager is None:
            raise ValueError("Either path_finder or dex_manager must be provided")
        
        path_finder = await create_path_finder(
            dex_manager=dex_manager,
            web3_manager=web3_manager,
            config=config
        )
    
    # Create detector
    detector = PathFinderDetector(
        path_finder=path_finder,
        web3_manager=web3_manager,
        config=config
    )
    
    return detector


async def create_path_finder_validator(
    path_finder: Optional[PathFinder] = None,
    dex_manager: Optional[Any] = None,
    web3_manager: Optional[Any] = None,
    config: Dict[str, Any] = None
) -> PathFinderValidator:
    """
    Create and initialize a path finder validator.
    
    Args:
        path_finder: Existing PathFinder instance, or None to create new
        dex_manager: DexManager instance for DEX interactions
        web3_manager: Web3Manager instance for blockchain interactions
        config: Configuration dictionary
        
    Returns:
        Initialized path finder validator
    """
    from ...path_finder import create_path_finder
    
    # Create path finder if not provided
    if path_finder is None:
        if dex_manager is None:
            raise ValueError("Either path_finder or dex_manager must be provided")
        
        path_finder = await create_path_finder(
            dex_manager=dex_manager,
            web3_manager=web3_manager,
            config=config
        )
    
    # Create validator
    validator = PathFinderValidator(
        path_finder=path_finder,
        web3_manager=web3_manager,
        config=config
    )
    
    return validator