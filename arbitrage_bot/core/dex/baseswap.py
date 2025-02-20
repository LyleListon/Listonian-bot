"""BaseSwap DEX implementation."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal
from web3 import Web3

from .base_dex_v2 import BaseDEXV2
from ..web3.web3_manager import Web3Manager

class BaseSwap(BaseDEXV2):
    """BaseSwap DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize BaseSwap interface."""
        super().__init__(web3_manager, config)
        self.weth_address = Web3.to_checksum_address(config['weth_address'])

    def initialize(self) -> bool:
        """Initialize the BaseSwap interface."""
        try:
            # Load contract ABIs with correct filenames
            self.router_abi = self.web3_manager.load_abi("baseswap_router")
            self.factory_abi = self.web3_manager.load_abi("baseswap_factory")
            self.pair_abi = self.web3_manager.load_abi("baseswap_pair")
            
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
            self._handle_error(e, "BaseSwap initialization")
            return False

    def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
  # This parameter is ignored - we always use web3_manager's wallet
        deadline: int
    ) -> TxReceipt:
        """Execute a swap."""
        try:
            # Validate inputs
            self._validate_path(path)
            self._validate_amounts(amount_in=amount_in, amount_out_min=amount_out_min)
            
            # Always use web3_manager's wallet address as recipient
            recipient = self.web3_manager.wallet_address
            
            # Get initial balances
            token_in = self.web3_manager.get_token_contract(path[0])
            token_out = self.web3_manager.get_token_contract(path[-1])
            balance_in_before = token_in.functions.balanceOf(recipient).call()
            balance_out_before = token_out.functions.balanceOf(recipient).call()
            
            # Check allowance and approve if needed
            allowance = token_in.functions.allowance(
                recipient,
                self.router_address
            ).call()
            
            if allowance < amount_in:
                self.logger.info(f"Approving {path[0]} for router {self.router_address}")
                approve_tx = self.web3_manager.build_and_send_transaction(
                    token_in,
                    'approve',
                    self.router_address,
                    amount_in * 2  # Double for future use
                )
                if not approve_tx or approve_tx['status'] != 1:
                    raise Exception("Token approval failed")
            
            # Get quote for gas estimation
            quote = self.get_quote_with_impact(amount_in, path)
            if not quote:
                raise Exception("Failed to get quote for swap")
            
            # Execute swap
            receipt = self.web3_manager.build_and_send_transaction(
                self.router,
                'swapExactTokensForTokens',
                amount_in,
                amount_out_min,
                path,
                recipient,
                deadline,
                value=0,  # No ETH value for token swaps
                gas=int(quote['estimated_gas'] * 1.1),  # Use quote's gas estimate with 10% buffer
                maxFeePerGas=None,  # Let web3_manager handle EIP-1559 params
                maxPriorityFeePerGas=None  # Let web3_manager handle EIP-1559 params
            )
            
            if receipt and receipt['status'] == 1:
                # Verify balance changes
                balance_in_after = token_in.functions.balanceOf(recipient).call()
                balance_out_after = token_out.functions.balanceOf(recipient).call()
                
                in_diff = balance_in_before - balance_in_after
                out_diff = balance_out_after - balance_out_before
                
                if in_diff <= 0 or out_diff <= 0:
                    raise Exception(
                        f"Balance verification failed: in_diff={in_diff}, "
                        f"out_diff={out_diff}, expected_min_out={amount_out_min}"
                    )
                
                self.logger.info(
                    f"Swap successful:\n"
                    f"  In: {in_diff} {path[0]}\n"
                    f"  Out: {out_diff} {path[-1]}\n"
                    f"  Gas Used: {receipt['gasUsed']}"
                )
                
                return receipt
            else:
                raise Exception("Swap transaction failed")
            
        except Exception as e:
            self.logger.error(f"Swap failed: {e}")
            raise

    def get_token_price(self, token_address: str) -> float:
        """Get current token price."""
        try:
            # If token is WETH, return 1.0 since price is in WETH
            if token_address.lower() == self.weth_address.lower():
                return 1.0

            # Get pair address
            pair_address = self._retry(
                lambda: self.factory.functions.getPair(token_address, self.weth_address).call(),
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

    def get_supported_tokens(self) -> List[str]:
        """Get list of supported tokens with active pairs."""
        try:
            supported_tokens = set()
            
            # Add WETH as it's always supported
            supported_tokens.add(self.weth_address)
            
            # Check USDC and DAI pairs
            common_tokens = {
                'USDC': self.config['tokens']['USDC']['address'],
                'DAI': self.config['tokens']['DAI']['address']
            }
            
            for token_address in common_tokens.values():
                try:
                    # Get pair address
                    pair_address = self._retry(
                        lambda: self.factory.functions.getPair(
                            token_address,
                            self.weth_address
                        ).call(),
                        retries=3
                    )
                    
                    if pair_address != "0x0000000000000000000000000000000000000000":
                        # Add token if pair exists
                        supported_tokens.add(token_address)
                        self.logger.debug(f"Found active pair for {token_address}")
                        
                except Exception as e:
                    self.logger.debug(f"Error checking pair for {token_address}: {e}")
                    continue
            
            return list(supported_tokens)
        except Exception as e:
            self.logger.error(f"Failed to get supported tokens: {e}")
            return []
