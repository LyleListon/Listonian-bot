"""
Balancer Flash Loan Module

This module provides functionality for:
- Flash loan execution through Balancer
- Loan validation
- Repayment verification
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from eth_typing import ChecksumAddress
from web3 import Web3

from ...utils.async_manager import with_retry, AsyncLock

logger = logging.getLogger(__name__)


class BalancerFlashLoan:
    """Manages flash loans through Balancer."""

    def __init__(self, w3: Web3, vault_address: ChecksumAddress, vault_abi: Dict):
        """
        Initialize Balancer flash loan.

        Args:
            w3: Web3 instance
            vault_address: Balancer vault address
            vault_abi: Balancer vault ABI
        """
        self.w3 = w3
        self.vault_address = vault_address
        self.vault_contract = self.w3.eth.contract(address=vault_address, abi=vault_abi)
        self._lock = AsyncLock()

    @with_retry(max_attempts=3, base_delay=1.0)
    async def check_liquidity(
        self, token_address: ChecksumAddress, amount: int
    ) -> bool:
        """
        Check if enough liquidity is available.

        Args:
            token_address: Token address
            amount: Amount in wei

        Returns:
            True if enough liquidity available
        """
        try:
            pool_id = await self.vault_contract.functions.getPool(token_address).call()
            pool_balance = await self.vault_contract.functions.getPoolBalance(
                pool_id, token_address
            ).call()
            return pool_balance >= amount
        except Exception as e:
            logger.error(f"Failed to check liquidity: {e}")
            return False

    @with_retry(max_attempts=3, base_delay=1.0)
    async def estimate_fees(
        self, tokens: List[ChecksumAddress], amounts: List[int]
    ) -> int:
        """
        Estimate flash loan fees.

        Args:
            tokens: List of token addresses
            amounts: List of amounts in wei

        Returns:
            Total fees in wei
        """
        try:
            total_fees = 0
            for i, token in enumerate(tokens):
                fee = (
                    await self.vault_contract.functions.getFlashLoanFeePercentage().call()
                )
                total_fees += (amounts[i] * fee) // 10000  # Fee in basis points
            return total_fees
        except Exception as e:
            logger.error(f"Failed to estimate fees: {e}")
            return 0

    @with_retry(max_attempts=3, base_delay=1.0)
    async def simulate_flash_loan(
        self,
        tokens: List[ChecksumAddress],
        amounts: List[int],
        target_contract: ChecksumAddress,
        callback_data: bytes,
    ) -> Tuple[bool, str, Dict]:
        """
        Simulate flash loan execution.

        Args:
            tokens: List of token addresses
            amounts: List of amounts in wei
            target_contract: Contract to receive the loan
            callback_data: Data for callback function

        Returns:
            Tuple of (success, error message, simulation results)
        """
        try:
            # Validate callback data
            if not callback_data or len(callback_data) < 4:
                return False, "Invalid callback data", {}

            # Estimate gas cost
            gas_estimate = await self.vault_contract.functions.flashLoan(
                target_contract, tokens, amounts, callback_data
            ).estimate_gas({"from": target_contract})

            return (
                True,
                "",
                {
                    "gas_estimate": gas_estimate,
                    "total_fees": await self.estimate_fees(tokens, amounts),
                },
            )
        except Exception as e:
            logger.error(f"Flash loan simulation failed: {e}")
            return False, str(e), {}

    @with_retry(max_attempts=3, base_delay=1.0)
    async def build_flash_loan_tx(
        self,
        tokens: List[ChecksumAddress],
        amounts: List[int],
        target_contract: ChecksumAddress,
        callback_data: bytes,
    ) -> Dict:
        """
        Build flash loan transaction.

        Args:
            tokens: List of token addresses
            amounts: List of amounts in wei
            target_contract: Contract to receive the loan
            callback_data: Data for callback function

        Returns:
            Transaction dictionary
        """
        async with self._lock:
            try:
                # Validate inputs
                if len(tokens) != len(amounts):
                    raise ValueError("Token and amount lists must be same length")

                # Check liquidity
                for i, token in enumerate(tokens):
                    if not await self.check_liquidity(token, amounts[i]):
                        raise ValueError(f"Insufficient liquidity for {token}")

                # Simulate transaction
                success, error, sim_results = await self.simulate_flash_loan(
                    tokens, amounts, target_contract, callback_data
                )

                if not success:
                    raise ValueError(f"Flash loan simulation failed: {error}")

                gas_estimate = sim_results["gas_estimate"]

                # Build transaction
                tx = await self.vault_contract.functions.flashLoan(
                    target_contract, tokens, amounts, callback_data
                ).build_transaction(
                    {
                        "from": target_contract,
                        "gas": int(gas_estimate * 1.2),  # Add 20% buffer
                        "maxFeePerGas": self.w3.eth.gas_price,
                        "maxPriorityFeePerGas": self.w3.eth.max_priority_fee,
                    }
                )

                return tx

            except Exception as e:
                logger.error(f"Failed to build flash loan transaction: {e}")
                raise

    async def test_flash_loan(
        self,
        token_address: ChecksumAddress,
        amount: int,
        target_contract: ChecksumAddress,
    ) -> Dict:
        """
        Test flash loan functionality with minimal amount.

        Args:
            token_address: Token to borrow
            amount: Test amount in wei
            target_contract: Contract to receive loan

        Returns:
            Test results dictionary
        """
        try:
            # Use empty callback for test
            callback_data = b""

            success, error, results = await self.simulate_flash_loan(
                [token_address], [amount], target_contract, callback_data
            )

            return {"success": success, "error": error, **results}
        except Exception as e:
            logger.error(f"Flash loan test failed: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Clean up resources."""
        pass


async def create_balancer_flash_loan(w3: Web3, config: Dict) -> BalancerFlashLoan:
    """
    Create a new Balancer flash loan instance.

    Args:
        w3: Web3 instance
        config: Configuration dictionary

    Returns:
        BalancerFlashLoan instance
    """
    # Load Balancer vault ABI
    with open("abi/balancer_vault.json", "r") as f:
        vault_abi = json.loads(f.read())

    return BalancerFlashLoan(
        w3=w3, vault_address=config["flash_loan"]["balancer_vault"], vault_abi=vault_abi
    )
