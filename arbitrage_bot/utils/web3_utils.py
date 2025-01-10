"""Web3 utility functions."""

import logging
from typing import Dict, Any, Optional
from web3 import Web3
from ..core.web3.web3_manager import Web3Manager, create_web3_manager

logger = logging.getLogger(__name__)


async def get_web3(testing: bool = False) -> Web3Manager:
    """
    Get Web3 manager instance.

    Args:
        testing (bool, optional): Whether to use mock provider for testing.

    Returns:
        Web3Manager: Web3 manager instance
    """
    return await create_web3_manager()


async def get_contract(web3: Web3Manager, address: str, abi: Dict[str, Any]) -> Any:
    """
    Get contract instance.

    Args:
        web3 (Web3Manager): Web3 manager instance
        address (str): Contract address
        abi (Dict[str, Any]): Contract ABI

    Returns:
        Contract: Web3 contract instance
    """
    return await web3.get_contract(address, abi)


async def estimate_gas(web3: Web3Manager, transaction: Dict[str, Any]) -> int:
    """
    Estimate gas for transaction.

    Args:
        web3 (Web3Manager): Web3 manager instance
        transaction (Dict[str, Any]): Transaction parameters

    Returns:
        int: Estimated gas
    """
    return await web3.estimate_gas(transaction)


def validate_address(address: str) -> bool:
    """
    Validate Ethereum address.

    Args:
        address (str): Address to validate

    Returns:
        bool: True if valid
    """
    return Web3.is_address(address)


async def get_token_balance(
    web3: Web3Manager, token_address: str, wallet_address: str
) -> float:
    """
    Get token balance for address.

    Args:
        web3 (Web3Manager): Web3 manager instance
        token_address (str): Token contract address
        wallet_address (str): Wallet address

    Returns:
        float: Token balance
    """
    try:
        contract = await web3.get_contract(token_address, [])  # TODO: Add ERC20 ABI
        balance = await contract.functions.balanceOf(wallet_address).call()
        decimals = await contract.functions.decimals().call()
        return float(balance) / (10**decimals)
    except Exception as e:
        logger.error(f"Failed to get token balance: {e}")
        return 0.0


async def get_eth_balance(web3: Web3Manager, address: str) -> float:
    """
    Get ETH balance for address.

    Args:
        web3 (Web3Manager): Web3 manager instance
        address (str): Address to check

    Returns:
        float: Balance in ETH
    """
    return await web3.get_balance(address)
