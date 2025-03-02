"""
Basic Arbitrage Validator

This module contains the implementation of the BasicValidator,
which validates arbitrage opportunities by checking for various conditions
like slippage, price impact, gas costs, and liquidity.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple, cast

from ....dex.interfaces import DEX, PriceSource
from ...interfaces import (
    OpportunityValidator,
    MarketDataProvider
)
from ...models import (
    ArbitrageOpportunity,
    TokenPair,
    MarketCondition,
    OpportunityStatus
)

logger = logging.getLogger(__name__)


class BasicValidator(OpportunityValidator):
    """
    Basic validator for arbitrage opportunities.
    
    This validator performs several checks on opportunities to ensure they are
    profitable and safe to execute, including slippage protection, liquidity
    verification, and price impact assessment.
    """
    
    def __init__(
        self,
        dexes: Dict[str, DEX],
        config: Dict[str, Any] = None
    ):
        """
        Initialize the basic validator.
        
        Args:
            dexes: Dictionary mapping DEX IDs to DEX instances
            config: Configuration dictionary
        """
        self.dexes = dexes
        self.config = config or {}
        
        # Configuration
        self.max_slippage = Decimal(self.config.get("max_slippage", "0.5"))  # 0.5%
        self.min_liquidity_usd = Decimal(self.config.get("min_liquidity_usd", "10000"))  # $10,000
        self.max_price_impact = Decimal(self.config.get("max_price_impact", "1.0"))  # 1%
        self.max_gas_percentage = Decimal(self.config.get("max_gas_percentage", "50.0"))  # 50% of profit
        self.gas_price_buffer = Decimal(self.config.get("gas_price_buffer", "20.0"))  # 20% buffer on gas price
        self.price_verification_sources = int(self.config.get("price_verification_sources", 1))  # Min number of sources
        self.max_price_age_seconds = int(self.config.get("max_price_age_seconds", 15))  # 15 seconds max age
        
        # Cache for token pairs with timestamps
        self._price_cache: Dict[str, Tuple[Decimal, float]] = {}
        self._cache_ttl = float(self.config.get("cache_ttl_seconds", 5.0))
        
        # Locks
        self._cache_lock = asyncio.Lock()
        
        logger.info("BasicValidator initialized")
    
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
            market_condition: Current market condition
            **kwargs: Additional validation parameters
            
        Returns:
            Updated opportunity with validation results
        """
        logger.info(f"Validating opportunity {opportunity.id}")
        
        # Make a copy of the opportunity to update
        validated_opportunity = opportunity
        
        # Start with validated status, set to rejected if any checks fail
        validated_opportunity.status = OpportunityStatus.VALIDATED
        
        # Extract parameters from kwargs or use defaults
        max_slippage = Decimal(kwargs.get("max_slippage", self.max_slippage))
        min_liquidity_usd = Decimal(kwargs.get("min_liquidity_usd", self.min_liquidity_usd))
        max_price_impact = Decimal(kwargs.get("max_price_impact", self.max_price_impact))
        
        # Perform all validation checks
        checks = [
            self._validate_slippage(validated_opportunity, max_slippage),
            self._validate_liquidity(validated_opportunity, min_liquidity_usd),
            self._validate_price_impact(validated_opportunity, max_price_impact),
            self._validate_gas_costs(validated_opportunity, market_condition),
            self._validate_token_safety(validated_opportunity),
            self._validate_price_consistency(validated_opportunity)
        ]
        
        # Run all checks in parallel
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Validation check {i} failed with error: {result}")
                validated_opportunity.status = OpportunityStatus.REJECTED
                validated_opportunity.metadata["validation_error"] = str(result)
                return validated_opportunity
            
            if not result:
                logger.info(f"Validation check {i} failed")
                validated_opportunity.status = OpportunityStatus.REJECTED
                return validated_opportunity
        
        # Additional validation: simulation
        if self.config.get("enable_simulation", True):
            simulation_result = await self._simulate_execution(validated_opportunity, market_condition)
            if not simulation_result:
                logger.info(f"Execution simulation failed for opportunity {opportunity.id}")
                validated_opportunity.status = OpportunityStatus.REJECTED
                return validated_opportunity
            
            # Update expected profit from simulation
            validated_opportunity.expected_profit = simulation_result
            validated_opportunity.expected_profit_after_gas = simulation_result - (
                validated_opportunity.gas_estimate * (validated_opportunity.gas_price + validated_opportunity.priority_fee)
            )
        
        # All checks passed
        logger.info(f"Opportunity {opportunity.id} successfully validated")
        
        # Update metadata
        validated_opportunity.metadata["validation_timestamp"] = int(time.time())
        validated_opportunity.metadata["validator"] = "BasicValidator"
        
        return validated_opportunity
    
    async def _validate_slippage(
        self,
        opportunity: ArbitrageOpportunity,
        max_slippage: Decimal
    ) -> bool:
        """
        Validate that expected slippage is within limits.
        
        Args:
            opportunity: Opportunity to validate
            max_slippage: Maximum allowed slippage percentage
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Extract slippage estimation from opportunity metadata or calculate it
            estimated_slippage = Decimal(str(opportunity.metadata.get("estimated_slippage", "0")))
            
            # If no slippage estimate is provided, estimate based on liquidity and trade size
            if estimated_slippage == 0:
                estimated_slippage = await self._estimate_slippage(opportunity)
            
            # Check against threshold
            if estimated_slippage > max_slippage:
                logger.info(
                    f"Opportunity {opportunity.id} rejected due to excessive slippage: "
                    f"{estimated_slippage}% > {max_slippage}%"
                )
                opportunity.metadata["rejection_reason"] = f"Excessive slippage: {estimated_slippage}%"
                return False
            
            # Update metadata with slippage estimation
            opportunity.metadata["validated_slippage"] = float(estimated_slippage)
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating slippage: {e}")
            opportunity.metadata["rejection_reason"] = f"Slippage validation error: {e}"
            return False
    
    async def _validate_liquidity(
        self,
        opportunity: ArbitrageOpportunity,
        min_liquidity_usd: Decimal
    ) -> bool:
        """
        Validate that pool liquidity is sufficient.
        
        Args:
            opportunity: Opportunity to validate
            min_liquidity_usd: Minimum required liquidity in USD
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Check each step in the route for liquidity
            for i, step in enumerate(opportunity.route.steps):
                # Try to get the DEX
                dex_id = step.dex.id
                if dex_id not in self.dexes:
                    logger.warning(f"DEX {dex_id} not found in available DEXes")
                    opportunity.metadata["rejection_reason"] = f"DEX {dex_id} not available"
                    return False
                
                dex = self.dexes[dex_id]
                
                # Skip if not a PriceSource
                if not isinstance(dex, PriceSource):
                    continue
                
                price_source = cast(PriceSource, dex)
                
                # Get token pair liquidity
                input_token = step.input_token.address
                output_token = step.output_token.address
                
                pair_liquidity = await self._get_pair_liquidity(
                    price_source=price_source,
                    token0=input_token,
                    token1=output_token
                )
                
                if pair_liquidity < min_liquidity_usd:
                    logger.info(
                        f"Opportunity {opportunity.id} rejected due to insufficient liquidity in step {i}: "
                        f"${pair_liquidity} < ${min_liquidity_usd}"
                    )
                    opportunity.metadata["rejection_reason"] = f"Insufficient liquidity: ${pair_liquidity} in step {i}"
                    return False
                
                # Update metadata with liquidity information
                if "step_liquidity" not in opportunity.metadata:
                    opportunity.metadata["step_liquidity"] = []
                
                opportunity.metadata["step_liquidity"].append(float(pair_liquidity))
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating liquidity: {e}")
            opportunity.metadata["rejection_reason"] = f"Liquidity validation error: {e}"
            return False
    
    async def _validate_price_impact(
        self,
        opportunity: ArbitrageOpportunity,
        max_price_impact: Decimal
    ) -> bool:
        """
        Validate that price impact is within limits.
        
        Args:
            opportunity: Opportunity to validate
            max_price_impact: Maximum allowed price impact percentage
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Extract price impact estimation from opportunity metadata or calculate it
            estimated_impact = Decimal(str(opportunity.metadata.get("estimated_price_impact", "0")))
            
            # If no price impact estimate is provided, estimate based on trade size and liquidity
            if estimated_impact == 0:
                estimated_impact = await self._estimate_price_impact(opportunity)
            
            # Check against threshold
            if estimated_impact > max_price_impact:
                logger.info(
                    f"Opportunity {opportunity.id} rejected due to excessive price impact: "
                    f"{estimated_impact}% > {max_price_impact}%"
                )
                opportunity.metadata["rejection_reason"] = f"Excessive price impact: {estimated_impact}%"
                return False
            
            # Update metadata with price impact estimation
            opportunity.metadata["validated_price_impact"] = float(estimated_impact)
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating price impact: {e}")
            opportunity.metadata["rejection_reason"] = f"Price impact validation error: {e}"
            return False
    
    async def _validate_gas_costs(
        self,
        opportunity: ArbitrageOpportunity,
        market_condition: MarketCondition
    ) -> bool:
        """
        Validate that gas costs are reasonable.
        
        Args:
            opportunity: Opportunity to validate
            market_condition: Current market condition
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Get current gas price from market condition or use opportunity's estimate
            current_gas_price = (
                market_condition.gas_price if market_condition.gas_price else opportunity.gas_price
            )
            
            current_priority_fee = (
                market_condition.priority_fee if market_condition.priority_fee else opportunity.priority_fee
            )
            
            # Add buffer to gas price to account for potential increases
            buffered_gas_price = current_gas_price * (Decimal("100") + self.gas_price_buffer) / Decimal("100")
            
            # Calculate gas cost
            gas_cost = opportunity.gas_estimate * (buffered_gas_price + current_priority_fee)
            
            # Calculate gas cost as percentage of expected profit
            if opportunity.expected_profit > 0:
                gas_percentage = (gas_cost / opportunity.expected_profit) * Decimal("100")
            else:
                gas_percentage = Decimal("100")
            
            # Check if gas cost is reasonable
            if gas_percentage > self.max_gas_percentage:
                logger.info(
                    f"Opportunity {opportunity.id} rejected due to excessive gas costs: "
                    f"{gas_percentage}% > {self.max_gas_percentage}% of profit"
                )
                opportunity.metadata["rejection_reason"] = f"Excessive gas costs: {gas_percentage}% of profit"
                return False
            
            # Update gas costs in opportunity
            opportunity.gas_price = buffered_gas_price
            opportunity.priority_fee = current_priority_fee
            opportunity.expected_profit_after_gas = opportunity.expected_profit - gas_cost
            
            # Update metadata
            opportunity.metadata["validated_gas_percentage"] = float(gas_percentage)
            opportunity.metadata["validated_gas_cost"] = float(gas_cost)
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating gas costs: {e}")
            opportunity.metadata["rejection_reason"] = f"Gas cost validation error: {e}"
            return False
    
    async def _validate_token_safety(
        self,
        opportunity: ArbitrageOpportunity
    ) -> bool:
        """
        Validate that tokens in the opportunity are safe to trade.
        
        Args:
            opportunity: Opportunity to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # In a real implementation, this would check token contracts for:
            # - Honeypot detection
            # - Transfer fee detection
            # - Rebasing tokens
            # - Blacklisted tokens
            # - Other problematic token implementations
            
            # For now, assume all tokens are safe unless specifically blacklisted
            token_blacklist = self.config.get("token_blacklist", [])
            
            # Check input and output tokens in each step
            for i, step in enumerate(opportunity.route.steps):
                input_token = step.input_token.address.lower()
                output_token = step.output_token.address.lower()
                
                if input_token in token_blacklist:
                    logger.info(f"Opportunity {opportunity.id} rejected due to blacklisted token: {input_token}")
                    opportunity.metadata["rejection_reason"] = f"Blacklisted token: {input_token}"
                    return False
                
                if output_token in token_blacklist:
                    logger.info(f"Opportunity {opportunity.id} rejected due to blacklisted token: {output_token}")
                    opportunity.metadata["rejection_reason"] = f"Blacklisted token: {output_token}"
                    return False
            
            # Add token safety check to metadata
            opportunity.metadata["token_safety_validated"] = True
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating token safety: {e}")
            opportunity.metadata["rejection_reason"] = f"Token safety validation error: {e}"
            return False
    
    async def _validate_price_consistency(
        self,
        opportunity: ArbitrageOpportunity
    ) -> bool:
        """
        Validate that prices are consistent across multiple sources.
        
        Args:
            opportunity: Opportunity to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Skip if only one verification source required
            if self.price_verification_sources <= 1:
                return True
            
            # In a real implementation, this would:
            # - Check prices from multiple sources (oracles, other DEXes)
            # - Verify that prices are within an acceptable range
            # - Check for recently manipulated prices
            
            # For now, assume prices are consistent unless marked otherwise
            price_risk = opportunity.metadata.get("price_manipulation_risk", 0.0)
            
            if price_risk > 0.5:  # If price manipulation risk is over 50%
                logger.info(f"Opportunity {opportunity.id} rejected due to price manipulation risk: {price_risk}")
                opportunity.metadata["rejection_reason"] = f"Price manipulation risk: {price_risk}"
                return False
            
            # Check price age
            price_timestamp = opportunity.metadata.get("price_timestamp", 0)
            current_time = int(time.time())
            
            if current_time - price_timestamp > self.max_price_age_seconds:
                logger.info(f"Opportunity {opportunity.id} rejected due to outdated prices")
                opportunity.metadata["rejection_reason"] = "Outdated prices"
                return False
            
            # Add price consistency check to metadata
            opportunity.metadata["price_consistency_validated"] = True
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating price consistency: {e}")
            opportunity.metadata["rejection_reason"] = f"Price consistency validation error: {e}"
            return False
    
    async def _simulate_execution(
        self,
        opportunity: ArbitrageOpportunity,
        market_condition: MarketCondition
    ) -> Optional[int]:
        """
        Simulate execution of the opportunity to validate profitability.
        
        Args:
            opportunity: Opportunity to validate
            market_condition: Current market condition
            
        Returns:
            Expected profit in wei if simulation passes, None otherwise
        """
        try:
            # In a real implementation, this would:
            # - Use a forked blockchain or simulation environment
            # - Simulate the actual transaction execution
            # - Return the expected profit based on simulation
            
            # For now, simulate by applying expected slippage and fees
            estimated_slippage = Decimal(str(opportunity.metadata.get("validated_slippage", "0.5"))) / Decimal("100")
            
            # Apply slippage to expected profit
            simulated_profit = opportunity.expected_profit * (Decimal("1") - estimated_slippage)
            
            # Apply DEX fees if not already accounted for
            dex_fee_percentage = Decimal(str(opportunity.metadata.get("dex_fee_percentage", "0.3"))) / Decimal("100")
            simulated_profit = simulated_profit * (Decimal("1") - dex_fee_percentage)
            
            # Convert to integer (wei)
            simulated_profit_wei = int(simulated_profit)
            
            # Update metadata with simulation results
            opportunity.metadata["simulated_profit"] = simulated_profit_wei
            opportunity.metadata["simulation_timestamp"] = int(time.time())
            
            return simulated_profit_wei
            
        except Exception as e:
            logger.error(f"Error simulating execution: {e}")
            opportunity.metadata["rejection_reason"] = f"Simulation error: {e}"
            return None
    
    async def _estimate_slippage(
        self,
        opportunity: ArbitrageOpportunity
    ) -> Decimal:
        """
        Estimate slippage for an opportunity.
        
        Args:
            opportunity: Opportunity to estimate slippage for
            
        Returns:
            Estimated slippage percentage
        """
        # This is a simplified slippage estimation
        # In a real implementation, this would use a more sophisticated model
        # based on order book depth, liquidity, and historical data
        
        # For now, estimate based on trade size and strategy type
        slippage_base = Decimal("0.1")  # 0.1% base slippage
        
        # Adjust based on strategy type
        if opportunity.strategy_type == "TRIANGULAR":
            # Triangular arbitrage typically has higher slippage
            slippage_base *= Decimal("1.5")
        
        # Adjust based on number of steps
        slippage_base *= Decimal(len(opportunity.route.steps))
        
        # Adjust based on trade size
        # Larger trades have higher slippage
        input_amount = Decimal(opportunity.route.input_token.amount)
        
        # Simplified model: slippage increases with square root of trade size
        # Normalize to a standard trade size of 1 ETH (10^18 wei)
        normalized_size = (input_amount / Decimal(10**18)) ** Decimal("0.5")
        size_multiplier = max(normalized_size, Decimal("1"))
        
        estimated_slippage = slippage_base * size_multiplier
        
        # Cap at a reasonable maximum
        return min(estimated_slippage, Decimal("2.0"))
    
    async def _estimate_price_impact(
        self,
        opportunity: ArbitrageOpportunity
    ) -> Decimal:
        """
        Estimate price impact for an opportunity.
        
        Args:
            opportunity: Opportunity to estimate price impact for
            
        Returns:
            Estimated price impact percentage
        """
        # Simplified price impact estimation
        # In a real implementation, this would use AMM models,
        # order book depth, and other liquidity metrics
        
        # For now, use a simple model similar to slippage
        impact_base = Decimal("0.05")  # 0.05% base impact
        
        # Adjust based on strategy type
        if opportunity.strategy_type == "CROSS_DEX":
            # Cross-DEX arbitrage typically has lower price impact
            impact_base *= Decimal("0.8")
        
        # Adjust based on number of steps
        impact_base *= Decimal(len(opportunity.route.steps))
        
        # Adjust based on trade size
        input_amount = Decimal(opportunity.route.input_token.amount)
        
        # Simplified model: impact increases with trade size
        normalized_size = (input_amount / Decimal(10**18)) ** Decimal("0.7")
        size_multiplier = max(normalized_size, Decimal("1"))
        
        estimated_impact = impact_base * size_multiplier
        
        # Cap at a reasonable maximum
        return min(estimated_impact, Decimal("1.5"))
    
    async def _get_pair_liquidity(
        self,
        price_source: PriceSource,
        token0: str,
        token1: str
    ) -> Decimal:
        """
        Get liquidity for a token pair.
        
        Args:
            price_source: Price source to get liquidity from
            token0: Address of first token
            token1: Address of second token
            
        Returns:
            Liquidity in USD
        """
        try:
            # Get token pair from price source
            pairs = await price_source.get_token_pairs()
            
            # Find matching pair
            for pair in pairs:
                if (
                    (pair.token0_address.lower() == token0.lower() and pair.token1_address.lower() == token1.lower()) or
                    (pair.token0_address.lower() == token1.lower() and pair.token1_address.lower() == token0.lower())
                ):
                    # Return liquidity in USD
                    if pair.liquidity_usd:
                        return pair.liquidity_usd
                    else:
                        # If liquidity not provided, use a default value
                        # In a real implementation, this would calculate liquidity
                        return Decimal("10000")
            
            # If pair not found, return a low liquidity value
            return Decimal("0")
            
        except Exception as e:
            logger.error(f"Error getting pair liquidity: {e}")
            # Return a low liquidity value on error
            return Decimal("0")


async def create_basic_validator(
    dexes: Dict[str, DEX],
    config: Dict[str, Any] = None
) -> BasicValidator:
    """
    Factory function to create a basic validator.
    
    Args:
        dexes: Dictionary mapping DEX IDs to DEX instances
        config: Configuration dictionary
        
    Returns:
        Initialized basic validator
    """
    return BasicValidator(dexes=dexes, config=config)