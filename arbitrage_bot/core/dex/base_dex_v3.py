"""Base class for V3 DEX implementations."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt

from .base_dex import BaseDEX
from ..web3.web3_manager import Web3Manager

class BaseDEXV3(BaseDEX):
    """Base class implementing V3 DEX-specific functionality."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize V3 DEX interface."""
        super().__init__(web3_manager, config)
        self.quoter_address = config.get('quoter')
        self.fee = config.get('fee', 3000)  # 0.3% default fee
        self.pool_abi = None
        self.quoter_abi = None

    async def initialize(self) -> bool:
        """Initialize the V3 DEX interface."""
        try:
            # Load contract ABIs
            self.router_abi = self.w3.web3_manager.load_abi(f"{self.name.lower()}_v3_router")
            self.factory_abi = self.w3.web3_manager.load_abi(f"{self.name.lower()}_factory")
            self.pool_abi = self.w3.web3_manager.load_abi(f"{self.name.lower()}_v3_pool")
            if self.quoter_address:
                self.quoter_abi = self.w3.web3_manager.load_abi(f"{self.name.lower()}_quoter")
            
            # Initialize contracts
            self.router = self.w3.eth.contract(
                address=self.router_address,
                abi=self.router_abi
            )
            self.factory = self.w3.eth.contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            if self.quoter_address:
                self.quoter = self.w3.eth.contract(
                    address=self.quoter_address,
                    abi=self.quoter_abi
                )
            
            # Test connection
            await self.router.functions.factory().call()
            if self.quoter_address:
                await self.quoter.functions.factory().call()
                
            self.initialized = True
            self.logger.info(f"{self.name} V3 interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "V3 DEX initialization")
            return False

    async def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact analysis for V3 pools."""
        try:
            # Validate inputs
            await self._validate_path(path)
            await self._validate_amounts(amount_in=amount_in)
            
            if not self.quoter_address:
                raise ValueError("Quoter address not configured")
                
            # Get pool info
            pool_address = await self.factory.functions.getPool(
                path[0],
                path[1],
                self.fee
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
            
            # Get quote from quoter
            encoded_path = self._encode_path(path)
            quote = await self.quoter.functions.quoteExactInput(
                encoded_path,
                amount_in
            ).call()
            
            # Calculate price impact
            sqrt_price_x96 = slot0[0]
            price_impact = self._calculate_price_impact(
                amount_in,
                quote,
                sqrt_price_x96,
                liquidity
            )
            
            return {
                'amount_in': amount_in,
                'amount_out': quote,
                'price_impact': price_impact,
                'liquidity_depth': liquidity,
                'fee_rate': self.fee / 1000000,  # Convert from basis points
                'estimated_gas': 200000,  # Base estimate for V3 swap
                'min_out': int(quote * 0.995)  # 0.5% slippage default
            }
            
        except Exception as e:
            self._handle_error(e, "V3 quote calculation")
            return None

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int
    ) -> TxReceipt:
        """Execute a V3 swap."""
        try:
            # Validate inputs
            await self._validate_path(path)
            await self._validate_amounts(amount_in, amount_out_min)
            
            # Encode the path with fees
            encoded_path = self._encode_path(path)
            
            # Build exact input params
            params = {
                'path': encoded_path,
                'recipient': to,
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': amount_out_min
            }
            
            # Build transaction
            tx = await self.router.functions.exactInput(params).build_transaction({
                'from': to,
                'gas': 350000,  # V3 needs more gas
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
            self._handle_error(e, "V3 swap execution")

    def _encode_path(self, path: List[str]) -> bytes:
        """Encode path with fees for V3 swap."""
        encoded = b''
        for i in range(len(path) - 1):
            encoded += bytes.fromhex(path[i][2:])  # Remove '0x' prefix
            encoded += self.fee.to_bytes(3, 'big')  # Add fee as 3 bytes
        encoded += bytes.fromhex(path[-1][2:])  # Add final token
        return encoded

    def _calculate_price_impact(
        self,
        amount_in: int,
        amount_out: int,
        sqrt_price_x96: int,
        liquidity: int
    ) -> float:
        """Calculate price impact percentage for V3 pools."""
        try:
            # Convert sqrtPriceX96 to price
            price = (sqrt_price_x96 ** 2) / (2 ** 192)
            
            # Calculate expected output without impact
            expected_out = amount_in * price
            
            # Calculate actual price impact
            impact = (expected_out - amount_out) / expected_out
            
            # Adjust impact based on liquidity depth
            liquidity_factor = min(1, amount_in / liquidity)
            adjusted_impact = impact * liquidity_factor
            
            return float(adjusted_impact)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate V3 price impact: {e}")
            return 1.0  # Return 100% impact on error (will prevent trade)
