"""Base class for V3 DEX implementations."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal
import time
from web3 import Web3

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
        self._enabled = config.get('enabled', False)
        
        # Checksum addresses
        if self.router_address:
            self.router_address = Web3.to_checksum_address(self.router_address)
        if self.factory_address:
            self.factory_address = Web3.to_checksum_address(self.factory_address)
        if self.quoter_address:
            self.quoter_address = Web3.to_checksum_address(self.quoter_address)

    async def initialize(self) -> bool:
        """Initialize the V3 DEX interface."""
        try:
            # Initialize contracts with checksummed addresses
            self.router = self.web3_manager.get_contract(
                address=self.router_address,
                abi_name=self.name.lower() + "_v3_router"
            )
            self.factory = self.web3_manager.get_contract(
                address=self.factory_address,
                abi_name=self.name.lower() + "_v3_factory"
            )
            if self.quoter_address:
                self.quoter = self.web3_manager.get_contract(
                    address=self.quoter_address,
                    abi_name=self.name.lower() + "_v3_quoter"
                )
            
            # Test connection by checking if contracts are deployed
            code = self._retry_sync(
                lambda: self.web3_manager.w3.eth.get_code(self.router_address)
            )
            if len(code) <= 2:  # Empty or just '0x'
                raise ValueError("No contract deployed at router address %s", self.router_address)
                
            code = self._retry_sync(
                lambda: self.web3_manager.w3.eth.get_code(self.factory_address)
            )
            if len(code) <= 2:
                raise ValueError("No contract deployed at factory address %s", self.factory_address)
                
            if self.quoter_address:
                code = self._retry_sync(
                    lambda: self.web3_manager.w3.eth.get_code(self.quoter_address)
                )
                if len(code) <= 2:
                    raise ValueError("No contract deployed at quoter address %s", self.quoter_address)
                
            self.initialized = True
            self.logger.info("%s V3 interface initialized", self.name)
            return True
            
        except Exception as e:
            self._handle_error(e, "V3 DEX initialization")
            return False

    async def get_token_price(self, token_address: str) -> float:
        """Get current price for a token."""
        try:
            # Convert addresses to checksum format
            token_address = Web3.to_checksum_address(token_address)
            weth_address = Web3.to_checksum_address(self.config.get('weth_address'))
            
            # For V3, use the quoter if available
            if self.quoter and token_address != weth_address:
                if not self.config.get('weth_address'):
                    raise ValueError("WETH address not configured")
                
                # Get quote for 1 token worth of WETH
                amount_in = 10**18  # 1 WETH
                quote = self.get_quote_from_quoter(
                    amount_in,
                    [weth_address, token_address]
                )
                
                if quote:
                    return float(quote) / (10**18)
            
            return 0.0
            
        except Exception as e:
            self.logger.error("Failed to get token price: %s", str(e))
            return 0.0

    async def get_quote_with_impact(self, amount_in: int, path: List[str]) -> Optional[Dict[str, Any]]:
        """Get quote including price impact and liquidity depth analysis."""
        try:
            amount_out = self.get_quote_from_quoter(amount_in, path)
            if not amount_out:
                return None

            # Calculate price impact
            small_amount = 10**6  # Use 1 USDC worth as small amount
            base_amount_out = self.get_quote_from_quoter(small_amount, path)
            if not base_amount_out:
                return None

            # Calculate price impact
            expected_amount = (amount_in * base_amount_out) / small_amount
            actual_amount = amount_out
            price_impact = abs(1 - (actual_amount / expected_amount))

            # Get pool liquidity
            pool_address = self._retry_sync(
                lambda: self.factory.functions.getPool(
                    Web3.to_checksum_address(path[0]),
                    Web3.to_checksum_address(path[1]),
                    self.fee
                ).call()
            )
            
            pool = self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pool_address),
                abi_name=self.name.lower() + "_v3_pool"
            )
            
            liquidity = self._retry_sync(
                lambda: pool.functions.liquidity().call()
            )

            return {
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price_impact': float(price_impact),
                'liquidity_depth': float(liquidity),
                'fee_rate': self.fee / 10000,  # Convert to percentage
                'estimated_gas': 200000,  # Estimated gas for V3 swap
                'min_out': int(amount_out * 0.995)  # 0.5% slippage
            }

        except Exception as e:
            self.logger.error("Failed to get quote with impact: %s", str(e))
            return None

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
        """Execute a token swap."""
        try:
            # Validate parameters
            self._validate_path(path)
            self._validate_amounts(amount_in, amount_out_min)
            
            # Encode path with fees
            encoded_path = self._encode_path(path)
            
            # Build transaction parameters
            params = {
                'from': self.web3_manager.wallet_address,
                'nonce': await self.web3_manager.w3.eth.get_transaction_count(
                    self.web3_manager.wallet_address
                )
            }
            
            # Add gas parameters if provided
            if gas:
                params['gas'] = gas
            if maxFeePerGas:
                params['maxFeePerGas'] = maxFeePerGas
            if maxPriorityFeePerGas:
                params['maxPriorityFeePerGas'] = maxPriorityFeePerGas
            
            # Build and send transaction
            tx_hash = await self.web3_manager.build_and_send_transaction(
                self.router,
                'exactInput',
                {
                    'path': encoded_path,
                    'recipient': Web3.to_checksum_address(to),
                    'deadline': deadline,
                    'amountIn': amount_in,
                    'amountOutMinimum': amount_out_min
                },
                tx_params=params
            )
            
            # Wait for transaction receipt
            receipt = await self.web3_manager.wait_for_transaction(tx_hash)
            
            # Log transaction details
            self._log_transaction(
                receipt['transactionHash'].hex(),
                amount_in,
                amount_out_min,
                path,
                to
            )
            
            return receipt
            
        except Exception as e:
            self._handle_error(e, "V3 swap_exact_tokens_for_tokens")
            raise

    def get_quote_from_quoter(self, amount_in: int, path: List[str]) -> Optional[int]:
        """Get quote from quoter contract if available."""
        if not self.quoter:
            return None

        # Only support direct swaps for now
        if len(path) != 2:
            self.logger.warning("Multi-hop paths not supported yet")
            return None

        try:
            # Use quoteExactInputSingle
            result = self._retry_sync(
                lambda: self.quoter.functions.quoteExactInputSingle(
                    Web3.to_checksum_address(path[0]),  # tokenIn
                    Web3.to_checksum_address(path[1]),  # tokenOut
                    self.fee,  # fee
                    amount_in,  # amountIn
                    0  # sqrtPriceLimitX96 (0 for no limit)
                ).call()
            )
            # Return just the amount_out from the tuple
            return result[0] if result else None

        except Exception as e:
            self.logger.error("Failed to get quote: %s", str(e))
            return None

    def _encode_path(self, path: List[str], fee: Optional[int] = None) -> bytes:
        """Encode path with fees for V3 swap."""
        encoded = b''
        for i in range(len(path) - 1):
            # Convert to checksum address and remove '0x' prefix
            token_addr = Web3.to_checksum_address(path[i])[2:]
            encoded += bytes.fromhex(token_addr)
            encoded += (fee if fee is not None else self.fee).to_bytes(3, 'big')  # Add fee as 3 bytes
        encoded += bytes.fromhex(Web3.to_checksum_address(path[-1])[2:])  # Add final token
        return encoded

    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        try:
            # Validate and checksum addresses
            token0 = Web3.to_checksum_address(token0)
            token1 = Web3.to_checksum_address(token1)
            
            # Get pool address using V3 factory method
            pool_address = self._retry_sync(
                lambda: self.factory.functions.getPool(
                    token0,
                    token1,
                    self.fee
                ).call()
            )
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return Decimal(0)
            
            # Get pool contract with checksummed address
            pool = self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pool_address),
                abi_name=self.name.lower() + "_v3_pool"
            )
            
            # Get volume from Swap events in last 24h
            current_block = self.web3_manager.w3.eth.block_number
            from_block = current_block - 7200  # ~24h of blocks
            
            swap_filter = pool.events.Swap.create_filter(fromBlock=from_block)
            swap_events = self._retry_sync(
                lambda: swap_filter.get_all_entries()
            )
            
            volume = Decimal(0)
            for event in swap_events:
                amount0 = abs(Decimal(event['args']['amount0']))
                amount1 = abs(Decimal(event['args']['amount1']))
                volume += max(amount0, amount1)
            
            return volume
            
        except Exception as e:
            self.logger.error("Failed to get 24h volume: %s", str(e))
            return Decimal(0)

    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        try:
            total_liquidity = Decimal(0)
            
            # Get pools from PoolCreated events
            pool_created_filter = self.factory.events.PoolCreated.create_filter(fromBlock=0)
            events = self._retry_sync(
                lambda: pool_created_filter.get_all_entries()
            )
            
            # Limit to most recent 100 pools for performance
            for event in events[-100:]:
                try:
                    pool_address = Web3.to_checksum_address(event['args']['pool'])
                    pool = self.web3_manager.get_contract(
                        address=pool_address,
                        abi_name=self.name.lower() + "_v3_pool"
                    )
                    
                    # Get liquidity
                    liquidity = self._retry_sync(
                        lambda: pool.functions.liquidity().call()
                    )
                    total_liquidity += Decimal(liquidity)
                    
                except Exception as e:
                    self.logger.warning("Failed to get liquidity for pool %s: %s", pool_address, str(e))
                    continue
            
            return total_liquidity
            
        except Exception as e:
            self.logger.error("Failed to get total liquidity: %s", str(e))
            return Decimal(0)
