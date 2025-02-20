"""Base class for V2 DEX implementations."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal
from web3 import Web3
import eventlet

from .base_dex import BaseDEX
from ..web3.web3_manager import Web3Manager

class BaseDEXV2(BaseDEX):
    """Base class implementing V2 DEX-specific functionality."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize V2 DEX interface."""
        super().__init__(web3_manager, config)
        self.fee = config.get('fee', 3000)  # 0.3% default fee for most V2 DEXs
        self.pair_abi = None
        
        # Checksum addresses
        self.router_address = Web3.to_checksum_address(self.router_address)
        self.factory_address = Web3.to_checksum_address(self.factory_address)

    def initialize(self) -> bool:
        """Initialize the V2 DEX interface."""
        try:
            # Load contract ABIs
            self.router_abi = self.web3_manager.load_abi(f"{self.name.lower()}_router")
            self.factory_abi = self.web3_manager.load_abi(f"{self.name.lower()}_factory")
            self.pair_abi = self.web3_manager.load_abi(f"{self.name.lower()}_pair")
            
            # Initialize contracts with checksummed addresses
            self.router = self.web3_manager.get_contract(
                address=self.router_address,
                abi=self.router_abi
            )
            self.factory = self.web3_manager.get_contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            
            # Initialize contracts
            self.initialized = True
            self.logger.info(f"{self.name} interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "V2 DEX initialization")
            return False

    def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact analysis for V2 pools."""
        try:
            # Validate inputs
            self._validate_path(path)
            self._validate_amounts(amount_in=amount_in)
            
            # Get pair address
            pair_address = self._retry(
                lambda: self.factory.functions.getPair(path[0], path[1]).call(),
                retries=3
            )
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return None
                
            # Get pair contract
            pair = self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pair_address),
                abi=self.pair_abi
            )
            
            # Get reserves
            reserves = self._retry(
                lambda: pair.functions.getReserves().call(),
                retries=3
            )
            token0 = self._retry(
                lambda: pair.functions.token0().call(),
                retries=3
            )
            
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
            amount_out = self._get_amount_out(
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

    def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,  # This parameter is ignored - we always use web3_manager's wallet
        deadline: int
    ) -> TxReceipt:
        """Execute a V2 swap."""
        try:
            # Use provided recipient address
            recipient = to
            self.logger.info(f"Using provided recipient address: {recipient}")
            
            # Validate inputs
            self._validate_path(path)
            self._validate_amounts(amount_in, amount_out_min)
            
            # Get initial balances
            token_in_contract = self.web3_manager.get_token_contract(path[0])
            token_out_contract = self.web3_manager.get_token_contract(path[-1])
            
            balance_in_before = token_in_contract.functions.balanceOf(recipient).call()
            balance_out_before = token_out_contract.functions.balanceOf(recipient).call()
            
            # Get quote for gas estimation
            quote = self.get_quote_with_impact(amount_in, path)
            if not quote:
                raise Exception("Failed to get quote for swap")
            
            # Execute swap using web3_manager
            receipt = self.web3_manager.build_and_send_transaction(
                self.router,
                'swapExactTokensForTokens',
                amount_in,
                amount_out_min,
                path,
                recipient,  # Use our wallet address
                deadline,
                value=0,  # No ETH value for token swaps
                gas=int(quote['estimated_gas'] * 1.2),  # V2 needs 20% more gas than estimate
                maxFeePerGas=None,  # Let web3_manager handle EIP-1559 params
                maxPriorityFeePerGas=None  # Let web3_manager handle EIP-1559 params
            )
            
            if not receipt:
                self.logger.error("No receipt returned from transaction")
                return None
            
            if receipt and receipt['status'] == 1:
                # Get balances after trade
                balance_in_after = token_in_contract.functions.balanceOf(recipient).call()
                balance_out_after = token_out_contract.functions.balanceOf(recipient).call()
                
                # Verify balance changes
                in_diff = balance_in_before - balance_in_after
                out_diff = balance_out_after - balance_out_before
                
                if in_diff <= 0 or out_diff <= 0:
                    self.logger.error(
                        f"Balance verification failed: in_diff={in_diff}, "
                        f"out_diff={out_diff}, expected_min_out={amount_out_min}"
                    )
                    return None
                
                # Log transaction
                self._log_transaction(
                    receipt['transactionHash'].hex(),
                    amount_in,
                    out_diff,  # Use actual output amount
                    path
                )
                
                return receipt
            else:
                self.logger.error("Transaction failed or returned invalid receipt")
                return None
            
        except Exception as e:
            self._handle_error(e, "V2 swap execution")
            return None

    def _get_amount_out(
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

    def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24h trading volume for a token pair."""
        try:
            # Get pair address
            pair_address = self._retry(
                lambda: self.factory.functions.getPair(token0, token1).call(),
                retries=3
            )
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return Decimal('0')
                
            # Get pair contract
            pair = self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pair_address),
                abi=self.pair_abi
            )
            
            # Get reserves
            reserves = self._retry(
                lambda: pair.functions.getReserves().call(),
                retries=3
            )
            
            # Calculate volume (simplified - actual implementation would track events)
            volume = Decimal(str(reserves[0] + reserves[1]))
            return volume
            
        except Exception as e:
            self.logger.error(f"Failed to get 24h volume: {e}")
            return Decimal('0')

    def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        try:
            # Get all pairs (simplified - actual implementation would track all pairs)
            total_liquidity = Decimal('0')
            return total_liquidity
            
        except Exception as e:
            self.logger.error(f"Failed to get total liquidity: {e}")
            return Decimal('0')

    def get_token_price(self, token_address: str) -> float:
        """Get current token price."""
        try:
            # Get WETH address from config
            weth_address = self.config.get('weth_address')
            if not weth_address:
                raise ValueError("WETH address not configured")
            
            # Get pair address
            pair_address = self._retry(
                lambda: self.factory.functions.getPair(token_address, weth_address).call(),
                retries=3
            )
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return 0.0
                
            # Get pair contract
            pair = self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pair_address),
                abi=self.pair_abi
            )
            
            # Get reserves
            reserves = self._retry(
                lambda: pair.functions.getReserves().call(),
                retries=3
            )
            token0 = self._retry(
                lambda: pair.functions.token0().call(),
                retries=3
            )
            
            # Determine which reserve corresponds to which token
            if token_address.lower() == token0.lower():
                token_reserve = reserves[0]
                weth_reserve = reserves[1]
            else:
                token_reserve = reserves[1]
                weth_reserve = reserves[0]
            
            if token_reserve == 0 or weth_reserve == 0:
                return 0.0
                
            # Calculate price in WETH
            price = weth_reserve / token_reserve
            return float(price)
            
        except Exception as e:
            self.logger.error(f"Failed to get token price: {e}")
            return 0.0
