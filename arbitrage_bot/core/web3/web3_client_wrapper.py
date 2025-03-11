"""
Web3 Client Wrapper Module

This module provides a wrapper around Web3.py client to ensure proper async/await usage.
"""

import logging
from typing import Any, Dict, Optional, Union, List, Tuple
from eth_typing import ChecksumAddress
from web3 import Web3

from .errors import Web3Error

logger = logging.getLogger(__name__)

def _parse_hex_value(value: Union[str, Dict[str, Any]], key: str = "result") -> int:
    """
    Parse hex value from response.
    
    Args:
        value: Response value
        key: Key to extract from dict response
        
    Returns:
        Parsed integer value
        
    Raises:
        ValueError: If value cannot be parsed
    """
    try:
        if isinstance(value, dict):
            hex_value = value.get(key)
            if not hex_value:
                raise ValueError(f"Missing {key} in response: {value}")
        else:
            hex_value = value
            
        if not isinstance(hex_value, str):
            raise ValueError(f"Expected hex string, got {type(hex_value)}")
            
        if not hex_value.startswith("0x"):
            raise ValueError(f"Invalid hex format: {hex_value}")
            
        return int(hex_value, 16)
    except (ValueError, TypeError, AttributeError) as e:
        raise ValueError(f"Failed to parse hex value: {e}")

def _format_response(response: Any, method: str) -> Any:
    """Format response based on method type."""
    if method in ["eth_getBlockByNumber", "eth_getBlockByHash", "eth_getTransactionReceipt"]:
        if isinstance(response, dict) and "result" in response:
            return response["result"]
        return response
    return response.get("result") if isinstance(response, dict) else response


