"""Arbitrage engine for finding and evaluating arbitrage opportunities."""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional

from arbitrage_bot.common.events.event_bus import EventBus
from arbitrage_bot.core.arbitrage.path_finder import PathFinder
from arbitrage_bot.core.arbitrage.profit_calculator import ProfitCalculator
from arbitrage_bot.core.arbitrage.risk_analyzer import RiskAnalyzer

logger = logging.getLogger(__name__)


class ArbitrageEngine:
    """Engine for finding and evaluating arbitrage opportunities."""
    
    def __init__(
        self,
        path_finder: PathFinder,
        profit_calculator: ProfitCalculator,
        risk_analyzer: RiskAnalyzer,
        event_bus: EventBus,
        config: Dict[str, Any],
    ):
        """Initialize the arbitrage engine.
        
        Args:
            path_finder: Path finder component.
            profit_calculator: Profit calculator component.
            risk_analyzer: Risk analyzer component.
            event_bus: Event bus for publishing events.
            config: Configuration dictionary.
        """
        self.path_finder = path_finder
        self.profit_calculator = profit_calculator
        self.risk_analyzer = risk_analyzer
        self.event_bus = event_bus
        self.config = config
        
        # Get configuration values
        trading_config = config.get("trading", {})
        self.min_profit_threshold = trading_config.get("min_profit_threshold", 0.5)
        self.max_slippage = trading_config.get("max_slippage", 1.0)
        self.max_trade_amount = trading_config.get("max_trade_amount", 1.0)
        self.min_liquidity = trading_config.get("min_liquidity", 10000)
        self.trading_enabled = trading_config.get("trading_enabled", False)
        
        # Initialize state
        self.market_data = {}
        self.token_prices = {}
        self.token_info = {}
        self.current_opportunities = []
        
        logger.info("Arbitrage engine initialized")
    
    def update_market_data(self, market_data: Dict[str, Any]) -> None:
        """Update market data.
        
        Args:
            market_data: Market data containing pairs information.
        """
        self.market_data = market_data
        self.path_finder.update_graph(market_data)
        logger.debug("Market data updated")
    
    def update_token_prices(self, token_prices: Dict[str, float]) -> None:
        """Update token prices.
        
        Args:
            token_prices: Dictionary mapping tokens to their USD prices.
        """
        self.token_prices = token_prices
        logger.debug("Token prices updated")
    
    def update_token_info(self, token_info: Dict[str, Dict[str, Any]]) -> None:
        """Update token information.
        
        Args:
            token_info: Dictionary mapping tokens to their information.
        """
        self.token_info = token_info
        logger.debug("Token info updated")
    
    def find_opportunities(self) -> List[Dict[str, Any]]:
        """Find arbitrage opportunities.
        
        Returns:
            List of arbitrage opportunities.
        """
        logger.info("Finding arbitrage opportunities")
        start_time = time.time()
        
        # Find arbitrage paths
        all_paths = self.path_finder.find_all_arbitrage_paths(
            min_liquidity=self.min_liquidity
        )
        
        # Evaluate opportunities
        opportunities = []
        
        for token, paths in all_paths.items():
            for path in paths:
                # Skip if path is empty
                if not path:
                    continue
                
                # Calculate input amount based on minimum liquidity
                min_liquidity = min(edge.get("liquidity", 0.0) for edge in path)
                input_amount = min(self.max_trade_amount, min_liquidity * 0.01)
                
                # Skip if input amount is too small
                if input_amount <= 0:
                    continue
                
                # Evaluate opportunity
                opportunity = self.profit_calculator.evaluate_opportunity(
                    path, input_amount, self.token_prices, use_flash_loan=True
                )
                
                # Skip if not profitable
                if not opportunity.get("profitable", False):
                    continue
                
                # Analyze risk
                opportunity = self.risk_analyzer.analyze_opportunity(
                    opportunity, self.token_info
                )
                
                # Skip if risk is not acceptable
                if not opportunity.get("acceptable_risk", False):
                    continue
                
                # Add opportunity ID
                opportunity["id"] = f"opp-{uuid.uuid4()}"
                
                # Add timestamp
                opportunity["timestamp"] = int(time.time())
                
                # Add to opportunities list
                opportunities.append(opportunity)
        
        # Rank opportunities
        ranked_opportunities = self.profit_calculator.rank_opportunities(opportunities)
        
        # Update current opportunities
        self.current_opportunities = ranked_opportunities
        
        # Publish event for each opportunity
        for opportunity in ranked_opportunities:
            self.event_bus.publish_event("opportunity_detected", opportunity)
        
        end_time = time.time()
        logger.info(
            f"Found {len(ranked_opportunities)} arbitrage opportunities "
            f"in {end_time - start_time:.2f} seconds"
        )
        
        return ranked_opportunities
    
    def get_opportunity_by_id(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """Get an opportunity by ID.
        
        Args:
            opportunity_id: The ID of the opportunity.
            
        Returns:
            The opportunity, or None if not found.
        """
        for opportunity in self.current_opportunities:
            if opportunity.get("id") == opportunity_id:
                return opportunity
        
        return None
    
    def prepare_execution_plan(
        self, opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare an execution plan for an opportunity.
        
        Args:
            opportunity: The opportunity to execute.
            
        Returns:
            Execution plan.
        """
        path = opportunity.get("path", [])
        input_amount = opportunity.get("input_amount", 0.0)
        input_token = opportunity.get("input_token")
        use_flash_loan = opportunity.get("use_flash_loan", True)
        
        # Create execution steps
        steps = []
        
        for edge in path:
            from_token = edge.get("from_token")
            to_token = edge.get("to_token")
            dex = edge.get("dex")
            
            step = {
                "dex": dex,
                "action": "swap",
                "input_token": from_token,
                "output_token": to_token,
                "input_amount": input_amount if from_token == input_token else None,
                "min_output_amount": None,  # Will be calculated during execution
            }
            
            steps.append(step)
        
        # Create flash loan plan if needed
        flash_loan = None
        if use_flash_loan:
            flash_loan_info = opportunity.get("flash_loan_info", {})
            flash_loan = {
                "provider": "aave",  # Default provider
                "token": input_token,
                "amount": input_amount,
                "fee": flash_loan_info.get("fee_amount", 0.0),
            }
        
        # Create MEV protection plan
        mev_protection = {
            "provider": "flashbots",  # Default provider
            "bundle_type": "standard",
        }
        
        # Create execution plan
        execution_plan = {
            "opportunity_id": opportunity.get("id"),
            "steps": steps,
            "flash_loan": flash_loan,
            "mev_protection": mev_protection,
            "max_slippage": self.max_slippage,
            "deadline": int(time.time()) + 60,  # 1 minute from now
        }
        
        return execution_plan
