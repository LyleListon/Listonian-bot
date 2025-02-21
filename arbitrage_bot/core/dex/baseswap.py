"""BaseSwap DEX implementation."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal
from web3 import Web3
import asyncio

from .base_dex_v2 import BaseDEXV2
from ..web3.web3_manager import Web3Manager

class BaseSwap(BaseDEXV2):
    """BaseSwap DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize BaseSwap interface."""
        super().__init__(web3_manager, config)
        self._enabled = config.get('enabled', False)

    async def is_enabled(self) -> bool:
        """Check if DEX is enabled."""
        return self._enabled

    async def initialize(self) -> bool:
        """Initialize the BaseSwap interface."""
        try:
            # Initialize contracts with checksummed addresses
            self.router = self.web3_manager.get_contract(
                address=self.router_address,
                abi_name="baseswap_router"
            )
            self.factory = self.web3_manager.get_contract(
                address=self.factory_address,
                abi_name="baseswap_factory"
            )
            
            # Validate contracts are working
            try:
                # Test factory contract
                await self.web3_manager.call_contract_function(
                    self.factory.functions.allPairsLength
                )
                
                # Test router contract
                await self.web3_manager.call_contract_function(
                    self.router.functions.factory
                )
                
                self.initialized = True
                self.logger.info("%s interface initialized successfully", self.name)
                return True
                
            except Exception as e:
                self.logger.error("Contract validation failed: %s", str(e))
                self.initialized = False
                return False
            
        except Exception as e:
            self._handle_error(e, "BaseSwap initialization")
            return False

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int,
        gas: Optional[int] = None,
        maxFeePerGas: Optional[int] = None,
        maxPriorityFeePerGas: Optional[int] = None
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
            balance_in_before = await self.web3_manager.call_contract_function(
                token_in.functions.balanceOf, recipient
            )
            balance_out_before = await self.web3_manager.call_contract_function(
                token_out.functions.balanceOf, recipient
            )
            
            # Check allowance and approve if needed
            allowance = await self.web3_manager.call_contract_function(
                token_in.functions.allowance,
                recipient,
                self.router_address
            )
            
            if allowance < amount_in:
                self.logger.info("Approving %s for router %s", path[0], self.router_address)
                approve_tx = self.web3_manager.build_and_send_transaction(
                    token_in,
                    'approve',
                    self.router_address,
                    amount_in * 2  # Double for future use
                )
                if not approve_tx or approve_tx['status'] != 1:
                    raise Exception("Token approval failed")
            
            # Get quote for gas estimation
            quote = await self.get_quote_with_impact(amount_in, path)
            if not quote:
                raise Exception("Failed to get quote for swap")
            
            # Calculate gas limit
            gas_limit = gas or int(quote['estimated_gas'] * 1.2)  # 20% buffer if not specified
            
            # Get gas parameters if not provided
            if not all([maxFeePerGas, maxPriorityFeePerGas]):
                block = await self.web3_manager.get_block('latest')
                maxFeePerGas = maxFeePerGas or block['baseFeePerGas'] * 2
                maxPriorityFeePerGas = maxPriorityFeePerGas or await self.web3_manager.get_max_priority_fee()
            
            # Execute swap
            receipt = await self.web3_manager.build_and_send_transaction(
                self.router,
                'swapExactTokensForTokens',
                amount_in,
                amount_out_min,
                path,
                recipient,
                deadline,
                value=0,  # No ETH value for token swaps
                gas=gas_limit,
                maxFeePerGas=maxFeePerGas,
                maxPriorityFeePerGas=maxPriorityFeePerGas
            )
            
            if receipt and receipt['status'] == 1:
                # Verify balance changes
                balance_in_after = await self.web3_manager.call_contract_function(
                    token_in.functions.balanceOf, recipient
                )
                balance_out_after = await self.web3_manager.call_contract_function(
                    token_out.functions.balanceOf, recipient
                )
                
                in_diff = balance_in_before - balance_in_after
                out_diff = balance_out_after - balance_out_before
                
                if in_diff <= 0 or out_diff <= 0:
                    raise Exception(
                        "Balance verification failed: in_diff=%s, out_diff=%s, expected_min_out=%s" % (
                            in_diff, out_diff, amount_out_min
                        )
                    )
                
                self.logger.info(
                    "Swap successful:\n"
                    "  In: %s %s\n"
                    "  Out: %s %s\n"
                    "  Gas Used: %s",
                    in_diff, path[0],
                    out_diff, path[-1],
                    receipt['gasUsed']
                )
                
                return receipt
            else:
                raise Exception("Swap transaction failed")
            
        except Exception as e:
            self.logger.error("Swap failed: %s", str(e))
            raise

    async def get_token_price(self, token_address: str) -> float:
        """Get current token price."""
        try:
            # If token is WETH, return 1.0 since price is in WETH
            if token_address.lower() == self.weth_address.lower():
                return 1.0

            # Get pair address
            pair_address = await self._retry_async(
                self.web3_manager.call_contract_function,
                self.factory.functions.getPair,
                token_address,
                self.weth_address,
                retries=3
            )
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return 0.0
                
            # Get pair contract
            pair = self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pair_address),
                abi_name="baseswap_pair"
            )
            
            # Get reserves and token0 concurrently
            reserves, token0 = await asyncio.gather(
                self._retry_async(
                    self.web3_manager.call_contract_function,
                    pair.functions.getReserves,
                    retries=3
                ),
                self._retry_async(
                    self.web3_manager.call_contract_function,
                    pair.functions.token0,
                    retries=3
                )
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
            self.logger.error("Failed to get token price: %s", str(e))
            return 0.0

    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24h trading volume for a token pair."""
        try:
            # Get pair address
            pair_address = await self._retry_async(
                self.web3_manager.call_contract_function,
                self.factory.functions.getPair,
                token0,
                token1,
                retries=3
            )
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return Decimal('0')
                
            # Get pair contract
            pair = self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pair_address),
                abi_name="baseswap_pair"
            )
            
            # Get reserves
            reserves = await self._retry_async(
                self.web3_manager.call_contract_function,
                pair.functions.getReserves,
                retries=3
            )
            
            # Calculate volume (simplified - actual implementation would track events)
            volume = Decimal(str(reserves[0] + reserves[1]))
            return volume
            
        except Exception as e:
            self.logger.error("Failed to get 24h volume: %s", str(e))
            return Decimal('0')

    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        try:
            # Get total pairs count
            pair_count = await self._retry_async(
                self.web3_manager.call_contract_function,
                self.factory.functions.allPairsLength,
                retries=3
            )
            
            total_liquidity = Decimal('0')
            
            # Sample first 100 pairs for efficiency
            sample_size = min(100, pair_count)
            for i in range(sample_size):
                try:
                    # Get pair address
                    pair_address = await self._retry_async(
                        self.web3_manager.call_contract_function,
                        self.factory.functions.allPairs,
                        i,
                        retries=3
                    )
                    
                    # Get pair contract
                    pair = self.web3_manager.get_contract(
                        address=Web3.to_checksum_address(pair_address),
                        abi_name="baseswap_pair"
                    )
                    
                    # Get reserves
                    reserves = await self._retry_async(
                        self.web3_manager.call_contract_function,
                        pair.functions.getReserves,
                        retries=3
                    )
                    
                    # Add to total (simplified - actual implementation would convert to common currency)
                    total_liquidity += Decimal(str(reserves[0] + reserves[1]))
                    
                except Exception as e:
                    self.logger.debug("Error getting liquidity for pair %s: %s", i, str(e))
                    continue
            
            # Extrapolate total based on sample
            if sample_size < pair_count:
                total_liquidity = total_liquidity * Decimal(str(pair_count / sample_size))
            
            return total_liquidity
            
        except Exception as e:
            self.logger.error("Failed to get total liquidity: %s", str(e))
            return Decimal('0')

    async def get_supported_tokens(self) -> List[str]:
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
                    pair_address = await self._retry_async(
                        self.web3_manager.call_contract_function,
                        self.factory.functions.getPair,
                        token_address,
                        self.weth_address,
                        retries=3
                    )
                    
                    if pair_address != "0x0000000000000000000000000000000000000000":
                        # Add token if pair exists
                        supported_tokens.add(token_address)
                        self.logger.debug("Found active pair for %s", token_address)
                        
                except Exception as e:
                    self.logger.debug("Error checking pair for %s: %s", token_address, str(e))
                    continue
            
            return list(supported_tokens)
        except Exception as e:
            self.logger.error("Failed to get supported tokens: %s", str(e))
            return []
