"""
Arbitrage Opportunity Detectors

This package contains detector implementations for identifying arbitrage opportunities
across different DEXs and trading pairs.
"""

from .cross_dex_detector import CrossDexDetector

from .triangular_detector import TriangularDetector

__all__ = ["CrossDexDetector", "TriangularDetector"]
