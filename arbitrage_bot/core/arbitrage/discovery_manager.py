"""
Discovery Manager Implementation

This module provides the implementation of the OpportunityDiscoveryManager protocol.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from .interfaces import OpportunityDetector, OpportunityValidator, OpportunityDiscoveryManager
from .models import ArbitrageOpportunity

logger = logging.getLogger(__name__)

class DiscoveryManager(OpportunityDiscoveryManager):
    """
    Implementation of the OpportunityDiscoveryManager protocol.
    
    This class coordinates opportunity detectors and validators to discover
    and validate arbitrage opportunities.
    """
    
    def __init__(self):
        """Initialize the discovery manager."""
        self._detectors = {}  # detector_id -> detector
        self._validators = {}  # validator_id -> validator
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the discovery manager."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing discovery manager")
            self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            self._initialized = False
            self._detectors.clear()
            self._validators.clear()
    
    async def register_detector(
        self,
        detector: OpportunityDetector,
        detector_id: str
    ) -> None:
        """
        Register an opportunity detector.
        
        Args:
            detector: The detector to register
            detector_id: Unique identifier for the detector
        """
        async with self._lock:
            if detector_id in self._detectors:
                raise ValueError(f"Detector {detector_id} already registered")
            
            self._detectors[detector_id] = detector
            logger.info(f"Registered detector {detector_id}")
    
    async def register_validator(
        self,
        validator: OpportunityValidator,
        validator_id: str
    ) -> None:
        """
        Register an opportunity validator.
        
        Args:
            validator: The validator to register
            validator_id: Unique identifier for the validator
        """
        async with self._lock:
            if validator_id in self._validators:
                raise ValueError(f"Validator {validator_id} already registered")
            
            self._validators[validator_id] = validator
            logger.info(f"Registered validator {validator_id}")
    
    async def discover_opportunities(
        self,
        max_results: int = 10,
        min_profit_wei: int = 0,
        market_condition: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Discover arbitrage opportunities.
        
        Args:
            max_results: Maximum number of opportunities to return
            min_profit_wei: Minimum profit threshold in wei
            market_condition: Current market state and prices
            **kwargs: Additional parameters
            
        Returns:
            List of discovered opportunities
        """
        if not self._initialized:
            logger.warning("Discovery manager not initialized")
            return []
        
        if not market_condition:
            logger.warning("No market condition provided")
            return []
        
        all_opportunities = []
        
        # Discover opportunities from all detectors
        for detector_id, detector in self._detectors.items():
            try:
                opportunities = await detector.detect_opportunities(
                    market_condition=market_condition,
                    **kwargs
                )
                all_opportunities.extend(opportunities)
            except Exception as e:
                logger.error(f"Error in detector {detector_id}: {e}", exc_info=True)
        
        # Filter by profit threshold
        filtered_opportunities = [
            opp for opp in all_opportunities
            if opp.expected_profit_wei >= min_profit_wei
        ]
        
        # Validate opportunities
        valid_opportunities = []
        for opportunity in filtered_opportunities:
            is_valid = True
            
            # Run through all validators
            for validator_id, validator in self._validators.items():
                try:
                    valid, error_msg, confidence = await validator.validate_opportunity(
                        opportunity=opportunity,
                        market_condition=market_condition,
                        **kwargs
                    )
                    
                    if not valid:
                        logger.debug(
                            f"Opportunity {opportunity.id} rejected by validator "
                            f"{validator_id}: {error_msg}"
                        )
                        is_valid = False
                        break
                    
                    # Update confidence score
                    if confidence is not None:
                        opportunity.confidence_score = min(
                            opportunity.confidence_score,
                            confidence
                        )
                        
                except Exception as e:
                    logger.error(
                        f"Error in validator {validator_id}: {e}",
                        exc_info=True
                    )
                    is_valid = False
                    break
            
            if is_valid:
                valid_opportunities.append(opportunity)
        
        # Sort by expected profit and return top results
        valid_opportunities.sort(
            key=lambda x: x.expected_profit_wei,
            reverse=True
        )
        return valid_opportunities[:max_results]