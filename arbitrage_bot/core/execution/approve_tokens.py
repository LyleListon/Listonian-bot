"""
Token Approval Module

Handles token approvals for DEX interactions with enhanced error handling
and logging mechanisms.
"""

import logging
import json
from typing import Dict, Any
from web3 import Web3
from eth_account.messages import encode_defunct
from eth_utils import to_bytes, remove_0x_prefix
from hexbytes import HexBytes

from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)


async def approve_token_for_dex(
    web3_manager: Web3Manager,
    token_address: str,
    router_address: str,
    private_key: str,
    erc20_abi: Dict[str, Any],
    nonce: int = None,
) -> bool:
    """
    Approve a token for trading on a DEX with proper error handling.

    Args:
        web3_manager: Web3Manager instance
        token_address: Address of the token to approve
        router_address: Address of the DEX router
        private_key: Private key for transaction signing
        erc20_abi: ABI for ERC20 token contract
        nonce: Optional nonce override

    Returns:
        bool: True if approval was successful, False otherwise
    """
    try:
        # Get account from private key
        if isinstance(private_key, str) and private_key.startswith("0x"):
            private_key = private_key[2:]
        account = web3_manager.w3.eth.account.from_key(private_key)

        # Convert addresses to checksum format
        token_address = web3_manager.w3.to_checksum_address(token_address)
        router_address = web3_manager.w3.to_checksum_address(router_address)

        # Get token contract
        token_contract = web3_manager.w3.eth.contract(
            address=token_address, abi=erc20_abi
        )

        # Check current allowance
        current_allowance = await token_contract.functions.allowance(
            account.address, router_address
        ).call()

        if current_allowance >= 2**128:
            logger.info(f"Token {token_address} already approved for {router_address}")
            return True

        # Get latest nonce if not provided
        if nonce is None:
            nonce = await web3_manager.w3.eth.get_transaction_count(account.address)

        # Get gas parameters with higher priority fee
        base_fee = await web3_manager.w3.eth.get_block("latest")
        base_fee_per_gas = base_fee["baseFeePerGas"]
        max_priority_fee_per_gas = 3_000_000_000  # 3 Gwei
        max_fee_per_gas = int(
            (base_fee_per_gas + max_priority_fee_per_gas) * 1.5
        )  # Higher multiplier

        # Build approval transaction
        approve_function = token_contract.functions.approve(
            router_address, 2**256 - 1  # max uint256
        )

        # Build transaction using contract method
        approve_tx = await approve_function.build_transaction(
            {
                "type": 2,  # EIP-1559
                "chainId": await web3_manager.w3.eth.chain_id,
                "nonce": nonce,
                "maxFeePerGas": max_fee_per_gas,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "gas": 100000,
                "from": account.address,
            }
        )

        # Sign and send transaction
        try:
            # Log transaction parameters for debugging
            logger.info(
                f"Transaction parameters: {json.dumps(approve_tx, indent=2, default=str)}"
            )

            # Sign transaction
            signed_tx = web3_manager.w3.eth.account.sign_transaction(
                approve_tx, private_key=f"0x{private_key}"
            )

            # Send raw transaction
            tx_hash = await web3_manager.w3.eth.send_raw_transaction(
                signed_tx.raw_transaction
            )
            logger.info(f"Approval transaction sent: {tx_hash.hex()}")

            # Wait for receipt
            receipt = await web3_manager.w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] == 1:
                logger.info(
                    f"Successfully approved token {token_address} for {router_address}"
                )
                return True
            else:
                logger.error(f"Approval transaction failed for token {token_address}")
                return False

        except Exception as e:
            if "replacement transaction underpriced" in str(e):
                # Try again with higher gas price and same nonce
                logger.warning(
                    f"Transaction underpriced, retrying with higher gas price"
                )
                return await approve_token_for_dex(
                    web3_manager,
                    token_address,
                    router_address,
                    private_key,
                    erc20_abi,
                    nonce=nonce,  # Keep same nonce
                )
            logger.error(f"Transaction signing failed: {str(e)}")
            logger.error(
                f"Transaction parameters: {json.dumps(approve_tx, indent=2, default=str)}"
            )
            return False

    except Exception as e:
        logger.error(f"Failed to approve token {token_address}: {str(e)}")
        return False


async def setup_all_approvals(
    web3_manager: Web3Manager,
    tokens: Dict[str, Any],
    dexes: Dict[str, Any],
    private_key: str,
) -> bool:
    """
    Set up approvals for all tokens across all DEXes.

    Args:
        web3_manager: Web3Manager instance
        tokens: Dictionary of token configurations
        dexes: Dictionary of DEX configurations
        private_key: Private key for transaction signing

    Returns:
        bool: True if all approvals were successful, False otherwise
    """
    try:
        # Load ERC20 ABI
        with open("abi/ERC20.json", "r") as f:
            erc20_abi = json.load(f)

        success = True
        # Get starting nonce
        if isinstance(private_key, str) and private_key.startswith("0x"):
            private_key = private_key[2:]
        account = web3_manager.w3.eth.account.from_key(private_key)
        nonce = await web3_manager.w3.eth.get_transaction_count(account.address)

        for token_name, token_config in tokens.items():
            token_address = token_config.get("address")
            if not token_address:
                continue

            for dex_name, dex_config in dexes.items():
                router_address = dex_config.get("router")
                if not router_address:
                    continue

                approval_success = await approve_token_for_dex(
                    web3_manager,
                    token_address,
                    router_address,
                    private_key,
                    erc20_abi,
                    nonce=nonce,
                )

                if approval_success:
                    nonce += 1  # Increment nonce only on success
                else:
                    logger.error(f"Failed to approve {token_name} for {dex_name}")
                    success = False

        return success

    except Exception as e:
        logger.error(f"Failed to set up token approvals: {str(e)}")
        return False
