"""Enhanced asynchronous flash loan management for arbitrage operations."""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from decimal import Decimal
from web3 import Web3
from eth_typing import Address

logger = logging.getLogger(__name__)

class AsyncFlashLoanManager:
    """
    Enhanced asynchronous flash loan manager with Flashbots integration.
    
    This implementation uses async/await pattern throughout, supports multi-token
    operations, and integrates with Flashbots for MEV protection.
    """
    
    def __init__(
        self, 
        web3_manager: Any, 
        config: Dict[str, Any],
        flashbots_manager: Optional[Any] = None,
        balance_validator: Optional[Any] = None
    ):
        """
        Initialize flash loan manager with advanced features.
        
        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary
            flashbots_manager: Optional FlashbotsManager instance
            balance_validator: Optional BundleBalanceValidator instance
        """
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self.flashbots_manager = flashbots_manager
        self.balance_validator = balance_validator
        
        # Configuration
        self.flash_loan_config = config.get('flash_loans', {})
        self.enabled = self.flash_loan_config.get('enabled', False)
        self.use_flashbots = self.flash_loan_config.get('use_flashbots', True)
        
        # Token configuration
        self.token_config = config.get('tokens', {})
        self.supported_tokens = {}  # Will be populated during initialization
        
        # Contract addresses
        self.arbitrage_contract_address = None
        self.arbitrage_contract = None
        self.balancer_vault_address = self.flash_loan_config.get(
            'balancer_vault', '0xBA12222222228d8Ba445958a75a0704d566BF2C8')
        
        # Transaction parameters
        self.min_profit_bps = self.flash_loan_config.get('min_profit_basis_points', 200)
        self.max_trade_size = Web3.to_wei(
            self.flash_loan_config.get('max_trade_size', '1'), 'ether')
        self.slippage_tolerance = self.flash_loan_config.get('slippage_tolerance', 50)  # 0.5%
        self.transaction_timeout = self.flash_loan_config.get('transaction_timeout', 180)  # 3 minutes
        
        # State tracking
        self._initialization_lock = asyncio.Lock()
        self.initialized = False
        self._supported_protocols = {"balancer", "aave"}
        self._active_loans = set()
        
        logger.info("Enhanced async flash loan manager initialized")
        
        if not self.enabled:
            logger.warning("Flash loans are currently disabled in config")
    
    async def initialize(self) -> bool:
        """
        Initialize flash loan manager asynchronously.
        
        Returns:
            bool: True if initialization succeeded
        """
        async with self._initialization_lock:
            if self.initialized:
                return True
                
            try:
                if not self.enabled:
                    logger.info("Flash loans are disabled, skipping initialization")
                    return True
                    
                # Load arbitrage contract ABI
                self.arbitrage_abi = await self._load_abi("BaseFlashLoanArbitrage")
                
                # Get contract address from deployments
                network = self.config.get('network', 'mainnet')
                contract_address = self.flash_loan_config.get('contract_address', {}).get(network)
                
                if not contract_address:
                    if network == 'mainnet':
                        # Use mainnet address when deployed
                        contract_address = self.flash_loan_config.get('mainnet_address')
                    else:
                        # Use testnet deployment
                        contract_address = self.flash_loan_config.get(
                            'testnet_address', "0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8")
                
                if contract_address:
                    self.arbitrage_contract_address = Web3.to_checksum_address(contract_address)
                    self.arbitrage_contract = self.w3.eth.contract(
                        address=self.arbitrage_contract_address,
                        abi=self.arbitrage_abi
                    )
                
                # Load supported tokens
                await self._initialize_supported_tokens()
                
                # Initialize Flashbots integration if requested
                if self.use_flashbots and not self.flashbots_manager:
                    await self._initialize_flashbots()
                
                if self.arbitrage_contract:
                    self.initialized = True
                    logger.info(f"Async flash loan manager initialized with contract at {self.arbitrage_contract_address}")
                    return True
                else:
                    logger.error("No flash loan contract address available")
                    return False
                
            except Exception as e:
                logger.error(f"Failed to initialize async flash loan manager: {e}")
                return False
    
    async def _initialize_supported_tokens(self) -> None:
        """Initialize the list of supported tokens for flash loans."""
        try:
            # Add basic tokens from config
            for symbol, token_data in self.token_config.items():
                if isinstance(token_data, dict) and 'address' in token_data:
                    address = Web3.to_checksum_address(token_data['address'])
                    decimals = token_data.get('decimals', 18)
                    self.supported_tokens[address] = {
                        'symbol': symbol,
                        'decimals': decimals,
                        'flash_loan_enabled': token_data.get('flash_loan_enabled', True)
                    }
                elif isinstance(token_data, str):
                    address = Web3.to_checksum_address(token_data)
                    # Try to get token details
                    token_contract = await self._get_token_contract(address)
                    if token_contract:
                        try:
                            symbol = await self._call_contract_method(token_contract.functions.symbol())
                            decimals = await self._call_contract_method(token_contract.functions.decimals())
                            self.supported_tokens[address] = {
                                'symbol': symbol,
                                'decimals': int(decimals),
                                'flash_loan_enabled': True
                            }
                        except Exception as e:
                            logger.warning(f"Could not get details for token {address}: {e}")
            
            logger.info(f"Initialized {len(self.supported_tokens)} supported tokens for flash loans")
        
        except Exception as e:
            logger.error(f"Error initializing supported tokens: {e}")
    
    async def _initialize_flashbots(self) -> None:
        """Initialize Flashbots integration if not already provided."""
        try:
            # Only import if needed
            if hasattr(self.web3_manager, 'flashbots_manager') and self.web3_manager.flashbots_manager:
                self.flashbots_manager = self.web3_manager.flashbots_manager
                logger.info("Using existing Flashbots manager from web3_manager")
            else:
                # Import here to avoid circular imports
                from ..integration.flashbots_integration import setup_flashbots_rpc
                
                # Initialize Flashbots RPC
                components = await setup_flashbots_rpc(
                    web3_manager=self.web3_manager,
                    config=self.config
                )
                
                self.flashbots_manager = components.get('flashbots_manager')
                self.balance_validator = components.get('balance_validator')
                
                logger.info("Initialized Flashbots integration for flash loans")
        
        except Exception as e:
            logger.error(f"Failed to initialize Flashbots integration: {e}")
    
    async def _load_abi(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Load contract ABI asynchronously.
        
        Args:
            name: Name of the ABI file (without .json extension)
            
        Returns:
            Optional ABI dictionary
        """
        try:
            # Use web3_manager's ABI loading if available
            if hasattr(self.web3_manager, '_load_abi'):
                return await self.web3_manager._load_abi(name)
            else:
                # Fallback to direct loading
                import json
                import os
                
                # Try common paths
                paths = [
                    os.path.join('abi', f"{name}.json"),
                    os.path.join('arbitrage_bot', 'abi', f"{name}.json"),
                    os.path.join(os.path.dirname(__file__), '..', '..', 'abi', f"{name}.json")
                ]
                
                for path in paths:
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            return json.load(f)
                
                logger.error(f"Could not find ABI file for {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading ABI {name}: {e}")
            return None
    
    async def _get_token_contract(self, token_address: str) -> Optional[Any]:
        """
        Get token contract instance asynchronously.
        
        Args:
            token_address: Token address
            
        Returns:
            Optional token contract
        """
        try:
            # Use web3_manager's get_token_contract if available
            if hasattr(self.web3_manager, 'get_token_contract'):
                return await self.web3_manager.get_token_contract(token_address)
            else:
                # Create contract instance directly
                token_address = Web3.to_checksum_address(token_address)
                token_abi = await self._load_abi("ERC20")
                if not token_abi:
                    return None
                
                return self.w3.eth.contract(address=token_address, abi=token_abi)
                
        except Exception as e:
            logger.error(f"Error getting token contract for {token_address}: {e}")
            return None
    
    async def _call_contract_method(self, method: Any, *args, **kwargs) -> Any:
        """
        Call a contract method asynchronously with retries.
        
        Args:
            method: Contract method to call
            *args: Arguments for the method
            **kwargs: Keyword arguments for the method
            
        Returns:
            Result of the method call
        """
        retries = 3
        delay = 1
        last_error = None
        
        for i in range(retries):
            try:
                # If method requires arguments
                if args or kwargs:
                    result = await method(*args, **kwargs).call()
                else:
                    result = await method.call()
                return result
            except Exception as e:
                last_error = e
                if i < retries - 1:
                    await asyncio.sleep(delay * (2 ** i))  # Exponential backoff
        
        # If we get here, all retries failed
        logger.error(f"Failed to call contract method after {retries} attempts: {last_error}")
        raise last_error
    
    async def is_token_supported(self, token_address: str) -> bool:
        """
        Check if a token is supported for flash loans.
        
        Args:
            token_address: Token address to check
            
        Returns:
            True if token is supported
        """
        # Make sure we're initialized
        if not self.initialized:
            await self.initialize()
            
        try:
            token_address = Web3.to_checksum_address(token_address)
            
            # Check if token is in supported_tokens
            if token_address in self.supported_tokens:
                return self.supported_tokens[token_address].get('flash_loan_enabled', False)
            
            # If not found, try to get details and check if it's supported
            token_contract = await self._get_token_contract(token_address)
            if not token_contract:
                return False
                
            try:
                # Check if token is supported on balancer
                symbol = await self._call_contract_method(token_contract.functions.symbol())
                decimals = await self._call_contract_method(token_contract.functions.decimals())
                
                # Add to supported tokens
                self.supported_tokens[token_address] = {
                    'symbol': symbol,
                    'decimals': int(decimals),
                    'flash_loan_enabled': True  # Assume enabled by default
                }
                
                return True
                
            except Exception as e:
                logger.warning(f"Could not determine if token {token_address} is supported: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking if token is supported: {e}")
            return False
    
    async def get_supported_tokens(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of supported tokens for flash loans.
        
        Returns:
            Dictionary of supported tokens with details
        """
        # Make sure we're initialized
        if not self.initialized:
            await self.initialize()
            
        return self.supported_tokens
    
    async def get_max_flash_loan_amount(self, token_address: str) -> int:
        """
        Get maximum flash loan amount for a token.
        
        Args:
            token_address: Token address
            
        Returns:
            Maximum amount in token units
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.enabled:
            return 0
            
        try:
            token_address = Web3.to_checksum_address(token_address)
            
            # Check if token is supported
            if not await self.is_token_supported(token_address):
                return 0
                
            # Get token decimals
            token_info = self.supported_tokens.get(token_address, {})
            decimals = token_info.get('decimals', 18)
            
            # Use configured max trade size as upper limit
            max_amount = self.max_trade_size
            
            # Convert max amount to token units if not WETH
            if token_address != self.web3_manager.get_weth_address():
                # Get token price in ETH
                token_price = await self._get_token_price(token_address)
                if token_price:
                    # Convert max ETH to token units
                    max_amount = int(max_amount / token_price)
            
            return max_amount
            
        except Exception as e:
            logger.error(f"Error getting max flash loan amount: {e}")
            return 0
    
    async def _get_token_price(self, token_address: str) -> Optional[Decimal]:
        """
        Get token price in ETH.
        
        Args:
            token_address: Token address
            
        Returns:
            Token price in ETH as Decimal
        """
        try:
            # Use web3_manager's get_token_price if available
            if hasattr(self.web3_manager, 'get_token_price'):
                price = await self.web3_manager.get_token_price(token_address)
                if price:
                    return Decimal(str(price))
            
            # Fallback to a simplified price calculation (not accurate)
            return Decimal('0.0001')  # Default fallback price
            
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return None
    
    async def estimate_flash_loan_cost(self, token_address: str, amount: Union[int, Decimal]) -> Dict[str, Any]:
        """
        Estimate complete cost breakdown for a flash loan.
        
        Args:
            token_address: Token address
            amount: Amount to borrow (in wei or token units)
            
        Returns:
            Dictionary with detailed cost breakdown
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.enabled:
            return {"success": False, "error": "Flash loans disabled"}
            
        try:
            token_address = Web3.to_checksum_address(token_address)
            
            # Check if token is supported
            if not await self.is_token_supported(token_address):
                return {"success": False, "error": f"Token {token_address} not supported"}
                
            # Convert amount to int if Decimal
            if isinstance(amount, Decimal):
                amount = int(amount)
                
            # Calculate fees based on protocol
            # Balancer charges 0.09%, AAVE charges 0.09%
            protocol_fee_rate = Decimal('0.0009')  # 0.09%
            protocol_fee = int(amount * protocol_fee_rate)
            
            # Calculate gas cost (estimate)
            gas_limit = 500000  # Conservative estimate
            
            # Get current gas price
            gas_price = await self.w3.eth.gas_price
            
            # Add buffer for gas price volatility
            gas_price = int(gas_price * 1.2)  # 20% buffer
            
            # Calculate gas cost in ETH
            gas_cost_wei = gas_limit * gas_price
            
            # Convert gas cost to token units if needed
            if token_address == self.web3_manager.get_weth_address():
                gas_cost_token = gas_cost_wei
            else:
                # Get token price in ETH
                token_price = await self._get_token_price(token_address)
                if token_price:
                    # Convert ETH to token units
                    gas_cost_token = int(gas_cost_wei / token_price)
                else:
                    gas_cost_token = 0
            
            # Calculate total cost
            total_cost = protocol_fee + gas_cost_token
            
            # Calculate minimum profit needed
            min_profit_required = int(amount * self.min_profit_bps / 10000)
            
            # Calculate minimum output needed for profit
            min_output_needed = amount + total_cost + min_profit_required
            
            return {
                "success": True,
                "token": token_address,
                "amount": amount,
                "protocol_fee": protocol_fee,
                "protocol_fee_rate": float(protocol_fee_rate),
                "gas_cost_wei": gas_cost_wei,
                "gas_cost_token": gas_cost_token,
                "total_cost": total_cost,
                "min_profit_required": min_profit_required,
                "min_output_needed": min_output_needed
            }
            
        except Exception as e:
            logger.error(f"Error estimating flash loan cost: {e}")
            return {"success": False, "error": str(e)}
    
    async def validate_arbitrage_opportunity(
        self,
        input_token: str,
        output_token: str,
        input_amount: int,
        expected_output: int,
        route: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate if an arbitrage opportunity is profitable with flash loan costs.
        
        Args:
            input_token: Input token address
            output_token: Output token address
            input_amount: Input amount in token units
            expected_output: Expected output amount
            route: List of route steps with DEX info
            
        Returns:
            Validation result with profit details
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.enabled:
            return {"success": False, "error": "Flash loans disabled"}
            
        try:
            input_token = Web3.to_checksum_address(input_token)
            output_token = Web3.to_checksum_address(output_token)
            
            # Check if this is a circular arbitrage (same input and output token)
            is_circular = input_token.lower() == output_token.lower()
            
            # Get flash loan cost estimate
            cost_estimate = await self.estimate_flash_loan_cost(input_token, input_amount)
            if not cost_estimate.get("success", False):
                return cost_estimate
                
            # Calculate net profit
            total_cost = cost_estimate.get("total_cost", 0)
            min_profit_required = cost_estimate.get("min_profit_required", 0)
            
            # For circular arbitrage, profit is expected_output - input_amount
            # For non-circular, need to convert output token to input token
            if is_circular:
                gross_profit = expected_output - input_amount
                net_profit = gross_profit - total_cost
            else:
                # Convert expected output to input token units
                output_in_input = await self._convert_token_value(
                    output_token, expected_output, input_token)
                
                gross_profit = output_in_input - input_amount
                net_profit = gross_profit - total_cost
            
            # Check if profitable
            is_profitable = net_profit > min_profit_required
            
            # Create detailed result
            result = {
                "success": True,
                "input_token": input_token,
                "output_token": output_token,
                "input_amount": input_amount,
                "expected_output": expected_output,
                "is_circular": is_circular,
                "gross_profit": gross_profit,
                "total_cost": total_cost,
                "net_profit": net_profit,
                "min_profit_required": min_profit_required,
                "is_profitable": is_profitable,
                "profit_margin": net_profit / input_amount if input_amount > 0 else 0,
                "route_details": route
            }
            
            # Add warning if net profit is too small
            if is_profitable and net_profit < min_profit_required * 2:
                result["warnings"] = ["Profit margin is very small and may be affected by price movements"]
                
            logger.info(f"Arbitrage validation: {'Profitable' if is_profitable else 'Not profitable'}, "
                       f"net profit: {net_profit}, required: {min_profit_required}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error validating arbitrage opportunity: {e}")
            return {"success": False, "error": str(e)}
    
    async def _convert_token_value(
        self, 
        from_token: str, 
        amount: int, 
        to_token: str
    ) -> int:
        """
        Convert token value from one token to another.
        
        Args:
            from_token: Source token address
            amount: Amount in source token units
            to_token: Target token address
            
        Returns:
            Equivalent amount in target token units
        """
        try:
            # If same token, no conversion needed
            if from_token.lower() == to_token.lower():
                return amount
                
            # Get prices in ETH
            from_price = await self._get_token_price(from_token)
            to_price = await self._get_token_price(to_token)
            
            if from_price and to_price and to_price > 0:
                # Convert value
                value_in_eth = Decimal(str(amount)) * from_price
                value_in_to_token = int(value_in_eth / to_price)
                return value_in_to_token
                
            return 0
            
        except Exception as e:
            logger.error(f"Error converting token value: {e}")
            return 0
    
    async def prepare_flash_loan_transaction(
        self,
        token_address: str,
        amount: int,
        route: List[Dict[str, Any]],
        min_profit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prepare a flash loan arbitrage transaction for execution.
        
        Args:
            token_address: Token to borrow
            amount: Amount to borrow
            route: Arbitrage route to execute
            min_profit: Minimum required profit
            
        Returns:
            Transaction data ready for execution
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.enabled:
            return {"success": False, "error": "Flash loans disabled"}
            
        if not self.arbitrage_contract:
            return {"success": False, "error": "Arbitrage contract not initialized"}
            
        try:
            token_address = Web3.to_checksum_address(token_address)
            
            # Check if token is supported
            if not await self.is_token_supported(token_address):
                return {"success": False, "error": f"Token {token_address} not supported"}
                
            # Make sure amount is within limits
            max_amount = await self.get_max_flash_loan_amount(token_address)
            if amount > max_amount:
                return {"success": False, "error": f"Amount {amount} exceeds max {max_amount}"}
                
            # Encode route for contract
            encoded_route = await self._encode_route(route)
            
            # Set minimum profit if not provided
            if min_profit is None:
                # Calculate minimum required profit
                cost_estimate = await self.estimate_flash_loan_cost(token_address, amount)
                if cost_estimate.get("success", False):
                    min_profit = max(
                        cost_estimate.get("min_profit_required", 0),
                        int(amount * self.min_profit_bps / 10000)
                    )
                else:
                    # Default to basis points calculation
                    min_profit = int(amount * self.min_profit_bps / 10000)
            
            # Prepare transaction data
            tx_data = await self.arbitrage_contract.functions.executeArbitrage(
                token_address,
                amount,
                encoded_route,
                min_profit
            ).build_transaction({
                'from': self.web3_manager.wallet_address,
                'gas': 900000,  # Higher gas limit for complex operations
                'maxFeePerGas': await self.w3.eth.gas_price * 2,
                'maxPriorityFeePerGas': await self.w3.eth.gas_price,
                'nonce': await self.w3.eth.get_transaction_count(self.web3_manager.wallet_address)
            })
            
            return {
                "success": True,
                "transaction": tx_data,
                "token": token_address,
                "amount": amount,
                "min_profit": min_profit,
                "encoded_route": encoded_route
            }
            
        except Exception as e:
            logger.error(f"Error preparing flash loan transaction: {e}")
            return {"success": False, "error": str(e)}
    
    async def _encode_route(self, route: List[Dict[str, Any]]) -> bytes:
        """
        Encode arbitrage route for contract consumption.
        
        Args:
            route: List of route steps with DEX info
            
        Returns:
            Encoded route data
        """
        # Simple implementation - customize based on your contract's expectations
        # In a real implementation, this would properly encode according to the contract's ABI
        try:
            encoded_steps = []
            for step in route:
                dex_id = step.get("dex_id", 0)  # Numeric identifier for DEX
                token_in = Web3.to_checksum_address(step.get("token_in"))
                token_out = Web3.to_checksum_address(step.get("token_out"))
                
                # Pack data based on your contract's expectations
                # This is a simplified example
                encoded_steps.append({
                    "dexId": dex_id,
                    "tokenIn": token_in,
                    "tokenOut": token_out
                })
                
            # Use web3's encoder
            return self.w3.codec.encode_abi(
                ["tuple(uint256 dexId, address tokenIn, address tokenOut)[]"],
                [encoded_steps]
            )
            
        except Exception as e:
            logger.error(f"Error encoding route: {e}")
            raise
    
    async def execute_flash_loan_arbitrage(
        self,
        token_address: str,
        amount: int,
        route: List[Dict[str, Any]],
        min_profit: Optional[int] = None,
        use_flashbots: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Execute a flash loan arbitrage transaction.
        
        Args:
            token_address: Token to borrow
            amount: Amount to borrow
            route: Arbitrage route to execute
            min_profit: Minimum required profit
            use_flashbots: Whether to use Flashbots (defaults to config)
            
        Returns:
            Execution result including transaction receipt
        """
        if not self.initialized:
            await self.initialize()
            
        if not self.enabled:
            return {"success": False, "error": "Flash loans disabled"}
            
        try:
            # Prepare transaction
            tx_result = await self.prepare_flash_loan_transaction(
                token_address=token_address,
                amount=amount,
                route=route,
                min_profit=min_profit
            )
            
            if not tx_result.get("success", False):
                return tx_result
                
            tx_data = tx_result.get("transaction")
            
            # Determine whether to use Flashbots
            if use_flashbots is None:
                use_flashbots = self.use_flashbots
                
            if use_flashbots and self.flashbots_manager:
                # Execute via Flashbots
                return await self._execute_via_flashbots(tx_data, token_address, min_profit)
            else:
                # Execute via standard transaction
                return await self._execute_standard_transaction(tx_data)
                
        except Exception as e:
            logger.error(f"Error executing flash loan arbitrage: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_via_flashbots(
        self,
        tx_data: Dict[str, Any],
        token_address: str,
        min_profit: int
    ) -> Dict[str, Any]:
        """
        Execute transaction via Flashbots.
        
        Args:
            tx_data: Transaction data
            token_address: Token being borrowed
            min_profit: Minimum profit required
            
        Returns:
            Execution result
        """
        try:
            logger.info("Executing flash loan arbitrage via Flashbots")
            
            # Sign transaction
            signed_tx = self.web3_manager.account.sign_transaction(tx_data)
            
            # Create bundle
            next_block = await self.w3.eth.block_number + 1
            bundle_id = await self.flashbots_manager.create_bundle(
                target_block=next_block,
                transactions=[signed_tx.rawTransaction.hex()]
            )
            
            # Simulate bundle
            simulation = await self.flashbots_manager.simulate_bundle(bundle_id)
            
            # Validate bundle profit
            validation = None
            if self.balance_validator:
                validation = await self.balance_validator.validate_bundle_balance(
                    bundle_id=bundle_id,
                    token_addresses=[token_address, self.web3_manager.get_weth_address()],
                    expected_profit=min_profit
                )
                
                if validation and not validation.get("success", False):
                    return {
                        "success": False, 
                        "status": "rejected",
                        "reason": "validation_failed",
                        "validation": validation,
                        "simulation": simulation
                    }
            
            # Submit bundle
            submission = await self.flashbots_manager.submit_bundle(bundle_id)
            
            return {
                "success": True,
                "status": "submitted",
                "bundle_id": bundle_id,
                "simulation": simulation,
                "validation": validation,
                "submission": submission,
                "target_block": next_block
            }
            
        except Exception as e:
            logger.error(f"Error executing via Flashbots: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_standard_transaction(
        self,
        tx_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute transaction via standard method.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            Execution result
        """
        try:
            logger.info("Executing flash loan arbitrage via standard transaction")
            
            # Sign transaction
            signed_tx = self.web3_manager.account.sign_transaction(tx_data)
            
            # Send transaction
            tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            logger.info(f"Flash loan transaction submitted: {tx_hash_hex}")
            
            # Wait for transaction receipt with timeout
            try:
                receipt = await asyncio.wait_for(
                    self.web3_manager.wait_for_transaction(tx_hash),
                    timeout=self.transaction_timeout
                )
                
                success = receipt.status == 1
                logger.info(f"Flash loan transaction {'succeeded' if success else 'failed'}: {tx_hash_hex}")
                
                return {
                    "success": success,
                    "status": "confirmed" if success else "failed",
                    "tx_hash": tx_hash_hex,
                    "receipt": dict(receipt)
                }
                
            except asyncio.TimeoutError:
                logger.warning(f"Transaction timed out after {self.transaction_timeout}s: {tx_hash_hex}")
                return {
                    "success": False,
                    "status": "timeout",
                    "tx_hash": tx_hash_hex,
                    "error": f"Transaction timed out after {self.transaction_timeout}s"
                }
                
        except Exception as e:
            logger.error(f"Error executing standard transaction: {e}")
            return {"success": False, "error": str(e)}
            
    async def __aenter__(self):
        """Support async context manager."""
        if not self.initialized:
            await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup when used as context manager."""
        # Nothing specific to clean up for now
        return False

async def create_flash_loan_manager(
    web3_manager: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None,
    flashbots_manager: Optional[Any] = None
) -> AsyncFlashLoanManager:
    """
    Create and initialize an enhanced async flash loan manager.
    
    Args:
        web3_manager: Optional Web3Manager instance
        config: Optional configuration dictionary
        flashbots_manager: Optional FlashbotsManager instance
        
    Returns:
        Initialized AsyncFlashLoanManager
    """
    try:
        # Load dependencies if not provided
        if web3_manager is None or config is None:
            # Import here to avoid circular imports
            from ..utils.config_loader import load_config
            from ..core.web3.web3_manager import create_web3_manager
            
            if config is None:
                config = load_config()
                
            if web3_manager is None:
                web3_manager = await create_web3_manager(
                    provider_url=config.get("provider_url"),
                    chain_id=config.get("chain_id"),
                    private_key=config.get("private_key")
                )
        
        # Create Flashbots integration if needed
        if not flashbots_manager and config.get('flash_loans', {}).get('use_flashbots', True):
            try:
                from ..integration.flashbots_integration import setup_flashbots_rpc
                
                components = await setup_flashbots_rpc(
                    web3_manager=web3_manager,
                    config=config
                )
                
                flashbots_manager = components.get('flashbots_manager')
                balance_validator = components.get('balance_validator')
                
            except Exception as e:
                logger.warning(f"Could not set up Flashbots integration: {e}")
                flashbots_manager = None
                balance_validator = None
        else:
            balance_validator = None
        
        # Create manager instance
        manager = AsyncFlashLoanManager(
            web3_manager=web3_manager,
            config=config,
            flashbots_manager=flashbots_manager,
            balance_validator=balance_validator
        )
        
        # Initialize manager
        await manager.initialize()
        
        logger.info("Async flash loan manager created and initialized")
        return manager
        
    except Exception as e:
        logger.error(f"Failed to create async flash loan manager: {e}")
        raise