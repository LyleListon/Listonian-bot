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
        self.is_enabled = config.get('enabled', False)

    async def initialize(self) -> bool:
        """Initialize the SwapBased interface."""
        try:
            # Initialize contracts with checksummed addresses
            self.router = self.web3_manager.get_contract(
                address=self.router_address,
                abi_name="swapbased_v3_router"
            )
            self.factory = self.web3_manager.get_contract(
                address=self.factory_address,
                abi_name="swapbased_v3_factory"
            )
            self.quoter = self.web3_manager.get_contract(
                address=self.quoter_address,
                abi_name="swapbased_v3_quoter"
            )
            
            # Initialize contracts
            self.initialized = True
            self.logger.info(self.name + " interface initialized")
            return True
            
        except Exception as e:
            self._handle_error(e, "SwapBased initialization")
            return False

    async def get_quote_with_impact(
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
                    pool_address = self.get_pool_address(path[0], path[1], fee)
                    if not pool_address:
                        continue
                        
                    # Get pool contract
                    pool = self.web3_manager.get_contract(
                        address=Web3.to_checksum_address(pool_address),
                        abi_name="swapbased_v3_pool"
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
                        self.logger.debug("No quote available for fee tier " + str(fee))
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
                    self.logger.debug("Error getting quote for fee tier " + str(fee) + ": " + str(e))
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get V3 quote: " + str(e))
            return None

    async def get_token_price(self, token_address: str) -> float:
        """Get current token price."""
        try:
            # If token is WETH, return 1.0 since price is in WETH
            if token_address.lower() == self.weth_address.lower():
                return 1.0

            # Try each fee tier
            for fee in self.FEE_TIERS:
                try:
                    # Get pool address
                    pool_address = self.get_pool_address(
                        token_address,
                        self.weth_address,
                        fee
                    )
                    
                    if not pool_address:
                        continue
                        
                    # Get pool contract
                    pool = self.web3_manager.get_contract(
                        address=Web3.to_checksum_address(pool_address),
                        abi_name="swapbased_v3_pool"
                    )
                    
                    # Get slot0 data which contains the current sqrt price
                    slot0 = self._retry_sync(
                        lambda: pool.functions.slot0().call()
                    )
                    
                    # Calculate price from sqrtPriceX96
                    sqrt_price_x96 = slot0[0]
                    if sqrt_price_x96 == 0:
                        continue
                        
                    price = (sqrt_price_x96 / (2 ** 96)) ** 2
                    
                    # Adjust for token order
                    token0 = self._retry_sync(
                        lambda: pool.functions.token0().call()
                    )
                    
                    if token_address.lower() == token0.lower():
                        price = 1 / price
                        
                    return float(price)
                    
                except Exception as e:
                    self.logger.debug("Error getting price for fee tier " + str(fee) + ": " + str(e))
                    continue
            
            return 0.0
            
        except Exception as e:
            self.logger.error("Failed to get token price: " + str(e))
            return 0.0

    def _encode_path(self, path: List[str], fee: int = None) -> bytes:
        """Encode path with fees for V3 swap."""
        encoded = b''
        for i in range(len(path) - 1):
            encoded += bytes.fromhex(path[i][2:])  # Remove '0x' prefix
            encoded += (fee or self.fee).to_bytes(3, 'big')  # Add fee as 3 bytes
        encoded += bytes.fromhex(path[-1][2:])  # Add final token
        return encoded

    async def get_supported_tokens(self) -> List[str]:
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
                            abi_name="swapbased_v3_pool"
                        )
                        
                except Exception as e:
                    self.logger.debug("Error checking fee tier " + str(fee) + ": " + str(e))
                    continue
            
            return list(supported_tokens)
        except Exception as e:
            self.logger.error("Failed to get supported tokens: " + str(e))
            return []

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
                self.logger.info("Approving token " + str(token_in) + " for amount " + str(amount_in))
                if not await self.check_and_approve_token(token_in, amount_in):
                    self.logger.error("Failed to approve token " + str(token_in))
                    raise Exception("Token approval failed for " + str(token_in))
                self.logger.info("Token " + str(token_in) + " approved successfully")
            
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
            self.logger.info("Token In: " + str(token_in))
            self.logger.info("Token Out: " + str(path[-1]))
            self.logger.info("Recipient Address: " + str(to))
            # Package arguments into the expected struct format
            params = {
                'path': encoded_path,
                'recipient': Web3.to_checksum_address(to),  # Ensure checksum address
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': amount_out_min
            }
            self.logger.info(
                "Transaction Parameters:\n" +
                "- Method: exactInput\n" +
                "- Path Length: " + str(len(encoded_path)) + " bytes\n" +
                "- Recipient: " + str(params['recipient']) + "\n" +
                "- Gas: " + str(tx_params.get('gas')) + "\n" +
                "- MaxFeePerGas: " + str(tx_params.get('maxFeePerGas')) + "\n" +
                "- MaxPriorityFeePerGas: " + str(tx_params.get('maxPriorityFeePerGas'))
            )

            receipt = await self.web3_manager.build_and_send_transaction(
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
                            self.logger.info("Transfer Event Detected:")
                            self.logger.info("From: " + str(from_addr))
                            self.logger.info("To: " + str(to_addr))
                except Exception as e:
                    self.logger.error("Failed to parse transaction logs: " + str(e))
            
            # Log transaction result
            self.logger.info("="*50)
            self.logger.info("TRANSACTION RESULT")
            self.logger.info("="*50)
            self.logger.info("Transaction Hash: " + str(receipt['transactionHash'].hex()))
            self.logger.info("Block Number: " + str(receipt['blockNumber']))
            self.logger.info("Gas Used: " + str(receipt['gasUsed']))
            self.logger.info("Status: " + ("✅ Success" if receipt['status'] == 1 else "❌ Failed"))
            self.logger.info("="*50)
            self.logger.info("Verify funds at: https://basescan.org/address/" + str(to))
            
            self._log_transaction(receipt['transactionHash'].hex(), amount_in, amount_out_min, path, to)
            return receipt
            
        except Exception as e:
            self._handle_error(e, "SwapBased V3 swap")
            raise
