"""Uniswap V3 DEX implementation."""

from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
from web3.types import TxReceipt, Wei

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager

class UniswapV3DEX(BaseDEXV3):
    """Uniswap V3 DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize Uniswap V3 interface."""
        super().__init__(web3_manager, config)
        self.name = "Uniswap V3"
        self.version = "v3"
        self.logger.info(f"Initializing {self.name} {self.version} interface")

    async def initialize(self) -> bool:
        """Initialize the Uniswap V3 interface."""
        try:
            # Load contract ABIs
            self.router_abi = self.web3_manager.load_abi("IUniswapV3Router")
            self.factory_abi = self.web3_manager.load_abi("IUniswapV3Factory")
            self.pool_abi = self.web3_manager.load_abi("IUniswapV3Pool")
            self.quoter_abi = self.web3_manager.load_abi("IUniswapV3QuoterV2")
            
            # Initialize contracts
            self.router = self.w3.eth.contract(
                address=self.router_address,
                abi=self.router_abi
            )
            self.factory = self.w3.eth.contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            self.quoter = self.w3.eth.contract(
                address=self.config['quoter'],
                abi=self.quoter_abi
            )
            
            # Test connection by getting fee tier
            await self.factory.functions.feeAmountTickSpacing(3000).call()
            self.initialized = True
            self.logger.info(f"{self.name} interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, f"{self.name} initialization")
            return False

    async def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact analysis for Uniswap V3 pools."""
        try:
            # Validate inputs
            await self._validate_path(path)
            await self._validate_amounts(amount_in=amount_in)
            
            # Get pool address
            pool_address = await self.factory.functions.getPool(
                path[0],
                path[1],
                self.config['fee']
            ).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return None
                
            # Get pool contract
            pool = self.w3.eth.contract(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Get pool state
            slot0 = await pool.functions.slot0().call()
            liquidity = await pool.functions.liquidity().call()
            
            if liquidity == 0:
                return None
                
            # Get quote from quoter
            quote = await self.quoter.functions.quoteExactInputSingle(
                path[0],
                path[1],
                self.config['fee'],
                amount_in,
                0  # sqrtPriceLimitX96
            ).call()
            
            # Calculate price impact
            price_impact = self._calculate_price_impact_v3(
                amount_in,
                quote.amountOut,
                slot0.sqrtPriceX96,
                liquidity
            )
            
            return {
                'amount_in': amount_in,
                'amount_out': quote.amountOut,
                'price_impact': price_impact,
                'liquidity_depth': liquidity,
                'fee_rate': self.config['fee'] / 1000000,
                'estimated_gas': 200000,  # Base estimate for V3 swap
                'min_out': int(quote.amountOut * 0.995)  # 0.5% slippage
            }
            
        except Exception as e:
            self._handle_error(e, f"{self.name} quote calculation")
            return None

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int
    ) -> TxReceipt:
        """Execute a swap on Uniswap V3."""
        try:
            # Build exact input params
            params = {
                'tokenIn': path[0],
                'tokenOut': path[1],
                'fee': self.config['fee'],
                'recipient': to,
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': amount_out_min,
                'sqrtPriceLimitX96': 0
            }
            
            # Build transaction
            tx = await self.router.functions.exactInputSingle(
                params
            ).build_transaction({
                'from': to,
                'gas': 300000,  # Higher gas limit for V3
                'nonce': await self.w3.eth.get_transaction_count(to)
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                private_key=self.config.get('wallet', {}).get('private_key')
            )
            tx_hash = await self.w3.eth.send_raw_transaction(
                signed_tx.rawTransaction
            )
            
            # Wait for receipt
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Log transaction
            self._log_transaction(
                tx_hash.hex(),
                amount_in,
                amount_out_min,
                path
            )
            
            return receipt
            
        except Exception as e:
            self._handle_error(e, f"{self.name} swap execution")

    def _calculate_price_impact_v3(
        self,
        amount_in: int,
        amount_out: int,
        sqrt_price_x96: int,
        liquidity: int
    ) -> float:
        """Calculate price impact for V3 pools."""
        try:
            # Convert sqrtPriceX96 to price
            price = (sqrt_price_x96 ** 2) / (2 ** 192)
            
            # Calculate expected output without impact
            expected_out = amount_in * price
            
            # Calculate actual price impact
            impact = (expected_out - amount_out) / expected_out
            
            # Adjust impact based on liquidity depth
            liquidity_factor = min(1, (amount_in * price) / liquidity)
            adjusted_impact = impact * liquidity_factor
            
            return float(adjusted_impact)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate V3 price impact: {e}")
            return 1.0  # Return 100% impact on error
