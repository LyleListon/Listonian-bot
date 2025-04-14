"""Request models for API endpoints."""

from typing import Dict, List, Any, Optional

from arbitrage_bot.api.models.base_model import BaseModel


class OpportunitiesRequest(BaseModel):
    """Request model for opportunities endpoint."""
    
    __fields__ = ["min_profit", "max_risk", "limit", "offset", "token"]
    
    def __init__(
        self,
        min_profit: float = 0.0,
        max_risk: int = 5,
        limit: int = 10,
        offset: int = 0,
        token: Optional[str] = None,
    ):
        """Initialize opportunities request.
        
        Args:
            min_profit: Minimum profit percentage.
            max_risk: Maximum risk score (1-5).
            limit: Maximum number of opportunities to return.
            offset: Offset for pagination.
            token: Filter by token.
        """
        self.min_profit = min_profit
        self.max_risk = max_risk
        self.limit = limit
        self.offset = offset
        self.token = token


class TradesRequest(BaseModel):
    """Request model for trades endpoint."""
    
    __fields__ = ["status", "limit", "offset"]
    
    def __init__(
        self,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ):
        """Initialize trades request.
        
        Args:
            status: Filter by status.
            limit: Maximum number of trades to return.
            offset: Offset for pagination.
        """
        self.status = status
        self.limit = limit
        self.offset = offset


class ExecuteTradeRequest(BaseModel):
    """Request model for execute trade endpoint."""
    
    __fields__ = ["opportunity_id", "options"]
    
    def __init__(
        self,
        opportunity_id: str = "",
        options: Dict[str, Any] = None,
    ):
        """Initialize execute trade request.
        
        Args:
            opportunity_id: Opportunity ID.
            options: Trade execution options.
        """
        self.opportunity_id = opportunity_id
        self.options = options or {}