class Web3ClientWrapper:
    """Wrapper for Web3.py client to ensure proper async/await."""

    def __init__(self, w3: Web3):
        """
        Initialize wrapper.

        Args:
            w3: Web3.py client
        """
        self._w3 = w3
        self._request_id = 0

    @property
    def eth(self) -> Any:
        """
        Get eth module.

        Returns:
            Eth module
        """
        return self._w3.eth

    async def get_balance(self, address: ChecksumAddress) -> int:
        """
        Get ETH balance for address.

        Args:
            address: Address to check

        Returns:
            Balance in wei
        """
        try:
            response = await self._w3.provider.make_request(
                "eth_getBalance",
                [address, "latest"]
            )
            return _parse_hex_value(response)
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            raise Web3Error(
                str(e),
                "balance_error",
                {
                    "address": address
                }
            )

    async def get_gas_price(self) -> int:
        """
        Get current gas price.

        Returns:
            Gas price in wei
        """
        try:
            response = await self._w3.provider.make_request(
                "eth_gasPrice",
                []
            )
            return _parse_hex_value(response)
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            raise Web3Error(
                str(e),
                "gas_price_error",
                {
                    "method": "eth_gasPrice"
                }
            )

    async def get_block(self, block_identifier: Union[str, int], full_transactions: bool = False) -> Dict[str, Any]:
        """
        Get block by number or hash.

        Args:
            block_identifier: Block number, hash, or 'latest'
            full_transactions: If True, return full transaction objects instead of hashes

        Returns:
            Block data as a dictionary
        """
        try:
            if isinstance(block_identifier, int):
                block_identifier = hex(block_identifier)

            response = await self._w3.provider.make_request(
                "eth_getBlockByNumber",
                [block_identifier, full_transactions]
            )

            result = _format_response(response, "eth_getBlockByNumber")
            if not result:
                raise ValueError(f"No block data returned for {block_identifier}")
            return result

        except Exception as e:
            logger.error(f"Failed to get block {block_identifier}: {e}")
            raise Web3Error(
                str(e),
                "block_error",
                {"block_identifier": block_identifier}
            )

    async def get_block_number(self) -> int:
        """
        Get current block number.

        Returns:
            Block number
        """
        try:
            response = await self._w3.provider.make_request(
                "eth_blockNumber",
                []
            )
            return _parse_hex_value(response)
        except Exception as e:
            logger.error(f"Failed to get block number: {e}")
            raise Web3Error(
                str(e),
                "block_number_error",
                {
                    "method": "eth_blockNumber"
                }
            )

    async def get_transaction_count(
        self,
        address: ChecksumAddress,
        block_identifier: Optional[Union[str, int]] = "latest"
    ) -> int:
        """
        Get transaction count (nonce) for address.

        Args:
            address: Address to check
            block_identifier: Block number, hash, or 'latest'

        Returns:
            Transaction count
        """
        try:
            if isinstance(block_identifier, int):
                block_identifier = hex(block_identifier)

            response = await self._w3.provider.make_request(
                "eth_getTransactionCount",
                [address, block_identifier]
            )
            return _parse_hex_value(response)
        except Exception as e:
            logger.error(f"Failed to get transaction count for {address}: {e}")
            raise Web3Error(
                str(e),
                "transaction_count_error",
                {
                    "address": address,
                    "block_identifier": block_identifier
                }
            )

    async def send_raw_transaction(self, transaction: str) -> str:
        """
        Send raw transaction.

        Args:
            transaction: Raw transaction data

        Returns:
            Transaction hash
        """
        try:
            response = await self._w3.provider.make_request(
                "eth_sendRawTransaction",
                [transaction]
            )
            return _format_response(response, "eth_sendRawTransaction")
        except Exception as e:
            logger.error(f"Failed to send raw transaction: {e}")
            raise Web3Error(
                str(e),
                "send_transaction_error",
                {
                    "transaction": transaction[:10] + "..."  # Truncate for logging
                }
            )

    async def get_transaction_receipt(self, transaction_hash: str) -> Dict[str, Any]:
        """
        Get transaction receipt.

        Args:
            transaction_hash: Transaction hash

        Returns:
            Transaction receipt
        """
        try:
            response = await self._w3.provider.make_request(
                "eth_getTransactionReceipt",
                [transaction_hash]
            )
            return _format_response(response, "eth_getTransactionReceipt")
        except Exception as e:
            logger.error(f"Failed to get transaction receipt for {transaction_hash}: {e}")
            raise Web3Error(
                str(e),
                "transaction_receipt_error",
                {
                    "transaction_hash": transaction_hash
                }
            )

    async def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """
        Estimate gas for transaction.

        Args:
            transaction: Transaction dictionary

        Returns:
            Gas estimate
        """
        try:
            response = await self._w3.provider.make_request(
                "eth_estimateGas",
                [transaction]
            )
            return _parse_hex_value(response)
        except Exception as e:
            logger.error(f"Failed to estimate gas: {e}")
            raise Web3Error(
                str(e),
                "gas_estimate_error",
                {
                    "transaction": transaction
                }
            )

    async def call(
        self,
        transaction: Dict[str, Any],
        block_identifier: Optional[Union[str, int]] = "latest"
    ) -> str:
        """
        Call contract function.

        Args:
            transaction: Transaction dictionary
            block_identifier: Block number, hash, or 'latest'

        Returns:
            Function result
        """
        try:
            if isinstance(block_identifier, int):
                block_identifier = hex(block_identifier)

            response = await self._w3.provider.make_request(
                "eth_call",
                [transaction, block_identifier]
            )
            return _format_response(response, "eth_call")
        except Exception as e:
            logger.error(f"Failed to call contract: {e}")
            raise Web3Error(
                str(e),
                "contract_call_error",
                {
                    "transaction": transaction,
                    "block_identifier": block_identifier
                }
            )

    async def batch_request(self, requests: List[Tuple[str, List[Any]]]) -> List[Any]:
        """
        Execute multiple requests in a batch.
        
        Args:
            requests: List of (method, params) tuples
            
        Returns:
            List of results in same order as requests
        """
        batch_response = await self._w3.provider.make_request("eth_batchRequest", requests)
        return [_format_response(r, method) for (method, _), r in zip(requests, batch_response.get("result", []))]