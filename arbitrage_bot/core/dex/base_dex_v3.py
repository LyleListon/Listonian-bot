"""Base class for V3 DEX implementations."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal
import eventlet
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
        
        # Checksum addresses
        if self.router_address:
            self.router_address = Web3.to_checksum_address(self.router_address)
        if self.factory_address:
            self.factory_address = Web3.to_checksum_address(self.factory_address)
        if self.quoter_address:
            self.quoter_address = Web3.to_checksum_address(self.quoter_address)

    def initialize(self) -> bool:
        """Initialize the V3 DEX interface."""
        try:
            # Load contract ABIs
            self.router_abi = self.web3_manager.load_abi(f"{self.name.lower()}_v3_router")
            self.factory_abi = self.web3_manager.load_abi(f"{self.name.lower()}_v3_factory")
            self.pool_abi = self.web3_manager.load_abi(f"{self.name.lower()}_v3_pool")
            if self.quoter_address:
                self.quoter_abi = self.web3_manager.load_abi(f"{self.name.lower()}_v3_quoter")
            
            # Initialize contracts with checksummed addresses
            self.router = self.web3_manager.get_contract(
                address=self.router_address,
                abi=self.router_abi
            )
            self.factory = self.web3_manager.get_contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            if self.quoter_address:
                self.quoter = self.web3_manager.get_contract(
                    address=self.quoter_address,
                    abi=self.quoter_abi
                )
            
            # Test connection by checking if contracts are deployed
            code = self._retry_sync(
                lambda: self.web3_manager.w3.eth.get_code(self.router_address)
            )
            if len(code) <= 2:  # Empty or just '0x'
                raise ValueError(f"No contract deployed at router address {self.router_address}")
                
            code = self._retry_sync(
                lambda: self.web3_manager.w3.eth.get_code(self.factory_address)
            )
            if len(code) <= 2:
                raise ValueError(f"No contract deployed at factory address {self.factory_address}")
                
            if self.quoter_address:
                code = self._retry_sync(
                    lambda: self.web3_manager.w3.eth.get_code(self.quoter_address)
                )
                if len(code) <= 2:
                    raise ValueError(f"No contract deployed at quoter address {self.quoter_address}")
                
            self.initialized = True
            self.logger.info(f"{self.name} V3 interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "V3 DEX initialization")
            return False

    def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,  # This parameter is ignored - we always use web3_manager's wallet
        deadline: int
    ) -> TxReceipt:
        """Execute a V3 swap using exactInput."""
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
            
            balance_in_before = token_in_contract.functions.balanceOf(self.web3_manager.wallet_address).call()
            balance_out_before = token_out_contract.functions.balanceOf(recipient).call()
            
            # Check and approve token spending
            if not self.check_and_approve_token(path[0], amount_in):
                self.logger.error(
                    f"Failed to approve token {path[0]} for spending"
                )
                return None
            
            # Prepare swap parameters
            # Get quote to find best fee tier
            quote = self.get_quote_with_impact(amount_in, path)
            if not quote:
                self.logger.error("Failed to get quote for swap")
                return None
                
            # Use fee from successful quote
            params = self._prepare_exact_input_params(
                amount_in,
                amount_out_min,
                path,
                recipient,  # Use our wallet address
                deadline
            )
            params['path'] = self._encode_path(path, int(quote['fee_rate'] * 1000000))  # Convert fee back to basis points
            
            # Build function parameters
            function_params = (
                params['path'],
                params['recipient'],
                params['deadline'],
                params['amountIn'],
                params['amountOutMinimum']
            )
            
            # Execute swap with proper transaction parameters
            receipt = self.web3_manager.build_and_send_transaction(
                contract=self.router,
                method_name='exactInput',
                *function_params,
                value=0,  # No ETH value for token swaps
                gas=int(quote['estimated_gas'] * 1.1),  # Use quote's gas estimate with 10% buffer
                maxFeePerGas=None,  # Let web3_manager handle EIP-1559 params
                maxPriorityFeePerGas=None  # Let web3_manager handle EIP-1559 params
            )
            
            if receipt and receipt['status'] == 1:
                # Get balances after trade
                balance_in_after = token_in_contract.functions.balanceOf(self.web3_manager.wallet_address).call()
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
            self._handle_error(e, "V3 swap execution")
            return None

    def _prepare_exact_input_params(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int
    ) -> Dict[str, Any]:
        """Prepare parameters for V3 exactInput swap."""
        # Validate inputs
        self._validate_path(path)
        self._validate_amounts(amount_in, amount_out_min)
        
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

    def get_quote_from_quoter(self, amount_in: int, path: List[str]) -> Optional[int]:
        """Get quote from quoter contract if available."""
        if not self.quoter:
            return None
            
        encoded_path = self._encode_path(path)
        return self._retry_sync(
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

    def get_24h_volume(self, token0: str, token1: str) -> Decimal:
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
                abi=self.pool_abi
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
            self.logger.error(f"Failed to get 24h volume: {e}")
            return Decimal(0)

    def get_total_liquidity(self) -> Decimal:
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
                        abi=self.pool_abi
                    )
                    
                    # Get liquidity
                    liquidity = self._retry_sync(
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

    def _retry_sync(self, func, retries=3, delay=1):
        """Synchronous retry helper."""
        last_error = None
        for attempt in range(retries):
            try:
                return func()
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    eventlet.sleep(delay * (2 ** attempt))  # Exponential backoff
                    continue
                self.logger.error(f"Failed after {retries} attempts: {e}")
                raise last_error
        return None

    def get_token_price(self, token_address: str) -> float:
        """Get current price for a token."""
        try:
            # For V3, use the quoter if available
            if self.quoter and token_address != self.config.get('weth_address'):
                weth_address = self.config.get('weth_address')
                if not weth_address:
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
            self.logger.error(f"Failed to get token price: {e}")
            return 0.0
