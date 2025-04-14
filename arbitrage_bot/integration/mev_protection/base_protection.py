"""Base protection for MEV protection integrations."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class BaseMEVProtection(ABC):
    """Base class for MEV protection services."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize the MEV protection service.
        
        Args:
            name: Name of the protection service.
            config: Configuration dictionary.
        """
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
        
        logger.info(f"Initialized {name} MEV protection service")
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the protection service is available.
        
        Returns:
            True if available, False otherwise.
        """
        pass
    
    @abstractmethod
    def prepare_transaction(
        self, tx: Dict[str, Any], options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare a transaction for MEV protection.
        
        Args:
            tx: The transaction parameters.
            options: Additional options for the protection service.
            
        Returns:
            Modified transaction parameters.
        """
        pass
    
    @abstractmethod
    def send_transaction(self, tx: Dict[str, Any]) -> str:
        """Send a transaction with MEV protection.
        
        Args:
            tx: The transaction parameters.
            
        Returns:
            The transaction hash.
        """
        pass
    
    @abstractmethod
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """Get the status of a transaction.
        
        Args:
            tx_hash: The transaction hash.
            
        Returns:
            Transaction status information.
        """
        pass
