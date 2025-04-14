"""Trades endpoint handler."""

import logging
import time
from typing import Dict, List, Any, Optional

from arbitrage_bot.api.endpoints.base_handler import BaseHandler
from arbitrage_bot.api.models.request import TradesRequest, ExecuteTradeRequest
from arbitrage_bot.api.models.response import TradesResponse, TradeResponse

logger = logging.getLogger(__name__)


class TradesHandler(BaseHandler):
    """Handler for trades endpoint."""
    
    def get_trades(self, request: TradesRequest) -> TradesResponse:
        """Get recent trades.
        
        Args:
            request: Trades request.
            
        Returns:
            Trades response.
        """
        # Get recent trades from transaction manager
        trades = self.bot.transaction_manager.get_recent_trades(limit=100)
        
        # Filter by status
        if request.status:
            trades = [
                trade for trade in trades
                if trade.get("status") == request.status
            ]
        
        # Apply pagination
        total_count = len(trades)
        trades = trades[request.offset:request.offset + request.limit]
        
        # Convert to response models
        trade_responses = []
        
        for trade in trades:
            trade_response = TradeResponse(
                id=trade.get("id", ""),
                opportunity_id=trade.get("opportunity_id", ""),
                status=trade.get("status", ""),
                steps=trade.get("steps", []),
                transaction_hash=trade.get("transaction_hash", ""),
                block_number=trade.get("block_number", 0),
                net_profit_usd=trade.get("net_profit_usd", 0.0),
                timestamp=trade.get("timestamp", int(time.time())),
            )
            
            trade_responses.append(trade_response)
        
        # Create response
        response = TradesResponse(
            trades=trade_responses,
            total_count=total_count,
            timestamp=int(time.time()),
        )
        
        return response
    
    def get_trade(self, trade_id: str) -> Optional[TradeResponse]:
        """Get a specific trade.
        
        Args:
            trade_id: Trade ID.
            
        Returns:
            Trade response, or None if not found.
        """
        # Get trade from transaction manager
        trade = self.bot.transaction_manager.get_trade(trade_id)
        
        if not trade:
            return None
        
        # Convert to response model
        trade_response = TradeResponse(
            id=trade.get("id", ""),
            opportunity_id=trade.get("opportunity_id", ""),
            status=trade.get("status", ""),
            steps=trade.get("steps", []),
            transaction_hash=trade.get("transaction_hash", ""),
            block_number=trade.get("block_number", 0),
            net_profit_usd=trade.get("net_profit_usd", 0.0),
            timestamp=trade.get("timestamp", int(time.time())),
        )
        
        return trade_response
    
    def execute_trade(self, request: ExecuteTradeRequest) -> TradeResponse:
        """Execute a trade for an opportunity.
        
        Args:
            request: Execute trade request.
            
        Returns:
            Trade response.
        """
        # Check if trading is enabled
        trading_enabled = self.bot.config.get("trading", {}).get("trading_enabled", False)
        if not trading_enabled:
            raise ValueError("Trading is disabled")
        
        # Get opportunity
        opportunity = self.bot.arbitrage_engine.get_opportunity_by_id(request.opportunity_id)
        if not opportunity:
            raise ValueError(f"Opportunity {request.opportunity_id} not found")
        
        # Prepare execution plan
        execution_plan = self.bot.arbitrage_engine.prepare_execution_plan(opportunity)
        
        # Apply options
        if request.options:
            execution_plan.update(request.options)
        
        # Execute trade
        trade = self.bot.transaction_manager.execute_trade(execution_plan)
        
        # Convert to response model
        trade_response = TradeResponse(
            id=trade.get("id", ""),
            opportunity_id=trade.get("opportunity_id", ""),
            status=trade.get("status", ""),
            steps=trade.get("steps", []),
            transaction_hash=trade.get("transaction_hash", ""),
            block_number=trade.get("block_number", 0),
            net_profit_usd=trade.get("net_profit_usd", 0.0),
            timestamp=trade.get("timestamp", int(time.time())),
        )
        
        return trade_response
