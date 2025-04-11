"""
Discovery Manager Implementation

This module provides the implementation of the OpportunityDiscoveryManager protocol.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .interfaces import (
    OpportunityDetector,
    OpportunityValidator,
    OpportunityDiscoveryManager,
)
from ..memory.memory_bank import MemoryBank
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
        self._memory_bank = MemoryBank()

    async def initialize(self) -> None:
        """Initialize the discovery manager."""
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing discovery manager")
            await self._memory_bank.initialize()
            self._initialized = True

    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            self._initialized = False
            self._detectors.clear()
            self._validators.clear()
            await self._memory_bank.cleanup()

    async def register_detector(
        self, detector: OpportunityDetector, detector_id: str
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
        self, validator: OpportunityValidator, validator_id: str
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
        **kwargs,
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
                    market_condition=market_condition, **kwargs
                )
                all_opportunities.extend(opportunities)
            except Exception as e:
                logger.error(f"Error in detector {detector_id}: {e}", exc_info=True)

        logger.debug(
            f"Detected {len(all_opportunities)} raw opportunities before profit filtering."
        )
        for opp in all_opportunities:
            logger.debug(f"  - Raw Opp ID: {opp.id}, Profit: {opp.expected_profit_wei}")
        # Filter by profit threshold
        filtered_opportunities = [
            opp
            for opp in all_opportunities
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
                        **kwargs,
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
                            opportunity.confidence_score, confidence
                        )

                except Exception as e:
                    logger.error(
                        f"Error in validator {validator_id}: {e}", exc_info=True
                    )
                    is_valid = False
                    break

            if is_valid:
                valid_opportunities.append(opportunity)

        # Sort by expected profit and return top results
        valid_opportunities.sort(key=lambda x: x.expected_profit_wei, reverse=True)

        # Get top opportunities
        top_opportunities = valid_opportunities[:max_results]

        # Update memory bank state
        await self._update_state(top_opportunities, market_condition)

        return top_opportunities

    async def _update_state(
        self,
        opportunities: List[ArbitrageOpportunity],
        market_condition: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update memory bank state with current opportunities."""
        try:
            state_dir = Path("memory-bank/state")
            state_dir.mkdir(parents=True, exist_ok=True)

            state = {
                "opportunities": [
                    {
                        "id": opp.id,
                        "token_pair": opp.token_pair,
                        "dex_1": opp.dex_1,
                        "dex_2": opp.dex_2,
                        "expected_profit_wei": str(opp.expected_profit_wei),
                        "confidence_score": opp.confidence_score,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    for opp in opportunities
                ],
                "market_condition": market_condition or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Write to state file
            state_file = state_dir / "opportunities.json"
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Error updating discovery state: {e}", exc_info=True)
