"""Flash loan management for arbitrage operations."""

import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
from web3 import Web3
from eth_typing import Address

logger = logging.getLogger(__name__)

class FlashLoanManager:
    """Manages flash loan operations for arbitrage."""
    
    def __init__(self, web3_manager: Any, config: Dict[str, Any]):
        """Initialize flash loan manager."""
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self.enabled = config.get('flash_loans', {}).get('enabled', False)
        self.initialized = False
        
        # Contract addresses
        self.arbitrage_contract = None
        self.arbitrage_abi = None
        self.weth_address = config.get('tokens', {}).get('WETH')
        self.usdc_address = config.get('tokens', {}).get('USDC')
        
        # Parameters
        self.min_profit_bps = config.get('flash_loans', {}).get('min_profit_basis_points', 200)
        self.max_trade_size = Web3.to_wei(config.get('flash_loans', {}).get('max_trade_size', '0.1'), 'ether')
        
        logger.info("Flash loan manager initialized")
        
        if not self.enabled:
            logger.warning("Flash loans are currently disabled in config")
    
    def initialize(self) -> bool:
        """Initialize flash loan manager."""
        try:
            if not self.enabled:
                logger.info("Flash loans are disabled, skipping initialization")
                return True
                
            # Load contract ABI
            self.arbitrage_abi = self.web3_manager.load_abi("BaseFlashLoanArbitrage")
            
            # Get contract address from deployments
            network = self.config.get('network', 'mainnet')
            if network == 'mainnet':
                # Use mainnet address when deployed
                self.arbitrage_contract = None  # TODO: Update with mainnet address
            else:
                # Use Sepolia test deployment
                self.arbitrage_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address("0xa111E81d1F6F8bF648d1405ADf45aAC92602BcA8"),
                    abi=self.arbitrage_abi
                )
            
            if self.arbitrage_contract:
                self.initialized = True
                logger.info(f"Flash loan manager initialized with contract at {self.arbitrage_contract.address}")
                return True
            else:
                logger.error("No flash loan contract address available")
                return False
            
        except Exception as e:
            logger.error(f"Failed to initialize flash loan manager: {e}")
            return False
    
    def check_flash_loan_availability(self, token_address: str, amount: Decimal) -> bool:
        """
        Check if flash loan is available for given token and amount.
        
        Args:
            token_address (str): Token address
            amount (Decimal): Amount to borrow
            
        Returns:
            bool: True if flash loan is available
        """
        if not self.enabled or not self.initialized:
            return False
            
        try:
            # Check if amount is within limits
            amount_wei = Web3.to_wei(amount, 'ether')
            if amount_wei > self.max_trade_size:
                logger.warning(f"Amount {amount} exceeds max trade size {Web3.from_wei(self.max_trade_size, 'ether')}")
                return False
            
            # Verify token is supported (currently only WETH and USDC)
            if token_address.lower() not in [self.weth_address.lower(), self.usdc_address.lower()]:
                logger.warning(f"Token {token_address} not supported for flash loans")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking flash loan availability: {e}")
            return False
    
    def estimate_flash_loan_cost(self, token_address: str, amount: Decimal) -> Decimal:
        """
        Estimate cost of flash loan.
        
        Args:
            token_address (str): Token address
            amount (Decimal): Amount to borrow
            
        Returns:
            Decimal: Estimated cost in token units
        """
        if not self.enabled or not self.initialized:
            return Decimal('0')
            
        try:
            # Flash loan fee is typically 0.09%
            fee_rate = Decimal('0.0009')
            return amount * fee_rate
            
        except Exception as e:
            logger.error(f"Error estimating flash loan cost: {e}")
            return Decimal('0')
    
    def prepare_flash_loan(self, token_address: str, amount: Decimal) -> Optional[Dict[str, Any]]:
        """
        Prepare flash loan transaction data.
        
        Args:
            token_address (str): Token address
            amount (Decimal): Amount to borrow
            
        Returns:
            Optional[Dict[str, Any]]: Transaction data if successful
        """
        if not self.enabled or not self.initialized:
            return None
            
        try:
            amount_wei = Web3.to_wei(amount, 'ether')
            
            # Prepare transaction data
            return {
                'token': Web3.to_checksum_address(token_address),
                'amount': amount_wei,
                'contract': self.arbitrage_contract.address
            }
            
        except Exception as e:
            logger.error(f"Error preparing flash loan: {e}")
            return None
            
    def execute_arbitrage(
        self,
        token_in: str,
        token_out: str,
        amount: int,
        buy_dex: str,
        sell_dex: str,
        min_profit: int
    ) -> Optional[Dict[str, Any]]:
        """
        Execute flash loan arbitrage.
        
        Args:
            token_in (str): Input token address
            token_out (str): Output token address
            amount (int): Amount to borrow
            buy_dex (str): DEX to buy from
            sell_dex (str): DEX to sell on
            min_profit (int): Minimum profit in wei
            
        Returns:
            Optional[Dict[str, Any]]: Transaction receipt if successful
        """
        if not self.enabled or not self.initialized:
            return None
            
        try:
            # Verify amount is within limits
            if amount > self.max_trade_size:
                logger.warning(f"Amount {amount} exceeds max trade size {self.max_trade_size}")
                return None
            
            # Verify min profit meets requirements
            min_profit_required = (amount * self.min_profit_bps) // 10000
            if min_profit < min_profit_required:
                logger.warning(f"Min profit {min_profit} below required {min_profit_required}")
                return None
            
            # Prepare transaction
            tx_data = self.arbitrage_contract.functions.executeArbitrage(
                token_in,
                token_out,
                amount,
                buy_dex,
                sell_dex,
                min_profit
            ).build_transaction({
                'from': self.web3_manager.account.address,
                'gas': 500000,  # Estimate gas
                'nonce': self.w3.eth.get_transaction_count(self.web3_manager.account.address)
            })
            
            # Sign and send transaction
            signed_tx = self.web3_manager.account.sign_transaction(tx_data)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            logger.info(f"Flash loan arbitrage executed: {receipt['transactionHash'].hex()}")
            return receipt
            
        except Exception as e:
            logger.error(f"Error executing flash loan arbitrage: {e}")
            return None

def create_flash_loan_manager(
    web3_manager: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None
) -> FlashLoanManager:
    """
    Create and initialize a flash loan manager instance.
    
    Args:
        web3_manager: Optional Web3Manager instance
        config: Optional configuration dictionary
        
    Returns:
        FlashLoanManager: Initialized flash loan manager
    """
    try:
        # Load dependencies if not provided
        if web3_manager is None or config is None:
            # Import here to avoid circular imports
            from .web3.web3_manager import create_web3_manager
            from ..utils.config_loader import load_config
            
            if config is None:
                config = load_config()
            
            if web3_manager is None:
                web3_manager = create_web3_manager()
        
        # Create manager instance
        manager = FlashLoanManager(web3_manager=web3_manager, config=config)
        manager.initialize()
        logger.info("Flash loan manager created")
        return manager
        
    except Exception as e:
        logger.error(f"Failed to create flash loan manager: {e}")
        raise
