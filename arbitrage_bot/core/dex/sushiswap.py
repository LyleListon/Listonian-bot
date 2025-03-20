"""Sushiswap DEX implementation."""

from typing import Dict, Any
from web3 import Web3

from .base_dex_v2 import BaseDEXV2
from ..web3.web3_manager import Web3Manager

class SushiswapDEX(BaseDEXV2):
    """Sushiswap DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize Sushiswap interface."""
        # Call parent constructor with config
        super().__init__(web3_manager, config)
        
        # Set Sushiswap-specific attributes
        self.name = "Sushiswap"
        self.fee = 3000  # 0.3% fee
        
        # Override pair ABI name since we use Uniswap V2 pair ABI
        self.pair_abi_name = "IUniswapV2Pair"

    async def initialize(self) -> bool:
        """Initialize the Sushiswap interface."""
        try:
            # Load contract ABIs
            self.router_abi = await self.web3_manager._load_abi("sushiswap_router")
            self.factory_abi = await self.web3_manager._load_abi("sushiswap_factory")
            
            # Initialize contracts with checksummed addresses
            self.router = await self.web3_manager.get_contract(
                address=self.router_address,
                abi_name="sushiswap_router"
            )
            self.factory = await self.web3_manager.get_contract(
                address=self.factory_address,
                abi_name="sushiswap_factory"
            )
            
            # Mark as initialized
            self.initialized = True
            self.logger.info("Sushiswap interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "Sushiswap initialization")
            return False

    async def get_method_signatures(self) -> Dict[str, str]:
        """Get method signatures for Sushiswap."""
        return {
            'swapExactTokensForTokens': 'swapExactTokensForTokens(uint256,uint256,address[],address,uint256)',
            'getAmountsOut': 'getAmountsOut(uint256,address[])',
            'getPair': 'getPair(address,address)',
            'getReserves': 'getReserves()'
        }