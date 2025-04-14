"""Base connector for DEX integrations."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class BaseDEXConnector(ABC):
    """Base class for DEX connectors."""
    
    def __init__(self, name: str, network: str, config: Dict[str, Any]):
        """Initialize the DEX connector.
        
        Args:
            name: Name of the DEX.
            network: Network the DEX is on.
            config: Configuration dictionary.
        """
        self.name = name
        self.network = network
        self.config = config
        self.enabled = config.get("enabled", True)
        
        logger.info(f"Initialized {name} connector on {network}")
    
    @abstractmethod
    def get_pairs(self) -> List[Dict[str, Any]]:
        """Get all trading pairs from the DEX.
        
        Returns:
            List of trading pairs.
        """
        pass
    
    @abstractmethod
    def get_token_prices(self) -> Dict[str, float]:
        """Get token prices from the DEX.
        
        Returns:
            Dictionary mapping tokens to their USD prices.
        """
        pass
    
    @abstractmethod
    def get_token_info(self) -> Dict[str, Dict[str, Any]]:
        """Get token information from the DEX.
        
        Returns:
            Dictionary mapping tokens to their information.
        """
        pass
    
    @abstractmethod
    def get_reserves(self, pair_address: str) -> Dict[str, Any]:
        """Get reserves for a trading pair.
        
        Args:
            pair_address: Address of the trading pair.
            
        Returns:
            Dictionary with reserve information.
        """
        pass
    
    @abstractmethod
    def calculate_output_amount(
        self,
        input_token: str,
        output_token: str,
        input_amount: float,
        fee_tier: Optional[float] = None,
    ) -> float:
        """Calculate the output amount for a swap.
        
        Args:
            input_token: Input token address or symbol.
            output_token: Output token address or symbol.
            input_amount: Input amount.
            fee_tier: Optional fee tier for DEXes with multiple fee tiers.
            
        Returns:
            Expected output amount.
        """
        pass
    
    @abstractmethod
    def get_swap_transaction(
        self,
        input_token: str,
        output_token: str,
        input_amount: float,
        min_output_amount: float,
        recipient: str,
        deadline: int,
        fee_tier: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get a swap transaction.
        
        Args:
            input_token: Input token address or symbol.
            output_token: Output token address or symbol.
            input_amount: Input amount.
            min_output_amount: Minimum output amount.
            recipient: Address to receive the output tokens.
            deadline: Transaction deadline timestamp.
            fee_tier: Optional fee tier for DEXes with multiple fee tiers.
            
        Returns:
            Transaction parameters.
        """
        pass
