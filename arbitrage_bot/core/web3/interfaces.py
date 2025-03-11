"""
Web3 Interface Module

This module provides interfaces and wrappers for web3.py functionality.
"""

from typing import Any, Dict, Optional, Protocol, TypedDict, List, Union
from eth_typing import ChecksumAddress, HexStr

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

    def contract(self, address: ChecksumAddress, abi: Dict[str, Any]) -> Contract:
        """Create contract instance."""
        raise NotImplementedError

class ContractFunctionWrapper:
    """Wrapper for web3.py contract functions to ensure proper async/await."""
    
    def __init__(self, contract_function: Any):
        """
        Initialize wrapper.

        Args:
            contract_function: Web3.py contract function
        """
        self._function = contract_function

    async def call(self, *args, **kwargs) -> Any:
        """
        Call contract function asynchronously.

        Returns:
            Function result
        """
        result = self._function.call(*args, **kwargs)
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

    @property
    def functions(self) -> Any:
        """
        Get contract functions.

        Returns:
            Contract functions object
        """
        return ContractFunctionsWrapper(self._contract.functions)

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
    
    def __init__(self, functions: Any):
        """
        Initialize wrapper.

        Args:
            functions: Web3.py contract functions object
        """
        self._functions = functions

    def __getattr__(self, name: str) -> ContractFunctionWrapper:
        """
        Get contract function by name.

        Args:
            name: Function name

        Returns:
            Wrapped contract function
        """
        function = getattr(self._functions, name)
        return ContractFunctionWrapper(function)

class Web3ClientWrapper:
    """Wrapper for web3.py client to ensure proper async/await."""
    
    def __init__(self, w3: Any):
        """
        Initialize wrapper.

        Args:
            w3: Web3.py client
        """
        self._w3 = w3

    @property
    def eth(self) -> Any:
        """
        Get eth module.

        Returns:
            Eth module
        """
        return self._w3.eth

    def contract(self, address: ChecksumAddress, abi: Dict[str, Any]) -> ContractWrapper:
        """
        Create contract instance.

        Args:
            address: Contract address
            abi: Contract ABI

        Returns:
            Wrapped contract instance
        """
        contract = self._w3.eth.contract(address=address, abi=abi)
        return ContractWrapper(contract)
