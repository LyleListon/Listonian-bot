"""Portfolio tracking utilities - compatibility layer for performance tracker."""

from ..monitoring import PerformanceTracker, create_performance_tracker

# Re-export with new names for backward compatibility
PortfolioTracker = PerformanceTracker
create_portfolio_tracker = create_performance_tracker

__all__ = ["PortfolioTracker", "create_portfolio_tracker"]
