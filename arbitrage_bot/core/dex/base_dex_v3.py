"""Base class for V3 DEX implementations."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal

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
            self.router_abi = self.web3_manager.load_abi(f"{self.name.lower()}_v3_router")
            self.factory_abi = self.web3_manager.load_abi(f"{self.name.lower()}_v3_factory")
            self.pool_abi = self.web3_manager.load_abi(f"{self.name.lower()}_v3_pool")
            if self.quoter_address:
                self.quoter_abi = self.web3_manager.load_abi(f"{self.name.lower()}_v3_quoter")
            
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
            
            # Test connection by checking if contracts are deployed
            code = await self._retry_async(
                lambda: self.w3.eth.get_code(self.router_address)
            )
            if len(code) <= 2:  # Empty or just '0x'
                raise ValueError(f"No contract deployed at router address {self.router_address}")
                
            code = await self._retry_async(
                lambda: self.w3.eth.get_code(self.factory_address)
            )
            if len(code) <= 2:
                raise ValueError(f"No contract deployed at factory address {self.factory_address}")
                
            if self.quoter_address:
                code = await self._retry_async(
                    lambda: self.w3.eth.get_code(self.quoter_address)
                )
                if len(code) <= 2:
                    raise ValueError(f"No contract deployed at quoter address {self.quoter_address}")
                
            self.initialized = True
            self.logger.info(f"{self.name} V3 interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "V3 DEX initialization")
            return False

    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        try:
            total_liquidity = Decimal(0)
            
            # Get pools from PoolCreated events
            pool_created_filter = self.factory.events.PoolCreated.create_filter(fromBlock=0)
            events = await self._retry_async(
                lambda: pool_created_filter.get_all_entries()
            )
            
            # Limit to most recent 100 pools for performance
            for event in events[-100:]:
                try:
                    pool_address = event['args']['pool']
                    pool = await self.web3_manager.get_contract_async(
                        address=pool_address,
                        abi=self.pool_abi
                    )
                    
                    # Get liquidity
                    liquidity = await self._retry_async(
                        lambda: pool.functions.liquidity().call()
                    )
                    total_liquidity += Decimal(liquidity)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get liquidity for pool {pool_address}: {e}")
                    continue
            
            return total_liquidity
            
        except Exception as e:
            self.logger.error(f"Failed to get total liquidity: {e}")
            return Decimal(0)

    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        try:
            # Get pool address using V3 factory method
            pool_address = await self._retry_async(
                lambda: self.factory.functions.getPool(
                    token0,
                    token1,
                    self.fee
                ).call()
            )
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return Decimal(0)
            
            # Get pool contract
            pool = await self.web3_manager.get_contract_async(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Get volume from Swap events in last 24h
            current_block = await self.web3_manager.w3.eth.block_number
            from_block = current_block - 7200  # ~24h of blocks
            
            swap_filter = pool.events.Swap.create_filter(fromBlock=from_block)
            swap_events = await self._retry_async(
                lambda: swap_filter.get_all_entries()
            )
            
            volume = Decimal(0)
            for event in swap_events:
                amount0 = abs(Decimal(event['args']['amount0']))
                amount1 = abs(Decimal(event['args']['amount1']))
                volume += max(amount0, amount1)
            
            return volume
            
        except Exception as e:
            self.logger.error(f"Failed to get 24h volume: {e}")
            return Decimal(0)

    async def _prepare_exact_input_params(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int
    ) -> TxReceipt:
        """Prepare parameters for V3 exactInput swap."""
        # Validate inputs
        await self._validate_path(path)
        await self._validate_amounts(amount_in, amount_out_min)
        
        # Encode the path with fees
        encoded_path = self._encode_path(path)
        
        # Build exact input params struct
        return {
            'path': encoded_path,
            'recipient': to,
            'deadline': deadline,
            'amountIn': amount_in,
            'amountOutMinimum': amount_out_min
        }

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int
    ) -> TxReceipt:
        """Execute a V3 swap using exactInput."""
        try:
            # Prepare swap parameters
            params = await self._prepare_exact_input_params(
                amount_in,
                amount_out_min,
                path,
                to,
                deadline
            )
            
            # Build transaction
            tx = await self.router.functions.exactInput((params,)).build_transaction({
                'from': to,
                'gas': 350000,  # V3 needs more gas
                'nonce': await self.w3.eth.get_transaction_count(to)
            })
            
            # Sign and send transaction
            signed_tx = await self._retry_async(lambda: self.w3.eth.account.sign_transaction(
                tx,
                private_key=self.config.get('wallet', {}).get('private_key')
            ))
            tx_hash = await self._retry_async(lambda: self.w3.eth.send_raw_transaction(
                signed_tx.rawTransaction
            ))
            
            # Wait for receipt
            receipt = await self._retry_async(
                lambda: self.w3.eth.wait_for_transaction_receipt(tx_hash)
            )
            
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
            raise

    async def get_quote_from_quoter(self, amount_in: int, path: List[str]) -> Optional[int]:
        """Get quote from quoter contract if available."""
        if not self.quoter:
            return None
            
        encoded_path = self._encode_path(path)
        return await self._retry_async(
            lambda: self.quoter.functions.quoteExactInput(
                encoded_path,
                amount_in
            ).call()
        )

    def _encode_path(self, path: List[str]) -> bytes:
        """Encode path with fees for V3 swap."""
        encoded = b''
        for i in range(len(path) - 1):
            encoded += bytes.fromhex(path[i][2:])  # Remove '0x' prefix
            encoded += self.fee.to_bytes(3, 'big')  # Add fee as 3 bytes
        encoded += bytes.fromhex(path[-1][2:])  # Add final token
        return encoded

    async def get_best_path(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        max_hops: int = 2
    ) -> Optional[Dict[str, Any]]:
        """Find best trading path between tokens."""
        try:
            if not self.initialized:
                raise ValueError("DEX not initialized")

            # Try quoter first if available
            direct_amount_out = None
            if self.quoter:
                try:
                    direct_amount_out = await self.get_quote_from_quoter(
                        amount_in,
                        [token_in, token_out]
                    )
                except Exception as e:
                    self.logger.debug(f"Quoter failed, falling back to pool state: {e}")
            
            # Fall back to pool state if quoter fails
            if direct_amount_out is None:
                direct_quote = await self.get_quote_with_impact(
                    amount_in=amount_in,
                    path=[token_in, token_out]
                )
                if not direct_quote:
                    return None
                direct_amount_out = direct_quote['amount_out']

            if direct_amount_out:
                return {
                    'path': [token_in, token_out],
                    'amounts': [amount_in, direct_amount_out],
                    'fees': [self.fee],
                    'price_impact': await self._get_price_impact(
                        token_in,
                        token_out,
                        amount_in,
                        direct_amount_out
                    )
                }

            # If direct path fails and max_hops > 1, try common intermediary tokens
            if max_hops > 1:
                intermediaries = ['WETH', 'USDC', 'USDT', 'DAI']
                best_quote = None
                best_amount_out = 0

                for mid_token in intermediaries:
                    mid_address = self.config.get('tokens', {}).get(mid_token, {}).get('address')
                    if not mid_address:
                        continue

                    # Try path through intermediary
                    try:
                        # Get first hop quote
                        first_amount_out = None
                        if self.quoter:
                            try:
                                first_amount_out = await self.get_quote_from_quoter(
                                    amount_in,
                                    [token_in, mid_address]
                                )
                            except Exception:
                                pass
                        
                        if first_amount_out is None:
                            first_quote = await self.get_quote_with_impact(
                                amount_in=amount_in,
                                path=[token_in, mid_address]
                            )
                            if not first_quote:
                                continue
                            first_amount_out = first_quote['amount_out']

                        # Get second hop quote
                        second_amount_out = None
                        if self.quoter:
                            try:
                                second_amount_out = await self.get_quote_from_quoter(
                                    first_amount_out,
                                    [mid_address, token_out]
                                )
                            except Exception:
                                pass

                        if second_amount_out is None:
                            second_quote = await self.get_quote_with_impact(
                                amount_in=first_amount_out,
                                path=[mid_address, token_out]
                            )
                            if not second_quote:
                                continue
                            second_amount_out = second_quote['amount_out']
                            
                        if second_amount_out > best_amount_out:
                            best_amount_out = second_amount_out
                            total_impact = await self._get_price_impact(
                                token_in,
                                token_out,
                                amount_in,
                                second_amount_out
                            )
                            
                            if total_impact is None:
                                total_impact = 1.0  # Default to high impact
                            
                            best_quote = {
                                'path': [token_in, mid_address, token_out],
                                'amounts': [
                                    amount_in,
                                    first_amount_out,
                                    second_amount_out
                                ],
                                'fees': [self.fee, self.fee],
                                'price_impact': total_impact
                            }
                    except Exception as e:
                        self.logger.debug(f"Failed to check path through {mid_token}: {e}")
                        continue

                return best_quote

            return None

        except Exception as e:
            self._handle_error(e, "Finding best V3 path")
            return None

    async def _get_price_impact(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        amount_out: int
    ) -> Optional[float]:
        """Calculate price impact for a trade."""
        try:
            # Get pool address
            pool_address = await self._retry_async(
                lambda: self.factory.functions.getPool(
                    token_in,
                    token_out,
                    self.fee
                ).call()
            )

            if pool_address == "0x0000000000000000000000000000000000000000":
                return None

            # Get pool contract
            pool = await self.web3_manager.get_contract_async(
                address=pool_address,
                abi=self.pool_abi
            )

            # Get pool state
            slot0 = await self._retry_async(
                lambda: pool.functions.slot0().call()
            )
            liquidity = await self._retry_async(
                lambda: pool.functions.liquidity().call()
            )

            return self._calculate_price_impact(
                amount_in=amount_in,
                amount_out=amount_out,
                sqrt_price_x96=slot0[0],
                liquidity=liquidity
            )

        except Exception as e:
            self.logger.error(f"Failed to calculate price impact: {e}")
            return None
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
