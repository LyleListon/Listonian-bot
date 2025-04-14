"""Profit calculator for arbitrage opportunities."""

import logging
from typing import Dict, Any, List, Optional

from arbitrage_bot.common.utils.helpers import calculate_profit, calculate_roi

logger = logging.getLogger(__name__)


class ProfitCalculator:
    """Calculates profit for arbitrage opportunities."""
    
    def __init__(
        self,
        min_profit_threshold: float = 0.5,
        gas_price_multiplier: float = 1.1,
    ):
        """Initialize the profit calculator.
        
        Args:
            min_profit_threshold: Minimum profit percentage to consider an opportunity.
            gas_price_multiplier: Multiplier for gas price estimation.
        """
        self.min_profit_threshold = min_profit_threshold
        self.gas_price_multiplier = gas_price_multiplier
    
    def calculate_expected_profit(
        self,
        path: List[Dict[str, Any]],
        input_amount: float,
        token_prices: Dict[str, float],
    ) -> Dict[str, Any]:
        """Calculate expected profit for a path.
        
        Args:
            path: The arbitrage path.
            input_amount: The input amount.
            token_prices: Dictionary mapping tokens to their USD prices.
            
        Returns:
            Dictionary with profit information.
        """
        if not path:
            return {
                "expected_profit_percentage": 0.0,
                "expected_profit_usd": 0.0,
                "estimated_gas_cost_usd": 0.0,
                "net_profit_usd": 0.0,
                "profitable": False,
            }
        
        # Calculate output amount
        output_amount = input_amount
        for edge in path:
            price = edge.get("price", 0.0)
            output_amount *= price
        
        # Get input and output tokens
        input_token = path[0].get("from_token")
        output_token = path[-1].get("to_token")
        
        # Calculate profit percentage
        profit_percentage = ((output_amount / input_amount) - 1.0) * 100.0
        
        # Calculate USD values
        input_price_usd = token_prices.get(input_token, 0.0)
        output_price_usd = token_prices.get(output_token, 0.0)
        
        input_amount_usd = input_amount * input_price_usd
        output_amount_usd = output_amount * output_price_usd
        
        # Estimate gas cost
        estimated_gas_cost_usd = self._estimate_gas_cost(path, token_prices)
        
        # Calculate net profit
        expected_profit_usd = output_amount_usd - input_amount_usd
        net_profit_usd = expected_profit_usd - estimated_gas_cost_usd
        
        # Check if profitable
        profitable = (
            profit_percentage >= self.min_profit_threshold
            and net_profit_usd > 0
        )
        
        return {
            "expected_profit_percentage": profit_percentage,
            "expected_profit_usd": expected_profit_usd,
            "estimated_gas_cost_usd": estimated_gas_cost_usd,
            "net_profit_usd": net_profit_usd,
            "profitable": profitable,
        }
    
    def _estimate_gas_cost(
        self, path: List[Dict[str, Any]], token_prices: Dict[str, float]
    ) -> float:
        """Estimate gas cost for a path.
        
        Args:
            path: The arbitrage path.
            token_prices: Dictionary mapping tokens to their USD prices.
            
        Returns:
            Estimated gas cost in USD.
        """
        # Base gas cost for a swap
        base_swap_gas = 100000  # 100k gas units
        
        # Additional gas for each hop
        hop_gas = 50000  # 50k gas units
        
        # Gas for flash loan (if needed)
        flash_loan_gas = 200000  # 200k gas units
        
        # Calculate total gas units
        total_gas = base_swap_gas + (len(path) * hop_gas) + flash_loan_gas
        
        # Estimate gas price (in gwei)
        gas_price_gwei = 20.0  # Default gas price in gwei
        
        # Apply gas price multiplier
        gas_price_gwei *= self.gas_price_multiplier
        
        # Convert gas price to ETH
        gas_price_eth = gas_price_gwei * 1e-9
        
        # Calculate gas cost in ETH
        gas_cost_eth = total_gas * gas_price_eth
        
        # Convert to USD
        eth_price_usd = token_prices.get("ETH", 0.0)
        gas_cost_usd = gas_cost_eth * eth_price_usd
        
        return gas_cost_usd
    
    def calculate_flash_loan_fee(
        self, input_amount: float, token: str, token_prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate flash loan fee.
        
        Args:
            input_amount: The input amount.
            token: The token to borrow.
            token_prices: Dictionary mapping tokens to their USD prices.
            
        Returns:
            Dictionary with flash loan fee information.
        """
        # Default fee percentage for Aave
        fee_percentage = 0.09  # 0.09%
        
        # Calculate fee amount
        fee_amount = input_amount * (fee_percentage / 100.0)
        
        # Calculate fee in USD
        token_price_usd = token_prices.get(token, 0.0)
        fee_usd = fee_amount * token_price_usd
        
        return {
            "fee_percentage": fee_percentage,
            "fee_amount": fee_amount,
            "fee_usd": fee_usd,
            "token": token,
        }
    
    def evaluate_opportunity(
        self,
        path: List[Dict[str, Any]],
        input_amount: float,
        token_prices: Dict[str, float],
        use_flash_loan: bool = True,
    ) -> Dict[str, Any]:
        """Evaluate an arbitrage opportunity.
        
        Args:
            path: The arbitrage path.
            input_amount: The input amount.
            token_prices: Dictionary mapping tokens to their USD prices.
            use_flash_loan: Whether to use a flash loan.
            
        Returns:
            Dictionary with opportunity evaluation.
        """
        # Calculate expected profit
        profit_info = self.calculate_expected_profit(path, input_amount, token_prices)
        
        # Get input token
        input_token = path[0].get("from_token") if path else None
        
        # Calculate flash loan fee if using flash loan
        flash_loan_info = None
        if use_flash_loan and input_token:
            flash_loan_info = self.calculate_flash_loan_fee(
                input_amount, input_token, token_prices
            )
            
            # Adjust net profit with flash loan fee
            profit_info["net_profit_usd"] -= flash_loan_info.get("fee_usd", 0.0)
            profit_info["profitable"] = (
                profit_info["expected_profit_percentage"] >= self.min_profit_threshold
                and profit_info["net_profit_usd"] > 0
            )
        
        # Create opportunity evaluation
        opportunity = {
            "path": path,
            "input_amount": input_amount,
            "input_token": input_token,
            "expected_profit_percentage": profit_info.get("expected_profit_percentage", 0.0),
            "expected_profit_usd": profit_info.get("expected_profit_usd", 0.0),
            "estimated_gas_cost_usd": profit_info.get("estimated_gas_cost_usd", 0.0),
            "net_profit_usd": profit_info.get("net_profit_usd", 0.0),
            "profitable": profit_info.get("profitable", False),
            "use_flash_loan": use_flash_loan,
            "flash_loan_info": flash_loan_info,
        }
        
        return opportunity
    
    def rank_opportunities(
        self, opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank arbitrage opportunities by net profit.
        
        Args:
            opportunities: List of opportunity evaluations.
            
        Returns:
            Sorted list of opportunities.
        """
        # Filter profitable opportunities
        profitable_opportunities = [
            opp for opp in opportunities if opp.get("profitable", False)
        ]
        
        # Sort by net profit (descending)
        sorted_opportunities = sorted(
            profitable_opportunities,
            key=lambda x: x.get("net_profit_usd", 0.0),
            reverse=True,
        )
        
        return sorted_opportunities
