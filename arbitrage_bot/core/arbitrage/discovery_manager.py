"""
Opportunity Discovery Manager

This module contains the implementation of the OpportunityDiscoveryManager,
which coordinates the discovery and validation of arbitrage opportunities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set, Tuple

from .interfaces import (
    OpportunityDiscoveryManager,
    OpportunityDetector,
    OpportunityValidator,
    MarketDataProvider
)
from .models import (
    ArbitrageOpportunity,
    OpportunityStatus,
    MarketCondition
)

logger = logging.getLogger(__name__)


class BaseOpportunityDiscoveryManager(OpportunityDiscoveryManager):
    """
    Base implementation of the OpportunityDiscoveryManager.
    
    This class coordinates the discovery and validation of arbitrage
    opportunities using registered detectors and validators.
    """
    
    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the discovery manager.
        
        Args:
            market_data_provider: Provider of market data
            config: Configuration dictionary
        """
        self.market_data_provider = market_data_provider
        self.config = config or {}
        
        # Registered components
        self._detectors: Dict[str, OpportunityDetector] = {}
        self._validators: Dict[str, OpportunityValidator] = {}
        
        # Configuration
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.5)
        self.validation_timeout = self.config.get("validation_timeout_seconds", 10)
        self.discovery_timeout = self.config.get("discovery_timeout_seconds", 30)
        
        # Locks
        self._discovery_lock = asyncio.Lock()
        self._validation_lock = asyncio.Lock()
        
        logger.info("BaseOpportunityDiscoveryManager initialized")
    
    async def register_detector(
        self,
        detector: OpportunityDetector,
        detector_id: str
    ) -> None:
        """
        Register an opportunity detector.
        
        Args:
            detector: Detector to register
            detector_id: Unique identifier for this detector
        """
        if detector_id in self._detectors:
            logger.warning(f"Detector {detector_id} already registered, replacing")
        
        self._detectors[detector_id] = detector
        logger.info(f"Registered detector: {detector_id}")
    
    async def register_validator(
        self,
        validator: OpportunityValidator,
        validator_id: str
    ) -> None:
        """
        Register an opportunity validator.
        
        Args:
            validator: Validator to register
            validator_id: Unique identifier for this validator
        """
        if validator_id in self._validators:
            logger.warning(f"Validator {validator_id} already registered, replacing")
        
        self._validators[validator_id] = validator
        logger.info(f"Registered validator: {validator_id}")
    
    async def discover_opportunities(
        self,
        max_results: int = 10,
        detector_ids: Optional[List[str]] = None,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Discover arbitrage opportunities.
        
        Args:
            max_results: Maximum number of opportunities to return
            detector_ids: Specific detectors to use, or None for all
            **kwargs: Additional discovery parameters
            
        Returns:
            List of validated arbitrage opportunities
        """
        async with self._discovery_lock:
            logger.info(f"Discovering opportunities with {len(self._detectors)} detectors")
            
            # Get current market condition
            market_condition = await self.market_data_provider.get_market_condition()
            
            # Select detectors to use
            selected_detectors = {}
            if detector_ids:
                for detector_id in detector_ids:
                    if detector_id in self._detectors:
                        selected_detectors[detector_id] = self._detectors[detector_id]
                    else:
                        logger.warning(f"Detector {detector_id} not found")
            else:
                selected_detectors = self._detectors
            
            if not selected_detectors:
                logger.warning("No detectors available for discovery")
                return []
            
            # Run detectors in parallel with timeout
            detection_tasks = []
            for detector_id, detector in selected_detectors.items():
                task = asyncio.create_task(self._run_detector(
                    detector=detector,
                    detector_id=detector_id,
                    market_condition=market_condition,
                    max_results=max_results,
                    **kwargs
                ))
                detection_tasks.append(task)
            
            # Wait for all detectors with timeout
            try:
                completed, pending = await asyncio.wait(
                    detection_tasks,
                    timeout=self.discovery_timeout
                )
                
                # Cancel any pending tasks
                for task in pending:
                    task.cancel()
                
                # Process completed tasks
                all_opportunities = []
                for task in completed:
                    try:
                        result = task.result()
                        all_opportunities.extend(result)
                    except Exception as e:
                        logger.error(f"Error in detector task: {e}")
                
            except Exception as e:
                logger.error(f"Error running detectors: {e}")
                return []
            
            logger.info(f"Discovered {len(all_opportunities)} opportunities across all detectors")
            
            # Validate opportunities
            validated_opportunities = []
            for opportunity in all_opportunities:
                try:
                    validated = await self.validate_opportunity(opportunity)
                    if validated.status == OpportunityStatus.VALIDATED:
                        validated_opportunities.append(validated)
                except Exception as e:
                    logger.error(f"Error validating opportunity {opportunity.id}: {e}")
            
            logger.info(f"Validated {len(validated_opportunities)} opportunities")
            
            # Sort by expected profit and limit to max_results
            sorted_opportunities = sorted(
                validated_opportunities,
                key=lambda o: o.expected_profit,
                reverse=True
            )
            
            return sorted_opportunities[:max_results]
    
    async def validate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        validator_ids: Optional[List[str]] = None,
        **kwargs
    ) -> ArbitrageOpportunity:
        """
        Validate an arbitrage opportunity.
        
        Args:
            opportunity: Opportunity to validate
            validator_ids: Specific validators to use, or None for all
            **kwargs: Additional validation parameters
            
        Returns:
            Updated opportunity with validation results
        """
        async with self._validation_lock:
            logger.info(f"Validating opportunity {opportunity.id}")
            
            # Get current market condition
            market_condition = await self.market_data_provider.get_market_condition()
            
            # Select validators to use
            selected_validators = {}
            if validator_ids:
                for validator_id in validator_ids:
                    if validator_id in self._validators:
                        selected_validators[validator_id] = self._validators[validator_id]
                    else:
                        logger.warning(f"Validator {validator_id} not found")
            else:
                selected_validators = self._validators
            
            if not selected_validators:
                logger.warning("No validators available for validation")
                opportunity.status = OpportunityStatus.REJECTED
                return opportunity
            
            # Run validators in sequence
            validated_opportunity = opportunity
            validated_opportunity.status = OpportunityStatus.VALIDATED  # Start as validated
            
            for validator_id, validator in selected_validators.items():
                try:
                    # Set a timeout for validation
                    validated_opportunity = await asyncio.wait_for(
                        validator.validate_opportunity(
                            opportunity=validated_opportunity,
                            market_condition=market_condition,
                            **kwargs
                        ),
                        timeout=self.validation_timeout
                    )
                    
                    # If any validator rejects, stop validation
                    if validated_opportunity.status == OpportunityStatus.REJECTED:
                        logger.info(f"Opportunity {opportunity.id} rejected by validator {validator_id}")
                        break
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Validator {validator_id} timed out")
                    validated_opportunity.status = OpportunityStatus.REJECTED
                    break
                except Exception as e:
                    logger.error(f"Validator {validator_id} failed: {e}")
                    validated_opportunity.status = OpportunityStatus.REJECTED
                    break
            
            # Check confidence threshold
            if (validated_opportunity.status == OpportunityStatus.VALIDATED and 
                validated_opportunity.confidence_score < self.min_confidence_threshold):
                logger.info(f"Opportunity {opportunity.id} rejected due to low confidence: {validated_opportunity.confidence_score}")
                validated_opportunity.status = OpportunityStatus.REJECTED
            
            logger.info(f"Validation result for {opportunity.id}: {validated_opportunity.status}")
            return validated_opportunity
    
    async def _run_detector(
        self,
        detector: OpportunityDetector,
        detector_id: str,
        market_condition: MarketCondition,
        max_results: int,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """Run a single detector with error handling."""
        try:
            logger.debug(f"Running detector: {detector_id}")
            opportunities = await detector.detect_opportunities(
                market_condition=market_condition,
                max_results=max_results,
                **kwargs
            )
            
            # Set source component for all opportunities
            for opportunity in opportunities:
                opportunity.source_component = detector_id
            
            logger.debug(f"Detector {detector_id} found {len(opportunities)} opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error in detector {detector_id}: {e}")
            return []


async def create_opportunity_discovery_manager(
    market_data_provider: MarketDataProvider,
    config: Dict[str, Any] = None
) -> BaseOpportunityDiscoveryManager:
    """
    Create and initialize an opportunity discovery manager.
    
    Args:
        market_data_provider: Provider of market data
        config: Configuration dictionary
        
    Returns:
        Initialized opportunity discovery manager
    """
    manager = BaseOpportunityDiscoveryManager(
        market_data_provider=market_data_provider,
        config=config
    )
    
    return manager