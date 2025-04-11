"""
Web3 Interface Module

This module provides interfaces and wrappers for web3.py functionality.
"""

from typing import Any, Dict, Optional, Protocol, TypedDict, List, Union
from eth_typing import ChecksumAddress, HexStr
import decimal


class AccessList(TypedDict, total=False):
    """Access list for EIP-2930 transactions."""

    address: ChecksumAddress
    storageKeys: List[HexStr]


class Transaction(TypedDict, total=False):
    """Transaction dictionary type."""

    blockHash: HexStr
    blockNumber: int
    from_: ChecksumAddress  # Note: actual key is 'from'
    gas: int
    gasPrice: int
    maxFeePerGas: int
    maxPriorityFeePerGas: int
    hash: HexStr
    input: HexStr
    nonce: int
    to: ChecksumAddress
    transactionIndex: int
    value: int
    type: int
    accessList: List[AccessList]
    chainId: int
    v: int
    r: HexStr
    s: HexStr


class TransactionReceipt(TypedDict, total=False):
    """Transaction receipt dictionary type."""

    transactionHash: HexStr
    transactionIndex: int
    blockHash: HexStr
    blockNumber: int
    from_: ChecksumAddress  # Note: actual key is 'from'
    to: ChecksumAddress
    cumulativeGasUsed: int
    gasUsed: int
    contractAddress: Optional[ChecksumAddress]
    logs: List[Dict[str, Any]]
    status: int
    effectiveGasPrice: int
    type: int
    logsBloom: HexStr


class ContractFunction:
    """Interface for web3.py contract functions."""

    async def call(self, *args, **kwargs) -> Any:
        """Call contract function."""
        raise NotImplementedError


class Contract:
    """Interface for web3.py contracts."""

    @property
    def functions(self) -> Any:
        """Get contract functions."""
        raise NotImplementedError

    @property
    def address(self) -> ChecksumAddress:
        """Get contract address."""
        raise NotImplementedError


class Web3Client(Protocol):
    """Interface for web3.py client."""

    @property
    def eth(self) -> Any:
        """Get eth module."""
        raise NotImplementedError

    async def initialize(self) -> None:
        """Initialize the Web3 connection."""
        raise NotImplementedError

    async def close(self) -> None:
        """Close the Web3 connection and cleanup resources."""
        raise NotImplementedError

    def contract(self, address: ChecksumAddress, abi: Dict[str, Any]) -> Contract:
        """Create contract instance."""
        raise NotImplementedError

    async def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        raise NotImplementedError

    async def get_block(self, block_identifier: Union[str, int]) -> Dict[str, Any]:
        """Get block by number or hash."""
        raise NotImplementedError

    def to_wei(
        self, value: Union[int, float, str, decimal.Decimal], currency: str
    ) -> int:
        """Convert currency value to wei."""
        raise NotImplementedError


class ContractFunctionWrapper:
    """Wrapper for web3.py contract functions to ensure proper async/await."""

    def __init__(self, contract_function: Any, w3: Any):
        """
        Initialize wrapper.

        Args:
            contract_function: Web3.py contract function
            w3: Web3.py instance
        """
        self._function = contract_function
        self._w3 = w3
        self.address = contract_function.address

    async def call(self, *args, **kwargs) -> Any:
        """
        Call contract function asynchronously.

        Returns:
            Function result
        """
        # Make a direct RPC call to call contract function
        # First, encode the function call
        data = self._function.encode_input(*args)

        # Prepare the transaction
        tx = {"to": self.address, "data": data, **kwargs}

        # Make the call
        response = await self._w3.provider.make_request("eth_call", [tx, "latest"])
        if "error" in response:
            raise ValueError(f"Failed to call contract: {response['error']}")

        # Decode the result
        result = self._function.decode_output(response["result"])
        return result


class ContractWrapper:
    """Wrapper for web3.py contracts to ensure proper async/await."""

    def __init__(self, contract: Any):
        """
        Initialize wrapper.

        Args:
            contract: Web3.py contract
        """
        self._contract = contract
        self._w3 = contract.w3

    @property
    def functions(self) -> Any:
        """
        Get contract functions.

        Returns:
            Contract functions object
        """
        return ContractFunctionsWrapper(self._contract.functions, self._w3)

    @property
    def address(self) -> ChecksumAddress:
        """
        Get contract address.

        Returns:
            Contract address
        """
        return self._contract.address


class ContractFunctionsWrapper:
    """Wrapper for web3.py contract functions object to ensure proper async/await."""

    def __init__(self, functions: Any, w3: Any):
        """
        Initialize wrapper.

        Args:
            functions: Web3.py contract functions object
            w3: Web3.py instance
        """
        self._functions = functions
        self._w3 = w3

    def __getattr__(self, name: str) -> ContractFunctionWrapper:
        """
        Get contract function by name.

        Args:
            name: Function name

        Returns:
            Wrapped contract function
        """
        function = getattr(self._functions, name)
        return ContractFunctionWrapper(function, self._w3)
