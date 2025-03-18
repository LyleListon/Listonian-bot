"""
Web3 interaction layer.

This module provides:
1. Provider management
2. Contract interactions
3. Transaction handling
4. Gas estimation
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from web3 import Web3
from web3.contract import Contract
from web3.types import TxParams, EventData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ABI_DIR = Path(__file__).parent.parent.parent / 'abi'
MULTICALL_ADDRESS = "0xcA11bde05977b3631167028862bE2a173976CA11"

class Web3Manager:
    """Manages Web3 provider and interactions."""
    
    def __init__(self, rpc_url: str, chain_id: int):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self._lock = asyncio.Lock()
        self._contract_cache: Dict[str, Contract] = {}
    
    async def get_block_number(self) -> int:
        """Get current block number."""
        return await self.web3.eth.get_block_number()
    
    async def get_balance(self, address: str) -> int:
        """Get account balance."""
        return await self.web3.eth.get_balance(address)

async def load_contract(
    address: str,
    abi_name: str,
    web3: Optional[Web3] = None
) -> Contract:
    """Load contract from ABI."""
    # Validate address
    if not Web3.is_address(address):
        raise ValueError(f"Invalid address: {address}")
    
    # Load ABI
    abi_path = ABI_DIR / f"{abi_name}.json"
    if not abi_path.exists():
        raise FileNotFoundError(f"ABI not found: {abi_name}")
    
    with open(abi_path) as f:
        abi = json.load(f)
    
    # Create contract
    if web3 is None:
        web3 = Web3(Web3.HTTPProvider(os.getenv('RPC_URL')))
    
    contract = web3.eth.contract(
        address=Web3.to_checksum_address(address),
        abi=abi
    )
    
    return contract

async def build_transaction(params: TxParams) -> Dict[str, Any]:
    """Build EIP-1559 transaction."""
    # Ensure required fields
    required_fields = ['from', 'to', 'value']
    for field in required_fields:
        if field not in params:
            raise ValueError(f"Missing required field: {field}")
    
    # Add EIP-1559 fields
    tx = {
        **params,
        'type': '0x2',  # EIP-1559
        'chainId': Web3.eth.chain_id
    }
    
    # Add nonce if not provided
    if 'nonce' not in tx:
        tx['nonce'] = await Web3.eth.get_transaction_count(
            tx['from'],
            'pending'
        )
    
    return tx

async def estimate_gas(
    tx_params: Dict[str, Any],
    block: Optional[str] = 'latest'
) -> int:
    """Estimate gas for transaction."""
    try:
        gas = await Web3.eth.estimate_gas(tx_params, block)
        return int(gas * 1.1)  # Add 10% buffer
    except Exception as e:
        logger.error(f"Gas estimation failed: {e}")
        raise

async def setup_event_filter(
    contract: Contract,
    event_name: str,
    from_block: Union[int, str] = 'latest',
    to_block: Union[int, str] = 'latest',
    argument_filters: Optional[Dict[str, Any]] = None
) -> Any:
    """Setup event filter."""
    try:
        event = getattr(contract.events, event_name)
        return event.create_filter(
            fromBlock=from_block,
            toBlock=to_block,
            argument_filters=argument_filters or {}
        )
    except Exception as e:
        logger.error(f"Failed to setup event filter: {e}")
        raise

async def batch_call(
    calls: List[Dict[str, str]],
    block: Optional[Union[str, int]] = 'latest'
) -> List[bytes]:
    """Execute multiple calls in single transaction."""
    multicall = await load_contract(
        MULTICALL_ADDRESS,
        'Multicall'
    )
    
    try:
        results = await multicall.functions.aggregate(calls).call(
            block_identifier=block
        )
        return results[1]  # [1] contains return data
    except Exception as e:
        logger.error(f"Multicall failed: {e}")
        raise

def handle_web3_error(error: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Web3 errors."""
    error_types = {
        3: 'RevertError',
        -32000: 'InvalidInput',
        -32001: 'ResourceNotFound',
        -32002: 'ResourceUnavailable',
        -32003: 'TransactionRejected',
        -32004: 'MethodNotFound',
        -32005: 'NetworkError',
        -32006: 'InvalidParams'
    }
    
    code = error.get('code', 0)
    message = error.get('message', 'Unknown error')
    
    return {
        'type': error_types.get(code, 'UnknownError'),
        'code': code,
        'message': message
    }

def validate_address(address: str) -> bool:
    """Validate Ethereum address checksum."""
    try:
        checksum_address = Web3.to_checksum_address(address)
        return checksum_address == address
    except ValueError:
        return False

# Initialize Web3 manager
def get_web3_manager(
    rpc_url: Optional[str] = None,
    chain_id: Optional[int] = None
) -> Web3Manager:
    """Get Web3 manager instance."""
    if rpc_url is None:
        rpc_url = os.getenv('RPC_URL')
    if chain_id is None:
        chain_id = int(os.getenv('CHAIN_ID', 1))
    
    return Web3Manager(rpc_url, chain_id)