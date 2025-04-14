"""Response models for API endpoints."""

from typing import Dict, List, Any, Optional, Generic, TypeVar
from datetime import datetime

from arbitrage_bot.api.models.base_model import BaseModel

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """Base API response model."""
    
    __fields__ = ["success", "data", "error", "timestamp"]
    
    def __init__(
        self,
        success: bool = True,
        data: Optional[T] = None,
        error: Optional[str] = None,
    ):
        """Initialize API response.
        
        Args:
            success: Whether the request was successful.
            data: Response data.
            error: Error message if request failed.
        """
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = datetime.utcnow()


class StatusResponse(BaseModel):
    """Status response model."""
    
    __fields__ = ["status", "version", "uptime", "components"]
    
    def __init__(
        self,
        status: str = "ok",
        version: str = "0.1.0",
        uptime: int = 0,
        components: Dict[str, str] = None,
    ):
        """Initialize status response.
        
        Args:
            status: System status.
            version: API version.
            uptime: System uptime in seconds.
            components: Component statuses.
        """
        self.status = status
        self.version = version
        self.uptime = uptime
        self.components = components or {}


class OpportunityResponse(BaseModel):
    """Opportunity response model."""
    
    __fields__ = [
        "id",
        "path",
        "input_token",
        "input_amount",
        "expected_profit_percentage",
        "expected_profit_usd",
        "estimated_gas_cost_usd",
        "net_profit_usd",
        "risk_score",
        "timestamp",
    ]
    
    def __init__(
        self,
        id: str = "",
        path: List[Dict[str, Any]] = None,
        input_token: str = "",
        input_amount: float = 0.0,
        expected_profit_percentage: float = 0.0,
        expected_profit_usd: float = 0.0,
        estimated_gas_cost_usd: float = 0.0,
        net_profit_usd: float = 0.0,
        risk_score: int = 0,
        timestamp: int = 0,
    ):
        """Initialize opportunity response.
        
        Args:
            id: Opportunity ID.
            path: Arbitrage path.
            input_token: Input token.
            input_amount: Input amount.
            expected_profit_percentage: Expected profit percentage.
            expected_profit_usd: Expected profit in USD.
            estimated_gas_cost_usd: Estimated gas cost in USD.
            net_profit_usd: Net profit in USD.
            risk_score: Risk score (1-5).
            timestamp: Timestamp.
        """
        self.id = id
        self.path = path or []
        self.input_token = input_token
        self.input_amount = input_amount
        self.expected_profit_percentage = expected_profit_percentage
        self.expected_profit_usd = expected_profit_usd
        self.estimated_gas_cost_usd = estimated_gas_cost_usd
        self.net_profit_usd = net_profit_usd
        self.risk_score = risk_score
        self.timestamp = timestamp


class OpportunitiesResponse(BaseModel):
    """Opportunities response model."""
    
    __fields__ = ["opportunities", "total_count", "timestamp"]
    
    def __init__(
        self,
        opportunities: List[OpportunityResponse] = None,
        total_count: int = 0,
        timestamp: int = 0,
    ):
        """Initialize opportunities response.
        
        Args:
            opportunities: List of opportunities.
            total_count: Total number of opportunities.
            timestamp: Timestamp.
        """
        self.opportunities = opportunities or []
        self.total_count = total_count
        self.timestamp = timestamp


class TradeResponse(BaseModel):
    """Trade response model."""
    
    __fields__ = [
        "id",
        "opportunity_id",
        "status",
        "steps",
        "transaction_hash",
        "block_number",
        "net_profit_usd",
        "timestamp",
    ]
    
    def __init__(
        self,
        id: str = "",
        opportunity_id: str = "",
        status: str = "",
        steps: List[Dict[str, Any]] = None,
        transaction_hash: str = "",
        block_number: int = 0,
        net_profit_usd: float = 0.0,
        timestamp: int = 0,
    ):
        """Initialize trade response.
        
        Args:
            id: Trade ID.
            opportunity_id: Opportunity ID.
            status: Trade status.
            steps: Trade steps.
            transaction_hash: Transaction hash.
            block_number: Block number.
            net_profit_usd: Net profit in USD.
            timestamp: Timestamp.
        """
        self.id = id
        self.opportunity_id = opportunity_id
        self.status = status
        self.steps = steps or []
        self.transaction_hash = transaction_hash
        self.block_number = block_number
        self.net_profit_usd = net_profit_usd
        self.timestamp = timestamp


class TradesResponse(BaseModel):
    """Trades response model."""
    
    __fields__ = ["trades", "total_count", "timestamp"]
    
    def __init__(
        self,
        trades: List[TradeResponse] = None,
        total_count: int = 0,
        timestamp: int = 0,
    ):
        """Initialize trades response.
        
        Args:
            trades: List of trades.
            total_count: Total number of trades.
            timestamp: Timestamp.
        """
        self.trades = trades or []
        self.total_count = total_count
        self.timestamp = timestamp


class ConfigResponse(BaseModel):
    """Config response model."""
    
    __fields__ = ["trading", "dexes", "networks", "mev_protection", "flash_loans"]
    
    def __init__(
        self,
        trading: Dict[str, Any] = None,
        dexes: List[Dict[str, Any]] = None,
        networks: List[Dict[str, Any]] = None,
        mev_protection: Dict[str, Any] = None,
        flash_loans: Dict[str, Any] = None,
    ):
        """Initialize config response.
        
        Args:
            trading: Trading configuration.
            dexes: DEX configurations.
            networks: Network configurations.
            mev_protection: MEV protection configuration.
            flash_loans: Flash loan configuration.
        """
        self.trading = trading or {}
        self.dexes = dexes or []
        self.networks = networks or []
        self.mev_protection = mev_protection or {}
        self.flash_loans = flash_loans or {}
