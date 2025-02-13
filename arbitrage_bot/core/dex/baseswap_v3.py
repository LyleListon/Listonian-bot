"""Baseswap V3 DEX implementation."""

from typing import Dict, Any, List, Optional
import logging
import asyncio
from decimal import Decimal

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager
from .utils import validate_config

logger = logging.getLogger(__name__)

class BaseswapV3(BaseDEXV3):
    """Implementation of Baseswap V3 DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize Baseswap V3 interface."""
        # Validate config
        is_valid, error = validate_config(config, {
            'router': str,
            'factory': str,
            'fee': int,
            'tick_spacing': int,
            'quoter': str  # Add quoter address requirement
        })
        if not is_valid:
            raise ValueError(f"Invalid config: {error}")
            
        super().__init__(web3_manager, config)
        self.name = "BaseswapV3"
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize Baseswap V3 interface."""
        try:
            # Initialize base V3 DEX
            if not await super().initialize():
                return False
            
            # Initialize quoter if available
            if self.quoter_address:
                self.quoter = self.w3.eth.contract(
                    address=self.quoter_address,
                    abi=self.quoter_abi
                )
            
            self.initialized = True
            logger.info(f"Baseswap V3 interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "Baseswap V3 initialization")
            return False

    async def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Baseswap V3-specific quote implementation."""
        try:
            # Use base implementation as Baseswap follows standard V3 quoting
            return await super().get_quote_with_impact(amount_in, path)
        except Exception as e:
            self._handle_error(e, "Baseswap V3 quote calculation")
            return None