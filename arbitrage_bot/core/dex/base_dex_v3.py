"""Base DEX V3 abstract class providing common functionality for V3 DEX implementations."""

from abc import abstractmethod
from typing import Dict, Any, List, Optional
from decimal import Decimal
from web3 import Web3
from web3.contract import Contract, AsyncContract
from .base_dex import BaseDEX
from ..web3.web3_manager import Web3Manager

class BaseDEXV3(BaseDEX):
    """Abstract base class for V3 DEX implementations."""

    EVENT_SIGNATURES = {
        'PoolCreated': 'PoolCreated(address,address,uint24,int24,address)',
        'Swap': 'Swap(address,address,int256,int256,uint160,uint128,int24)'
    }

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize base V3 DEX functionality."""
        super().__init__(web3_manager, config)
        self.quoter_address = config.get('quoter')
        self.quoter = None
        self.fee = config.get('fee', 3000)
        self.tick_spacing = config.get('tick_spacing', 60)

    async def initialize(self) -> bool:
        """Initialize the V3 DEX interface."""
        try:
            # Initialize router and factory contracts
            self.router = await self.web3_manager.get_contract(
                address=self.router_address,
                abi_name=self.name.lower() + "_v3_router"
            )
            self.factory = await self.web3_manager.get_contract(
                address=self.factory_address,
                abi_name=self.name.lower() + "_v3_factory"
            )

            # Initialize quoter if available
            if self.quoter_address:
                self.quoter = await self.web3_manager.get_contract(
                    address=self.quoter_address,
                    abi_name=self.name.lower() + "_v3_quoter"
                )

            self.initialized = True
            return True

        except Exception as e:
            self._handle_error(e, "V3 DEX initialization")
            return False

    def _encode_path(self, path: List[str]) -> bytes:
        """Encode path for V3 router."""
        encoded = b''
        for i, token in enumerate(path):
            encoded += Web3.to_bytes(hexstr=token)
            if i < len(path) - 1:
                encoded += self.fee.to_bytes(3, 'big')
        return encoded

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int,
        gas: Optional[int] = None,
        maxFeePerGas: Optional[int] = None,
        maxPriorityFeePerGas: Optional[int] = None
    ):
        """Execute a token swap."""
        try:
            # Validate inputs
            self._validate_state()
            self._validate_path(path)
            self._validate_amounts(amount_in, amount_out_min)

            # Encode path for V3
            encoded_path = self._encode_path(path)

            # Build transaction parameters
            params = {
                'path': encoded_path,
                'recipient': Web3.to_checksum_address(to),
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': amount_out_min
            }

            # Add gas parameters if provided
            tx_params = {}
            if gas is not None:
                tx_params['gas'] = gas
            if maxFeePerGas is not None:
                tx_params['maxFeePerGas'] = maxFeePerGas
            if maxPriorityFeePerGas is not None:
                tx_params['maxPriorityFeePerGas'] = maxPriorityFeePerGas

            # Send transaction
            tx_hash = await self.web3_manager.build_and_send_transaction(
                self.router,
                'exactInput',
                params,
                tx_params=tx_params
            )
            receipt = await self.web3_manager.wait_for_transaction(tx_hash)

            # Log transaction
            self._log_transaction(
                tx_hash.hex(),
                amount_in,
                amount_out_min,
                path,
                to
            )

            return receipt

        except Exception as e:
            self._handle_error(e, "V3 swap")

    @abstractmethod
    async def get_quote_from_quoter(self, amount_in: int, path: List[str]) -> Optional[int]:
        """Get quote from quoter contract if available."""
        pass

    @abstractmethod
    async def get_quote_with_impact(self, amount_in: int, path: List[str]) -> Optional[Dict[str, Any]]:
        """Get quote with price impact calculation."""
        pass

    @abstractmethod
    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        pass

    @abstractmethod
    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        pass

    @abstractmethod
    async def get_token_price(self, token_address: str) -> float:
        """Get current price for a token."""
        pass

    async def _get_pool_address(self, token0: str, token1: str) -> str:
        """Get pool address for token pair."""
        try:
            contract_func = self.factory.functions.getPool(
                Web3.to_checksum_address(token0),
                Web3.to_checksum_address(token1),
                self.fee
            )
            pool_address = await self.web3_manager.call_contract_function(contract_func)
            return Web3.to_checksum_address(pool_address)
        except Exception as e:
            self.logger.error("Failed to get pool address: %s", str(e))
            return "0x0000000000000000000000000000000000000000"

    async def _get_pool_contract(self, pool_address: str) -> Optional[AsyncContract]:
        """Get pool contract instance."""
        try:
            return await self.web3_manager.get_contract(
                address=pool_address,
                abi_name=self.name.lower() + "_v3_pool"
            )
        except Exception as e:
            self.logger.error("Failed to get pool contract: %s", str(e))
            return None

    async def _get_pool_liquidity(self, pool_contract: AsyncContract) -> Decimal:
        """Get pool liquidity."""
        try:
            contract_func = pool_contract.functions.liquidity()
            liquidity = await self.web3_manager.call_contract_function(contract_func)
            return Decimal(str(liquidity))  # Convert to string first to avoid float conversion issues
        except Exception as e:
            self.logger.error("Failed to get pool liquidity: %s", str(e))
            return Decimal(0)

    def _get_event_signature(self, event_name: str) -> str:
        """Get event signature."""
        if event_name not in self.EVENT_SIGNATURES:
            msg = "Unknown event: " + event_name
            raise ValueError(msg)
        signature = self.EVENT_SIGNATURES[event_name]
        return Web3.keccak(text=signature).hex()

    async def _process_log(
        self,
        event_obj: Any,
        log_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single event log."""
        try:
            # Convert numeric values in log to strings
            processed_log = {
                'address': log_dict['address'],
                'topics': log_dict['topics'],
                'data': log_dict['data'],
                'blockNumber': str(log_dict['blockNumber']),
                'transactionHash': log_dict['transactionHash'].hex() if isinstance(log_dict['transactionHash'], bytes) else log_dict['transactionHash'],
                'transactionIndex': str(log_dict['transactionIndex']),
                'blockHash': log_dict['blockHash'].hex() if isinstance(log_dict['blockHash'], bytes) else log_dict['blockHash'],
                'logIndex': str(log_dict['logIndex']),
                'removed': log_dict.get('removed', False)
            }

            # Process log using contract event
            decoded = event_obj.process_log(processed_log)

            # Convert numeric values in args to strings
            if 'args' in decoded:
                decoded['args'] = {
                    key: str(value) if isinstance(value, (int, float)) else value
                    for key, value in decoded['args'].items()
                }

            return decoded
        except Exception as e:
            self.logger.warning("Failed to process log: %s", str(e))
            raise

    async def _get_pool_events(
        self,
        pool_contract: AsyncContract,
        event_name: str,
        from_block: int,
        to_block: str = 'latest'
    ) -> List[Dict[str, Any]]:
        """Get pool events."""
        try:
            # Get event signature
            event_signature = self._get_event_signature(event_name)
            
            # Get logs using eth_getLogs
            logs = await self.web3_manager.w3.eth.get_logs({
                'address': pool_contract.address,
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [event_signature]
            })
            
            # Process logs
            events = []
            event_obj = pool_contract.events[event_name]()
            
            for log in logs:
                try:
                    # Convert log to dict for processing
                    log_dict = dict(log)
                    # Process log
                    decoded = await self._process_log(event_obj, log_dict)
                    events.append(decoded)
                except Exception as e:
                    self.logger.warning("Failed to decode log: %s", str(e))
                    continue
            
            return events
            
        except Exception as e:
            self.logger.error("Failed to get pool events: %s", str(e))
            return []
