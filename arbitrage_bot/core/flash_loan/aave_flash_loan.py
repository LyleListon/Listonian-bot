"""
Aave Flash Loan Module

This module provides functionality for:
- Flash loan execution through Aave
- Flash loan transaction building
- Loan validation and verification
"""

import logging
from typing import List, Dict, Any
from decimal import Decimal
from eth_typing import ChecksumAddress
from web3 import Web3

from ..web3.interfaces import Web3Client
from ...utils.async_manager import with_retry, AsyncLock

logger = logging.getLogger(__name__)

class AaveFlashLoan:
    """Manages flash loan operations through Aave."""

    def __init__(
        self,
        w3: Web3Client,
        pool_address: ChecksumAddress,
        min_profit: int = 0
    ):
        """
        Initialize Aave flash loan manager.

        Args:
            w3: Web3 client instance
            pool_address: Aave pool address
            min_profit: Minimum profit threshold in wei
        """
        self.w3 = w3
        self.pool_address = pool_address
        self.min_profit = min_profit
        self._lock = AsyncLock()

        # Aave Pool ABI for flash loan function
        self.pool_abi = [{
            "inputs": [
                {
                    "internalType": "address[]",
                    "name": "assets",
                    "type": "address[]"
                },
                {
                    "internalType": "uint256[]",
                    "name": "amounts",
                    "type": "uint256[]"
                },
                {
                    "internalType": "uint256[]",
                    "name": "modes",
                    "type": "uint256[]"
                },
                {
                    "internalType": "address",
                    "name": "onBehalfOf",
                    "type": "address"
                },
                {
                    "internalType": "bytes",
                    "name": "params",
                    "type": "bytes"
                },
                {
                    "internalType": "uint16",
                    "name": "referralCode",
                    "type": "uint16"
                }
            ],
            "name": "flashLoan",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }]

        # Create contract instance
        self.pool_contract = self.w3.contract(
            address=pool_address,
            abi=self.pool_abi
        )

        logger.info(
            f"Aave flash loan manager initialized with "
            f"pool {pool_address} and "
            f"min profit {self.w3.w3.from_wei(min_profit, 'ether')} ETH"
        )

    @with_retry(max_attempts=3, base_delay=1.0)
    async def build_flash_loan_tx(
        self,
        tokens: List[str],
        amounts: List[int],
        target_contract: ChecksumAddress,
        callback_data: bytes
    ) -> Dict[str, Any]:
        """
        Build flash loan transaction.

        Args:
            tokens: List of token addresses
            amounts: List of amounts in wei
            target_contract: Target contract address
            callback_data: Callback data for flash loan

        Returns:
            Transaction dictionary
        """
        async with self._lock:
            try:
                # Validate inputs
                if not tokens or not amounts:
                    raise ValueError("Empty tokens or amounts list")
                if len(tokens) != len(amounts):
                    raise ValueError("Tokens and amounts lists must have same length")
                if not target_contract:
                    raise ValueError("Target contract address required")

                # Build modes list (0 = no debt, 1 = stable, 2 = variable)
                modes = [0] * len(tokens)  # Use mode 0 for flash loans

                # Get current gas price
                gas_price = await self.w3.get_gas_price()

                # Build transaction
                tx = await self.pool_contract.functions.flashLoan(
                    tokens,          # assets
                    amounts,         # amounts
                    modes,           # modes
                    target_contract, # onBehalfOf
                    callback_data,   # params
                    0               # referralCode
                ).build_transaction({
                    'from': self.w3.wallet_address,
                    'gas': 500000,  # Estimate gas * safety margin
                    'gasPrice': gas_price,
                    'nonce': await self.w3.eth.get_nonce(self.w3.wallet_address)
                })

                return tx

            except Exception as e:
                logger.error(f"Failed to build flash loan transaction: {e}")
                raise

    async def validate_flash_loan(
        self,
        tokens: List[str],
        amounts: List[int],
        expected_profit: int
    ) -> bool:
        """
        Validate flash loan parameters.

        Args:
            tokens: List of token addresses
            amounts: List of amounts in wei
            expected_profit: Expected profit in wei

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check minimum profit
            if expected_profit < self.min_profit:
                logger.warning(
                    f"Expected profit {self.w3.w3.from_wei(expected_profit, 'ether')} ETH "
                    f"below minimum {self.w3.w3.from_wei(self.min_profit, 'ether')} ETH"
                )
                return False

            # Check token liquidity
            for token, amount in zip(tokens, amounts):
                # Get token contract
                token_contract = self.w3.contract(
                    address=token,
                    abi=[{
                        "constant": True,
                        "inputs": [{"name": "_owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "balance", "type": "uint256"}],
                        "type": "function"
                    }]
                )

                # Check pool liquidity
                pool_balance = await token_contract.functions.balanceOf(
                    self.pool_address
                ).call()

                if pool_balance < amount:
                    logger.warning(
                        f"Insufficient liquidity in pool for token {token}: "
                        f"need {self.w3.w3.from_wei(amount, 'ether')} but have "
                        f"{self.w3.w3.from_wei(pool_balance, 'ether')}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating flash loan: {e}")
            return False

    async def close(self):
        """Clean up resources."""
        pass  # No cleanup needed for Aave flash loans

async def create_aave_flash_loan(
    w3: Web3Client,
    config: Dict[str, Any]
) -> AaveFlashLoan:
    """
    Create and initialize an AaveFlashLoan instance.

    Args:
        w3: Web3 client instance
        config: Configuration dictionary

    Returns:
        Initialized AaveFlashLoan instance
    """
    try:
        # Validate configuration
        if not config.get('flash_loan', {}).get('aave_pool'):
            raise ValueError("Aave pool address not configured")

        # Create instance
        flash_loan = AaveFlashLoan(
            w3=w3,
            pool_address=config['flash_loan']['aave_pool'],
            min_profit=int(config.get('flash_loan', {}).get('min_profit', '0'))
        )

        logger.info("Aave flash loan manager created successfully")
        return flash_loan

    except Exception as e:
        logger.error(f"Failed to create Aave flash loan manager: {e}")
        raise