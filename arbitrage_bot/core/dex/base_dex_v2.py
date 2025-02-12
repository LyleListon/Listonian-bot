"""Base class for V2 DEX implementations."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt

from .base_dex import BaseDEX
from ..web3.web3_manager import Web3Manager

class BaseDEXV2(BaseDEX):
    """Base class implementing V2 DEX-specific functionality."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize V2 DEX interface."""
        super().__init__(web3_manager, config)
        self.fee = config.get('fee', 3000)  # 0.3% default fee for most V2 DEXs
        self.pair_abi = None

    async def initialize(self) -> bool:
        """Initialize the V2 DEX interface."""
        try:
            # Load contract ABIs
            self.router_abi = self.web3_manager.load_abi(f"{self.name.lower()}_router")
            self.factory_abi = self.web3_manager.load_abi(f"{self.name.lower()}_factory")
            self.pair_abi = self.web3_manager.load_abi(f"{self.name.lower()}_pair")
            
            # Initialize contracts
            self.router = await self.web3_manager.get_contract_async(
                address=self.router_address,
                abi=self.router_abi
            )
            self.factory = await self.web3_manager.get_contract_async(
                address=self.factory_address,
                abi=self.factory_abi
            )
            
            # Test connection
            factory_address = await self.router.functions.factory()
            if factory_address != self.factory_address:
                raise ValueError("Router factory address mismatch")
                
            self.initialized = True
            self.logger.info(f"{self.name} interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "V2 DEX initialization")
            return False

    async def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact analysis for V2 pools."""
        try:
            # Validate inputs
            await self._validate_path(path)
            await self._validate_amounts(amount_in=amount_in)
            
            # Get pair address
            pair_address = await self.factory.functions.getPair(path[0], path[1])
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return None
                
            # Get pair contract
            pair = await self.web3_manager.get_contract_async(
                address=pair_address,
                abi=self.pair_abi
            )
            
            # Get reserves
            reserves = await pair.functions.getReserves()
            token0 = await pair.functions.token0()
            
            # Determine which reserve corresponds to which token
            if path[0].lower() == token0.lower():
                reserve_in = reserves[0]
                reserve_out = reserves[1]
            else:
                reserve_in = reserves[1]
                reserve_out = reserves[0]
            
            if reserve_in == 0 or reserve_out == 0:
                return None
                
            # Calculate amounts
            amount_out = await self._get_amount_out(
                amount_in,
                reserve_in,
                reserve_out
            )
            
            # Calculate price impact
            price_impact = self._calculate_price_impact(
                amount_in,
                amount_out,
                reserve_in,
                reserve_out
            )
            
            return {
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price_impact': price_impact,
                'liquidity_depth': min(reserve_in, reserve_out),
                'fee_rate': self.fee / 1000000,  # Convert from basis points
                'estimated_gas': 150000,  # Base estimate for V2 swap
                'min_out': int(amount_out * 0.995)  # 0.5% slippage default
            }
            
        except Exception as e:
            self._handle_error(e, "V2 quote calculation")
            return None

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int
    ) -> TxReceipt:
        """Execute a V2 swap."""
        try:
            # Validate inputs
            await self._validate_path(path)
            await self._validate_amounts(amount_in, amount_out_min)
            
            # Build transaction
            tx = await self.router.functions.swapExactTokensForTokens(
                amount_in,
                amount_out_min,
                path,
                to,
                deadline
            ).build_transaction({
                'from': to,
                'gas': 300000,
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
            self._handle_error(e, "V2 swap execution")

    async def _get_amount_out(
        self,
        amount_in: int,
        reserve_in: int,
        reserve_out: int
    ) -> int:
        """Calculate output amount for V2 pools."""
        amount_in_with_fee = amount_in * (10000 - self.fee)
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in * 10000 + amount_in_with_fee
        return numerator // denominator

    def _calculate_price_impact(
        self,
        amount_in: int,
        amount_out: int,
        reserve_in: int,
        reserve_out: int
    ) -> float:
        """Calculate price impact percentage for V2 pools."""
        try:
            # Calculate price before trade
            price_before = reserve_out / reserve_in
            
            # Calculate expected output without impact
            expected_out = amount_in * price_before
            
            # Calculate actual price impact
            impact = (expected_out - amount_out) / expected_out
            
            # Adjust impact based on liquidity depth
            liquidity_factor = min(1, amount_in / reserve_in)
            adjusted_impact = impact * liquidity_factor
            
            return float(adjusted_impact)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate price impact: {e}")
            return 1.0  # Return 100% impact on error (will prevent trade)
