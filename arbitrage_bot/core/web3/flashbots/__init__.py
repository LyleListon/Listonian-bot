"""
Flashbots Integration Package

This package provides classes and utilities for interacting with Flashbots,
enabling private transaction submission to protect against MEV attacks.
"""

from .interfaces import (
    FlashbotsBundle, 
    BundleSimulationResult,
    BundleSubmissionResult,
    BundleStatsResult
)
from .provider import FlashbotsProvider
from .simulator import BundleSimulator

__all__ = [
    'FlashbotsBundle',
    'FlashbotsProvider',
    'BundleSimulator',
    'BundleSimulationResult',
    'BundleSubmissionResult',
    'BundleStatsResult'
]