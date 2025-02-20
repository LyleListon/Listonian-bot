"""SwapBased V3 DEX implementation."""

from typing import Dict, Any, List, Optional
from web3.types import TxReceipt
from decimal import Decimal
from web3 import Web3

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager

class SwapBased(BaseDEXV3):
    """SwapBased V3 DEX implementation."""

    # SwapBased V3 fee tiers
    FEE_TIERS = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize SwapBased interface."""
        super().__init__(web3_manager, config)
        self.weth_address = Web3.to_checksum_address(config['weth_address'])
        self.quoter_address = Web3.to_checksum_address(config['quoter'])
        self.fee = config.get('fee', 3000)  # Default to 0.3%

    def initialize(self) -> bool:
        """Initialize the SwapBased interface."""
        try:
            # Load contract ABIs with correct filenames
            self.router_abi = self.web3_manager.load_abi("swapbased_v3_router")
            self.factory_abi = self.web3_manager.load_abi("swapbased_v3_factory")
            self.pool_abi = self.web3_manager.load_abi("swapbased_v3_pool")
            self.quoter_abi = self.web3_manager.load_abi("swapbased_v3_quoter")
            
            # Initialize contracts with checksummed addresses
            self.router = self.web3_manager.get_contract(
                address=self.router_address,
                abi=self.router_abi
            )
            self.factory = self.web3_manager.get_contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            self.quoter = self.web3_manager.get_contract(
                address=self.quoter_address,
                abi=self.quoter_abi
            )
            
            # Initialize contracts
            self.initialized = True
            self.logger.info(f"{self.name} interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "SwapBased initialization")
            return False

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
                    pool_address = self._retry_sync(
                        lambda: self.factory.functions.getPool(
                            path[0],
                            path[1],
                            fee
                        ).call()
                    )
                    
                    if pool_address == "0x0000000000000000000000000000000000000000":
                        self.logger.debug(f"No pool found for fee tier {fee}")
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
                    
                    # Get quote from quoter with current fee tier
                    encoded_path = self._encode_path(path, fee)
                    amount_out = self._retry_sync(
                        lambda: self.quoter.functions.quoteExactInput(
                            encoded_path,
                            amount_in
                        ).call()
                    )
                    if not amount_out:
                        self.logger.debug(f"No quote available for fee tier {fee}")
                        continue
                        
                    # Calculate price impact
                    impact = self._calculate_price_impact(
                        amount_in=amount_in,
                        amount_out=amount_out,
                        sqrt_price_x96=slot0[0],
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
                    self.logger.debug(f"Trying fee tier {fee} for {token_address}")
                    # Get pool address
                    pool_address = self._retry_sync(
                        lambda: self.factory.functions.getPool(
                            token_address,
                            self.weth_address,
                            fee
                        ).call()
                    )
                    
                    if pool_address == "0x0000000000000000000000000000000000000000":
                        self.logger.debug(f"No pool found for fee tier {fee}")
                        continue
                        
                    self.logger.debug(f"Found pool {pool_address} for fee tier {fee}")
                    
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
                        self.logger.debug(f"Zero price for fee tier {fee}")
                        continue
                        
                    # Convert sqrtPriceX96 to price
                    price = (sqrt_price_x96 / (2 ** 96)) ** 2
                    
                    # Adjust for token order
                    token0 = self._retry_sync(
                        lambda: pool.functions.token0().call()
                    )
                    
                    if token_address.lower() == token0.lower():
                        price = 1 / price
                        
                    self.logger.debug(f"Got price {price} for fee tier {fee}")
                    return float(price)
                    
                except Exception as e:
                    self.logger.debug(f"Error getting price for fee tier {fee}: {e}")
                    continue
            
            self.logger.debug("No valid price found in any fee tier")
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to get token price: {e}")
            return 0.0

    def _encode_path(self, path: List[str], fee: int = None) -> bytes:
        """Encode path with fees for V3 swap."""
        encoded = b''
        for i in range(len(path) - 1):
            encoded += bytes.fromhex(path[i][2:])  # Remove '0x' prefix
            encoded += (fee or self.fee).to_bytes(3, 'big')  # Add fee as 3 bytes
        encoded += bytes.fromhex(path[-1][2:])  # Add final token
        return encoded

    def get_supported_tokens(self) -> List[str]:
        """Get list of supported tokens with active pools."""
        try:
            supported_tokens = set()
            
            # Add WETH as it's always supported
            supported_tokens.add(self.weth_address)
            
            # Get tokens from active pools
            for fee in self.FEE_TIERS:
                try:
                    # Get pool address for WETH pairs
                    pool_address = self._retry_sync(
                        lambda: self.factory.functions.getPool(
                            self.config['tokens']['USDC']['address'],
                            self.weth_address,
                            fee
                        ).call()
                    )
                    
                    if pool_address != "0x0000000000000000000000000000000000000000":
                        # Add USDC if pool exists
                        supported_tokens.add(self.config['tokens']['USDC']['address'])
                        
                        # Get pool contract
                        pool = self.web3_manager.get_contract(
                            address=Web3.to_checksum_address(pool_address),
                            abi=self.pool_abi
                        )
                        
                except Exception as e:
                    self.logger.debug(f"Error checking fee tier {fee}: {e}")
                    continue
            
            return list(supported_tokens)
        except Exception as e:
            self.logger.error(f"Failed to get supported tokens: {e}")
            return []

    def swap_exact_tokens_for_tokens(
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
        """Execute a token swap with EIP-1559 gas parameters."""
        try:
            # Validate inputs
            self._validate_path(path)
            self._validate_amounts(amount_in, amount_out_min)

            # Check and approve token spending
            token_in = path[0]
            if not self.web3_manager.get_token_contract(token_in).functions.allowance(
                self.web3_manager.wallet_address,
                self.router_address
            ).call() >= amount_in:
                logger.info(f"Approving token {token_in} for amount {amount_in}")
                if not self.check_and_approve_token(token_in, amount_in):
                    logger.error(f"Failed to approve token {token_in}")
                    raise Exception(f"Token approval failed for {token_in}")
                logger.info(f"Token {token_in} approved successfully")
            
            # Encode path with fees
            encoded_path = self._encode_path(path)
            
            # Prepare transaction parameters
            tx_params = {
                'from': self.web3_manager.wallet_address,
                'nonce': self.web3_manager.w3.eth.get_transaction_count(
                    self.web3_manager.wallet_address,
                    'pending'
                ),
                'value': 0  # No ETH being sent
            }
            
            # Add EIP-1559 gas parameters if provided
            if gas is not None:
                tx_params['gas'] = gas
            if maxFeePerGas is not None:
                tx_params['maxFeePerGas'] = maxFeePerGas
            if maxPriorityFeePerGas is not None:
                tx_params['maxPriorityFeePerGas'] = maxPriorityFeePerGas
            
            # Build and send transaction
            # Log detailed recipient information
            self.logger.info("="*50)
            self.logger.info("SWAP TRANSACTION DETAILS")
            self.logger.info("="*50)
            self.logger.info(f"Token In: {token_in}")
            self.logger.info(f"Token Out: {path[-1]}")
            self.logger.info(f"Recipient Address: {to}")
            # Package arguments into the expected struct format
            params = {
                'path': encoded_path,
                'recipient': Web3.to_checksum_address(to),  # Ensure checksum address
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': amount_out_min
            }
            self.logger.info(f"""
