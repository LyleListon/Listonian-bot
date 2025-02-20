"""RocketSwap V3 DEX implementation."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal
from web3 import Web3

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager

class RocketSwapV3(BaseDEXV3):
    """RocketSwap V3 DEX implementation."""

    # RocketSwap V3 fee tiers
    FEE_TIERS = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize RocketSwap V3 interface."""
        super().__init__(web3_manager, config)
        self.name = "rocketswap_v3"
        self.weth_address = Web3.to_checksum_address(config['weth_address'])
        self.factory_address = Web3.to_checksum_address(config['factory'])
        self.router_address = Web3.to_checksum_address(config['router'])
        self.fee = config.get('fee', 3000)  # Default to 0.3%

    def initialize(self) -> bool:
        """Initialize the RocketSwap V3 interface."""
        try:
            # Load contract ABIs
            self.factory_abi = self.web3_manager.load_abi("swapbased_v3_factory")
            self.pool_abi = self.web3_manager.load_abi("IPancakeV3Pool")  # Use PancakeSwap V3 pool ABI as they're compatible
            
            # Initialize factory contract
            self.factory = self.web3_manager.get_contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            
            # Initialize router contract
            self.router = self.web3_manager.get_contract(
                address=self.router_address,
                abi=self.web3_manager.load_abi("swapbased_v3_router")  # Use SwapBased V3 router ABI
            )
            
            # Initialize contracts
            self.initialized = True
            self.logger.info(f"{self.name} interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "RocketSwap V3 initialization")
            return False

    def get_pool_address(self, token0: str, token1: str, fee: int) -> str:
        """Get pool address from factory."""
        try:
            # Ensure token addresses are in the correct order
            token0, token1 = sorted([token0, token1])
            
            # Get pool address from factory
            pool_address = self.factory.functions.getPool(
                token0,
                token1,
                fee
            ).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                self.logger.debug(f"No pool found for {token0}-{token1} with fee {fee}")
                return None
                
            return pool_address
            
        except Exception as e:
            self.logger.error(f"Error getting pool address: {e}")
            return None

    def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote including price impact and liquidity depth analysis."""
        try:
            # Validate inputs
            self._validate_path(path)
            self._validate_amounts(amount_in=amount_in)
            
            # Try each fee tier
            for fee in self.FEE_TIERS:
                try:
                    # Get pool address
                    pool_address = self.get_pool_address(path[0], path[1], fee)
                    if not pool_address:
                        continue
                        
                    # Get pool contract
                    pool = self.web3_manager.get_contract(
                        address=Web3.to_checksum_address(pool_address),
                        abi=self.pool_abi
                    )
                    
                    # Get pool state
                    slot0 = self._retry_sync(
                        lambda: pool.functions.slot0().call()
                    )
                    liquidity = self._retry_sync(
                        lambda: pool.functions.liquidity().call()
                    )
                    
                    # Calculate amounts from sqrtPriceX96
                    sqrt_price_x96 = slot0[0]
                    if sqrt_price_x96 == 0:
                        continue
                        
                    # Calculate price from sqrtPriceX96
                    price = (sqrt_price_x96 / (2 ** 96)) ** 2
                    
                    # Calculate output amount
                    amount_out = int(amount_in * price)
                    
                    # Calculate price impact
                    impact = self._calculate_price_impact(
                        amount_in=amount_in,
                        amount_out=amount_out,
                        sqrt_price_x96=sqrt_price_x96,
                        liquidity=liquidity
                    )
                    
                    return {
                        'amount_in': amount_in,
                        'amount_out': amount_out,
                        'price_impact': impact,
                        'liquidity_depth': liquidity,
                        'fee_rate': fee / 1000000,  # Convert from basis points
                        'estimated_gas': 350000,  # Base estimate for V3 swap
                        'min_out': int(amount_out * 0.995)  # 0.5% slippage default
                    }
                    
                except Exception as e:
                    self.logger.debug(f"Error getting quote for fee tier {fee}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get V3 quote: {e}")
            return None

    def get_token_price(self, token_address: str) -> float:
        """Get current token price."""
        try:
            # If token is WETH, return 1.0 since price is in WETH
            if token_address.lower() == self.weth_address.lower():
                return 1.0

            # Try each fee tier
            for fee in self.FEE_TIERS:
                try:
                    # Get pool address
                    pool_address = self.get_pool_address(
                        token_address,
                        self.weth_address,
                        fee
                    )
                    
                    if not pool_address:
                        continue
                        
                    # Get pool contract
                    pool = self.web3_manager.get_contract(
                        address=Web3.to_checksum_address(pool_address),
                        abi=self.pool_abi
                    )
                    
                    # Get slot0 data which contains the current sqrt price
                    slot0 = self._retry_sync(
                        lambda: pool.functions.slot0().call()
                    )
                    
                    # Calculate price from sqrtPriceX96
                    sqrt_price_x96 = slot0[0]
                    if sqrt_price_x96 == 0:
                        continue
                        
                    price = (sqrt_price_x96 / (2 ** 96)) ** 2
                    
                    # Adjust for token order
                    token0 = self._retry_sync(
                        lambda: pool.functions.token0().call()
                    )
                    
                    if token_address.lower() == token0.lower():
                        price = 1 / price
                        
                    return float(price)
                    
                except Exception as e:
                    self.logger.debug(f"Error getting price for fee tier {fee}: {e}")
                    continue
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to get token price: {e}")
            return 0.0