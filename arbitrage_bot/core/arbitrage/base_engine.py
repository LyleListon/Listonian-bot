"""Base class for arbitrage engines."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from arbitrage_bot.common.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class BaseArbitrageEngine(ABC):
    """Base class for arbitrage engines."""
    
    def __init__(self, event_bus: EventBus, config: Dict[str, Any]):
        """Initialize the arbitrage engine.
        
        Args:
            event_bus: Event bus for publishing events.
            config: Configuration dictionary.
        """
        self.event_bus = event_bus
        self.config = config
    
    @abstractmethod
    def update_market_data(self, market_data: Dict[str, Any]) -> None:
        """Update market data.
        
        Args:
            market_data: Market data.
        """
        pass
    
    @abstractmethod
    def update_token_prices(self, token_prices: Dict[str, float]) -> None:
        """Update token prices.
        
        Args:
            token_prices: Token prices.
        """
        pass
    
    @abstractmethod
    def update_token_info(self, token_info: Dict[str, Dict[str, Any]]) -> None:
        """Update token information.
        
        Args:
            token_info: Token information.
        """
        pass
    
    @abstractmethod
    def find_opportunities(self) -> List[Dict[str, Any]]:
        """Find arbitrage opportunities.
        
        Returns:
            List of arbitrage opportunities.
        """
        pass
    
    @abstractmethod
    def get_opportunity_by_id(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """Get an opportunity by ID.
        
        Args:
            opportunity_id: Opportunity ID.
            
        Returns:
            Opportunity, or None if not found.
        """
        pass
    
    @abstractmethod
    def prepare_execution_plan(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare an execution plan for an arbitrage opportunity.
        
        Args:
            opportunity: Arbitrage opportunity.
            
        Returns:
            Execution plan.
        """
        pass