Transaction Parameters:
- Method: exactInput
- Path Length: {len(encoded_path)} bytes
- Recipient: {params['recipient']}
- Gas: {tx_params.get('gas')}
- MaxFeePerGas: {tx_params.get('maxFeePerGas')}
- MaxPriorityFeePerGas: {tx_params.get('maxPriorityFeePerGas')}
            """)

            receipt = self.web3_manager.build_and_send_transaction(
                self.router,
                'exactInput',
                params, tx_params=tx_params)

            # Monitor transaction events
            if receipt and receipt['status'] == 1:
                try:
                    # Get transaction logs
                    logs = self.web3_manager.w3.eth.get_transaction_receipt(receipt['transactionHash'])['logs']
                    for log in logs:
                        if log['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':  # Transfer event
                            from_addr = '0x' + log['topics'][1].hex()[-40:]
                            to_addr = '0x' + log['topics'][2].hex()[-40:]
                            self.logger.info(f"Transfer Event Detected:")
                            self.logger.info(f"From: {from_addr}")
                            self.logger.info(f"To: {to_addr}")
                except Exception as e:
                    self.logger.error(f"Failed to parse transaction logs: {e}")
            
            # Log transaction result
            self.logger.info("="*50)
            self.logger.info("TRANSACTION RESULT")
            self.logger.info("="*50)
            self.logger.info(f"Transaction Hash: {receipt['transactionHash'].hex()}")
            self.logger.info(f"Block Number: {receipt['blockNumber']}")
            self.logger.info(f"Gas Used: {receipt['gasUsed']}")
            self.logger.info(f"Status: {'✅ Success' if receipt['status'] == 1 else '❌ Failed'}")
            self.logger.info("="*50)
            self.logger.info(f"Verify funds at: https://basescan.org/address/{to}")
            
            self._log_transaction(receipt['transactionHash'].hex(), amount_in, amount_out_min, path, to)
            return receipt
            
        except Exception as e:
            self._handle_error(e, "SwapBased V3 swap")
            raise
