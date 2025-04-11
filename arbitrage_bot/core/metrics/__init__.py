"""
Metrics collection and monitoring.

This module provides:
1. System metrics collection
2. Performance monitoring
3. Resource tracking
4. Error rate calculation
"""

from .metrics import MetricsCollector, get_metrics_collector

__all__ = ["MetricsCollector", "get_metrics_collector"]
