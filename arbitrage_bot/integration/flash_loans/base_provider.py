"""Base provider for flash loan integrations."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class BaseFlashLoanProvider(ABC):
    """Base class for flash loan providers."""
    
    def __init__(self, name: str, network: str, config: Dict[str, Any]):
        """Initialize the flash loan provider.
        
        Args:
            name: Name of the provider.
            network: Network the provider is on.
            config: Configuration dictionary.
        """
        self.name = name
        self.network = network
        self.config = config
        self.enabled = config.get("enabled", True)
        
        logger.info(f"Initialized {name} flash loan provider on {network}")
    
    @abstractmethod
    def get_supported_tokens(self) -> List[str]:
        """Get supported tokens for flash loans.
        
        Returns:
            List of supported token addresses.
        """
        pass
    
    @abstractmethod
    def get_fee_percentage(self, token_address: str) -> float:
        """Get the fee percentage for a token.
        
        Args:
            token_address: The token address.
            
        Returns:
            The fee percentage.
        """
        pass
    
    @abstractmethod
    def get_max_loan_amount(self, token_address: str) -> float:
        """Get the maximum loan amount for a token.
        
        Args:
            token_address: The token address.
            
        Returns:
            The maximum loan amount.
        """
        pass
    
    @abstractmethod
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
        pass
