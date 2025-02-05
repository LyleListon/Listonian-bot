"""Portfolio tracking and balance management."""

import logging
from typing import Dict, Any, Optional
from web3 import Web3

logger = logging.getLogger(__name__)

class PortfolioTracker:
    """Tracks portfolio balances and performance."""
    
    def __init__(self, web3: Web3, wallet_address: str, config: Dict[str, Any]):
        """Initialize portfolio tracker."""
        self.web3 = web3
        self.wallet_address = wallet_address
        self.config = config
        self.balances = {}
        self.initialized = False
        
    async def initialize(self) -> bool:
        """Initialize portfolio tracker."""
        try:
            # Get initial balances
            for token_symbol, token_config in self.config.get('tokens', {}).items():
                address = token_config.get('address')
                if address:
                    try:
                        balance = await self.get_token_balance(address)
                        self.balances[token_symbol] = str(balance)
                    except Exception as e:
                        logger.error(f"Failed to get balance for {token_symbol}: {e}")
                        return False
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize portfolio tracker: {e}")
            return False
            
    async def get_token_balance(self, token_address: str) -> str:
        """Get token balance for wallet."""
        try:
            # Create contract instance
            abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                }
            ]
            contract = self.web3.eth.contract(address=token_address, abi=abi)
            
            # Get balance
            balance = await contract.functions.balanceOf(self.wallet_address).call()
            return str(balance)
            
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            return "0"
            
    async def update_balances(self) -> bool:
        """Update all token balances."""
        try:
            for token_symbol, token_config in self.config.get('tokens', {}).items():
                address = token_config.get('address')
                if address:
                    try:
                        balance = await self.get_token_balance(address)
                        self.balances[token_symbol] = str(balance)
                    except Exception as e:
                        logger.error(f"Failed to update balance for {token_symbol}: {e}")
                        return False
            return True
            
        except Exception as e:
            logger.error(f"Failed to update balances: {e}")
            return False

async def create_portfolio_tracker(
    web3_manager: Any,
    wallet_address: str,
    config: Dict[str, Any]
) -> Optional[PortfolioTracker]:
    """Create and initialize a portfolio tracker instance."""
    try:
        tracker = PortfolioTracker(web3_manager.w3, wallet_address, config)
        if await tracker.initialize():
            return tracker
        return None
    except Exception as e:
        logger.error(f"Failed to create portfolio tracker: {e}")
        return None
