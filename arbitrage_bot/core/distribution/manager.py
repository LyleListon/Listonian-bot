"""Distribution management module."""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from .config import DistributionConfig

logger = logging.getLogger(__name__)

class DistributionManager:
    """Manages distribution of resources across DEXes."""

    def __init__(
        self,
        config: DistributionConfig,
        memory_bank: Any,
        storage_hub: Any
    ):
        """Initialize distribution manager."""
        self.config = config
        self.memory_bank = memory_bank
        self.storage_hub = storage_hub
        self.initialized = False
        self._exposures = {}
        self._liquidity = {}
        self._success_rates = {}
        self._gas_prices = {}
        self._volumes = {}

    def initialize(self) -> bool:
        """Initialize the distribution manager."""
        try:
            # Initialize tracking dictionaries
            self._exposures = {
                'dex': {},
                'pair': {}
            }
            self._liquidity = {}
            self._success_rates = {}
            self._gas_prices = {}
            self._volumes = {}

            self.initialized = True
            logger.info("Distribution manager initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize distribution manager: {e}")
            return False

    def get_dex_allocation(self, dex_name: str) -> Optional[Decimal]:
        """Get allocation for a specific DEX."""
        try:
            if not self.initialized:
                raise RuntimeError("Distribution manager not initialized")

            # Calculate allocation based on weights
            gas_score = self._get_gas_score(dex_name)
            liquidity_score = self._get_liquidity_score(dex_name)
            volume_score = self._get_volume_score(dex_name)
            success_score = self._get_success_score(dex_name)

            # Apply weights
            allocation = (
                gas_score * self.config.gas_price_weight +
                liquidity_score * self.config.liquidity_weight +
                volume_score * self.config.volume_weight +
                success_score * self.config.success_rate_weight
            )

            # Apply exposure limit
            current_exposure = self._exposures['dex'].get(dex_name, Decimal('0'))
            max_allocation = self.config.max_exposure_per_dex - current_exposure

            return min(allocation, max_allocation)

        except Exception as e:
            logger.error(f"Error getting DEX allocation: {e}")
            return None

    def _get_gas_score(self, dex_name: str) -> Decimal:
        """Calculate gas price score for DEX."""
        try:
            gas_price = self._gas_prices.get(dex_name)
            if not gas_price:
                return Decimal('0')

            # Lower gas price = higher score
            return Decimal('1') / (Decimal(str(gas_price)) + Decimal('1'))

        except Exception as e:
            logger.error(f"Error calculating gas score: {e}")
            return Decimal('0')

    def _get_liquidity_score(self, dex_name: str) -> Decimal:
        """Calculate liquidity score for DEX."""
        try:
            liquidity = self._liquidity.get(dex_name)
            if not liquidity:
                return Decimal('0')

            # Higher liquidity = higher score
            return min(
                Decimal(str(liquidity)) / self.config.min_liquidity_threshold,
                Decimal('1')
            )

        except Exception as e:
            logger.error(f"Error calculating liquidity score: {e}")
            return Decimal('0')

    def _get_volume_score(self, dex_name: str) -> Decimal:
        """Calculate volume score for DEX."""
        try:
            volume = self._volumes.get(dex_name)
            if not volume:
                return Decimal('0')

            # Normalize volume to [0, 1]
            total_volume = sum(self._volumes.values())
            if total_volume == 0:
                return Decimal('0')

            return Decimal(str(volume)) / Decimal(str(total_volume))

        except Exception as e:
            logger.error(f"Error calculating volume score: {e}")
            return Decimal('0')

    def _get_success_score(self, dex_name: str) -> Decimal:
        """Calculate success rate score for DEX."""
        try:
            success_rate = self._success_rates.get(dex_name)
            if not success_rate:
                return Decimal('0')

            return Decimal(str(success_rate))

        except Exception as e:
            logger.error(f"Error calculating success score: {e}")
            return Decimal('0')
