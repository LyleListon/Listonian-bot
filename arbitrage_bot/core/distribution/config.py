"""Distribution configuration module."""

from dataclasses import dataclass
from decimal import Decimal

@dataclass
class DistributionConfig:
    """Configuration for distribution management."""
    max_exposure_per_dex: Decimal
    max_exposure_per_pair: Decimal
    min_liquidity_threshold: Decimal
    rebalance_threshold: Decimal
    gas_price_weight: float
    liquidity_weight: float
    volume_weight: float
    success_rate_weight: float