"""
Execution Adapter

This module contains adapters to integrate existing execution components
with the new arbitrage system architecture.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from ..interfaces import ExecutionStrategy, TransactionMonitor
from ..models import ArbitrageOpportunity, ExecutionResult, ExecutionStatus
from ...execution.arbitrage_executor import ArbitrageExecutor

logger = logging.getLogger(__name__)
