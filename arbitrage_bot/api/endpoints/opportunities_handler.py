"""Opportunities endpoint handler."""

import logging
import time
from typing import Dict, List, Any, Optional

from arbitrage_bot.api.endpoints.base_handler import BaseHandler
from arbitrage_bot.api.models.request import OpportunitiesRequest
from arbitrage_bot.api.models.response import OpportunitiesResponse, OpportunityResponse

logger = logging.getLogger(__name__)


class OpportunitiesHandler(BaseHandler):
    """Handler for opportunities endpoint."""
    
    def get_opportunities(self, request: OpportunitiesRequest) -> OpportunitiesResponse:
        """Get arbitrage opportunities.
        
        Args:
            request: Opportunities request.
            
        Returns:
            Opportunities response.
        """
        # Get current opportunities from arbitrage engine
        opportunities = self.bot.arbitrage_engine.current_opportunities
        
        # Filter by minimum profit
        if request.min_profit > 0:
            opportunities = [
                opp for opp in opportunities
                if opp.get("expected_profit_percentage", 0) >= request.min_profit
            ]
        
        # Filter by maximum risk
        if request.max_risk < 5:
            opportunities = [
                opp for opp in opportunities
                if opp.get("risk_score", 5) <= request.max_risk
            ]
        
        # Filter by token
        if request.token:
            opportunities = [
                opp for opp in opportunities
                if opp.get("input_token") == request.token
                or any(edge.get("from_token") == request.token for edge in opp.get("path", []))
                or any(edge.get("to_token") == request.token for edge in opp.get("path", []))
            ]
        
        # Apply pagination
        total_count = len(opportunities)
        opportunities = opportunities[request.offset:request.offset + request.limit]
        
        # Convert to response models
        opportunity_responses = []
        
        for opp in opportunities:
            opportunity_response = OpportunityResponse(
                id=opp.get("id", ""),
                path=opp.get("path", []),
                input_token=opp.get("input_token", ""),
                input_amount=opp.get("input_amount", 0.0),
                expected_profit_percentage=opp.get("expected_profit_percentage", 0.0),
                expected_profit_usd=opp.get("expected_profit_usd", 0.0),
                estimated_gas_cost_usd=opp.get("estimated_gas_cost_usd", 0.0),
                net_profit_usd=opp.get("net_profit_usd", 0.0),
                risk_score=opp.get("risk_score", 0),
                timestamp=opp.get("timestamp", int(time.time())),
            )
            
            opportunity_responses.append(opportunity_response)
        
        # Create response
        response = OpportunitiesResponse(
            opportunities=opportunity_responses,
            total_count=total_count,
            timestamp=int(time.time()),
        )
        
        return response
    
    def get_opportunity(self, opportunity_id: str) -> Optional[OpportunityResponse]:
        """Get a specific opportunity.
        
        Args:
            opportunity_id: Opportunity ID.
            
        Returns:
            Opportunity response, or None if not found.
        """
        # Get opportunity from arbitrage engine
        opp = self.bot.arbitrage_engine.get_opportunity_by_id(opportunity_id)
        
        if not opp:
            return None
        
        # Convert to response model
        opportunity_response = OpportunityResponse(
            id=opp.get("id", ""),
            path=opp.get("path", []),
            input_token=opp.get("input_token", ""),
            input_amount=opp.get("input_amount", 0.0),
            expected_profit_percentage=opp.get("expected_profit_percentage", 0.0),
            expected_profit_usd=opp.get("expected_profit_usd", 0.0),
            estimated_gas_cost_usd=opp.get("estimated_gas_cost_usd", 0.0),
            net_profit_usd=opp.get("net_profit_usd", 0.0),
            risk_score=opp.get("risk_score", 0),
            timestamp=opp.get("timestamp", int(time.time())),
        )
        
        return opportunity_response
