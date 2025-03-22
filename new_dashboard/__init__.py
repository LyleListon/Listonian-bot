"""Dashboard package for arbitrage bot monitoring."""

from .dashboard import app
from .components import create_production_components

__all__ = ['app', 'create_production_components']
