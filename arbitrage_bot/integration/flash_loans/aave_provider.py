"""Aave flash loan provider."""

import logging
from typing import Dict, List, Any, Optional

from arbitrage_bot.integration.flash_loans.base_provider import BaseFlashLoanProvider
from arbitrage_bot.integration.blockchain.base_connector import BaseBlockchainConnector

logger = logging.getLogger(__name__)


class AaveFlashLoanProvider(BaseFlashLoanProvider):
    """Provider for Aave flash loans."""
    
    def __init__(
        self,
        name: str,
        network: str,
        config: Dict[str, Any],
        blockchain_connector: BaseBlockchainConnector,
    ):
        """Initialize the Aave flash loan provider.
        
        Args:
            name: Name of the provider.
            network: Network the provider is on.
            config: Configuration dictionary.
            blockchain_connector: Blockchain connector.
        """
        super().__init__(name, network, config)
        
        self.blockchain_connector = blockchain_connector
        self.lending_pool_address = config.get("lending_pool_address")
        self.fee_percentage = config.get("fee_percentage", 0.09)
        self.max_loan_amount = config.get("max_loan_amount", 100)
        
        # Token cache
        self.supported_tokens = {}
        
        logger.info(f"Initialized {name} flash loan provider on {network}")
    
    def get_supported_tokens(self) -> List[str]:
        """Get supported tokens for flash loans.
        
        Returns:
            List of supported token addresses.
        """
        # This is a simplified implementation
        # In a real implementation, we would query the Aave protocol
        
        # For now, we'll return hardcoded tokens
        if not self.supported_tokens:
            self.supported_tokens = {
                "0x0000000000000000000000000000000000000000": {
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "decimals": 18,
                },
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": {
                    "symbol": "WETH",
                    "name": "Wrapped Ethereum",
                    "decimals": 18,
                },
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": {
                    "symbol": "USDC",
                    "name": "USD Coin",
                    "decimals": 6,
                },
                "0xdAC17F958D2ee523a2206206994597C13D831ec7": {
                    "symbol": "USDT",
                    "name": "Tether",
                    "decimals": 6,
                },
                "0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                    "symbol": "DAI",
                    "name": "Dai Stablecoin",
                    "decimals": 18,
                },
                "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599": {
                    "symbol": "WBTC",
                    "name": "Wrapped Bitcoin",
                    "decimals": 8,
                },
            }
        
        return list(self.supported_tokens.keys())
    
    def get_fee_percentage(self, token_address: str) -> float:
        """Get the fee percentage for a token.
        
        Args:
            token_address: The token address.
            
        Returns:
            The fee percentage.
        """
        # Aave V3 has a fixed fee of 0.09%
        return self.fee_percentage
    
    def get_max_loan_amount(self, token_address: str) -> float:
        """Get the maximum loan amount for a token.
        
        Args:
            token_address: The token address.
            
        Returns:
            The maximum loan amount.
        """
        # This is a simplified implementation
        # In a real implementation, we would query the Aave protocol
        
        # For now, we'll return a hardcoded value
        token_info = self.supported_tokens.get(token_address)
        if not token_info:
            return 0.0
        
        # Different max amounts for different tokens
        symbol = token_info.get("symbol")
        if symbol == "ETH" or symbol == "WETH":
            return self.max_loan_amount
        elif symbol == "WBTC":
            return self.max_loan_amount / 15.0  # Approximately 1/15 of ETH max
        elif symbol in ["USDC", "USDT", "DAI"]:
            return self.max_loan_amount * 3500.0  # Approximately ETH price in USD
        else:
            return self.max_loan_amount / 10.0
    
    def prepare_flash_loan(
        self,
        token_address: str,
        amount: float,
        target_contract: str,
        callback_data: bytes,
    ) -> Dict[str, Any]:
        """Prepare a flash loan transaction.
        
        Args:
            token_address: The token address.
            amount: The loan amount.
            target_contract: The contract that will receive the loan.
            callback_data: The data to pass to the callback function.
            
        Returns:
            Transaction parameters.
        """
        # This is a simplified implementation
        # In a real implementation, we would create a transaction to call the Aave lending pool
        
        # Check if token is supported
        if token_address not in self.supported_tokens:
            raise ValueError(f"Token {token_address} not supported for flash loans")
        
        # Check if amount is within limits
        max_amount = self.get_max_loan_amount(token_address)
        if amount > max_amount:
            raise ValueError(
                f"Loan amount {amount} exceeds maximum {max_amount} for token {token_address}"
            )
        
        # Create transaction
        tx = {
            "from": target_contract,
            "to": self.lending_pool_address,
            "value": 0,
            "data": f"flashLoan_{token_address}_{amount}_{target_contract}_{callback_data.hex()}",
            "gas": 500000,
            "gasPrice": self.blockchain_connector.get_gas_price(),
        }
        
        return tx
