"""RocketSwap DEX implementation."""

from typing import Dict, Any, List, Optional
from .base_dex_v2 import BaseDEXV2
from ..web3.web3_manager import Web3Manager

class RocketSwapDEX(BaseDEXV2):
    """RocketSwap DEX V2 implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize RocketSwap DEX."""
        super().__init__(web3_manager, config)
        self.name = "rocketswap"

    async def initialize(self) -> bool:
        """Initialize the RocketSwap DEX interface."""
        try:
            # Load contract ABIs
            self.router_abi = self.web3_manager.load_abi(f"{self.name.lower()}_router")
            self.factory_abi = self.web3_manager.load_abi(f"{self.name.lower()}_factory")
            self.pair_abi = self.web3_manager.load_abi(f"{self.name.lower()}_pair")
            
            # Initialize contracts
            self.router = self.w3.eth.contract(
                address=self.router_address,
                abi=self.router_abi
            )
            self.factory = self.w3.eth.contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            
            # Test connection using feeTo() instead of allPairsLength()
            await self.factory.functions.feeTo().call()
            self.initialized = True
            self.logger.info(f"{self.name} interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "RocketSwap initialization")
            return False
