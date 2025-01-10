"""Arbitrage bot package initialization."""

import logging
from . import utils
from . import core
from . import dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
    datefmt="%Y-%m-%d %H:%M:%S",
)

__all__ = ["utils", "core", "dashboard"]
