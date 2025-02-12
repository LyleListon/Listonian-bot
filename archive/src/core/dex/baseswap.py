"""BaseSwap V2 DEX implementation."""

import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import logging
from web3.types import TxReceipt

from .base_dex_v2 import BaseDEXV2
from ..web3.web3_manager import Web3Manager
from .utils import (
    validate_config,
    estimate_gas_cost,
    calculate_price_impact,
    get_common_base_tokens
)

logger = logging.getLogger(__name__)

# Increase recursion limit
sys.setrecursionlimit(10000)

class BaseSwapDEX(BaseDEXV2):
    """Implementation of BaseSwap V2 DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize BaseSwap V2 interface."""
        # BaseSwap uses 0.3% fee by default
        config['fee'] = config.get('fee', 3000)
        
        # Validate config
        is_valid, error = validate_config(config, {
            'router': str,
            'factory': str,
            'fee': int
        })
        if not is_valid:
            raise ValueError(f"Invalid config: {error}")
            
        super().__init__(web3_manager, config)
        self.name = "BaseSwap"

    async def _retry_async(self, fn, *args, retries=3, delay=1, **kwargs):
        """Helper method to retry async operations with exponential backoff."""
        last_error = None
        for attempt in range(retries):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt == retries - 1:  # Last attempt
                    raise last_error
                wait_time = delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

    async def _get_token_decimals(self, token_address: str) -> int:
        """Get token decimals with retry logic."""
        contract = self.w3.eth.contract(
            address=token_address,
            abi=self.web3_manager.load_abi('ERC20')
        )
        return await self._retry_async(contract.functions.decimals().call)

    async def get_reserves(self, token0: str, token1: str) -> Optional[Dict[str, int]]:
        """
        Get reserves for a token pair.
        
        Args:
            token0: First token address
            token1: Second token address
            
        Returns:
            Optional[Dict[str, int]]: Reserve details including:
                - reserve0: Reserve of first token
                - reserve1: Reserve of second token
                - timestamp: Last update timestamp
        """
        try:
            # Get pair address
            pair_address = await self._retry_async(self.factory.functions.getPair(token0, token1).call)
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return None
                
            # Get pair contract
            pair_contract = self.w3.eth.contract(
                address=pair_address,
                abi=self.pair_abi
            )
            
            # Get reserves
            reserves = await self._retry_async(pair_contract.functions.getReserves().call)
            token0_addr = await self._retry_async(pair_contract.functions.token0().call)
            token1_addr = await self._retry_async(pair_contract.functions.token1().call)
            
            # Get token decimals
            token0_decimals, token1_decimals = await asyncio.gather(
                self._get_token_decimals(token0_addr),
                self._get_token_decimals(token1_addr)
            )
            
            # Log successful fetch
            logger.debug(
                f"Got reserves for {token0_addr}/{token1_addr}:\n"
                f"  Reserve0: {reserves[0]} (decimals: {token0_decimals})\n"
                f"  Reserve1: {reserves[1]} (decimals: {token1_decimals})"
            )
            
            # Determine which reserve corresponds to which token
            if token0_addr.lower() == token0.lower():
                reserve0 = Decimal(reserves[0]) / Decimal(10 ** token0_decimals)
                reserve1 = Decimal(reserves[1]) / Decimal(10 ** token1_decimals)
            else:
                reserve0 = Decimal(reserves[1]) / Decimal(10 ** token1_decimals)
                reserve1 = Decimal(reserves[0]) / Decimal(10 ** token0_decimals)
            
            return {
                'reserve0': reserve0,
                'reserve1': reserve1,
                'timestamp': reserves[2],
                'token0': token0_addr,
                'token1': token1_addr,
                'decimals': {
                    token0_addr: token0_decimals,
                    token1_addr: token1_decimals
                },
                'raw_reserve0': reserves[0],
                'raw_reserve1': reserves[1]
            }
            
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            return None

    async def get_best_path(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        max_hops: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best trading path between tokens.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in wei
            max_hops: Maximum number of hops (default: 3)
            
        Returns:
            Optional[Dict[str, Any]]: Path details including:
                - path: List of token addresses
                - amounts: Expected amounts at each hop
                - fees: Cumulative fees
                - gas_estimate: Estimated gas cost
        """
        try:
            best_path = None
            max_output = 0
            
            # Direct path
            direct_amounts = await self.get_amounts_out(
                amount_in,
                [token_in, token_out]
            )
            if direct_amounts and direct_amounts[-1] > max_output:
                max_output = direct_amounts[-1]
                best_path = {
                    'path': [token_in, token_out],
                    'amounts': direct_amounts,
                    'fees': [self.fee],
                    'gas_estimate': estimate_gas_cost([token_in, token_out], 'v2')
                }
            
            # Only try multi-hop if max_hops > 1
            if max_hops > 1:
                # Get common pairs
                common_tokens = await self.get_common_pairs()
                
                # Try paths through each common token
                for mid_token in common_tokens:
                    path = [token_in, mid_token, token_out]
                    amounts = await self.get_amounts_out(amount_in, path)
                    
                    if amounts and amounts[-1] > max_output:
                        max_output = amounts[-1]
                        best_path = {
                            'path': path,
                            'amounts': amounts,
                            'fees': [self.fee] * 2,  # Fee for each hop
                            'gas_estimate': estimate_gas_cost(path, 'v2')
                        }
            
            return best_path
            
        except Exception as e:
            self._handle_error(e, "Path finding")
            return None

    async def get_common_pairs(self) -> List[str]:
        """Get list of common base tokens for routing."""
        return get_common_base_tokens()

    async def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Get quote including price impact and liquidity depth analysis.
        
        Args:
            amount_in: Input amount in wei
            path: List of token addresses in the swap path
            
        Returns:
            Optional[Dict[str, Any]]: Quote details including:
                - amount_in: Input amount
                - amount_out: Expected output amount
                - price_impact: Estimated price impact percentage
                - liquidity_depth: Available liquidity
                - fee_rate: DEX fee rate
                - estimated_gas: Estimated gas cost
                - min_out: Minimum output with slippage
        """
        try:
            # Get reserves
            reserves = await self.get_reserves(path[0], path[1])
            if not reserves:
                return None
                
            # Get amounts out
            amounts = await self.get_amounts_out(amount_in, path)
            if not amounts or len(amounts) < 2:
                return None
                
            amount_out = amounts[1]
            
            # Calculate price impact using shared utility
            price_impact = calculate_price_impact(
                amount_in=amount_in,
                amount_out=amount_out,
                reserve_in=reserves['reserve0'],
                reserve_out=reserves['reserve1']
            )
            
            return {
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price_impact': price_impact,
                'liquidity_depth': min(reserves['reserve0'], reserves['reserve1']),
                'fee_rate': self.fee / 1000000,  # Convert from basis points
                'estimated_gas': estimate_gas_cost(path, 'v2'),
                'min_out': int(amount_out * 0.995)  # 0.5% slippage default
            }
            
        except Exception as e:
            self._handle_error(e, "V2 quote calculation")
            return None

    async def estimate_gas_cost(self, path: List[str]) -> int:
        """
        Estimate gas cost for a swap path.
        
        Args:
            path: List of token addresses in the swap path
            
        Returns:
            int: Estimated gas cost in wei
        """
        return estimate_gas_cost(path, 'v2')
        
    async def get_24h_volume(self, token0: str, token1: str) -> float:
        """Get 24h trading volume for a token pair."""
        try:
            # Get pair address
            pair_address = await self.factory.functions.getPair(token0, token1).call()
            if pair_address == "0x0000000000000000000000000000000000000000":
                return 0.0
                
            # Get pair contract
            pair = self.w3.eth.contract(
                address=pair_address,
                abi=self.pair_abi
            )
            
            # Get events from last 24h
            now = datetime.now()
            day_ago = now - timedelta(days=1)
            
            # Get Swap events
            block_number = await self.w3.eth.block_number
            events = await pair.events.Swap.get_logs(
                fromBlock=block_number - 7200,  # Last ~24h of blocks
                toBlock='latest'
            )
            
            # Sum volumes
            volume = 0
            for event in events:
                # Use larger of amount0In/Out
                volume0 = max(event['args']['amount0In'], event['args']['amount0Out'])
                volume1 = max(event['args']['amount1In'], event['args']['amount1Out'])
                volume += volume0 + volume1
                
            return float(volume)
            
        except Exception as e:
            logger.error(f"Failed to get 24h volume: {e}")
            return 0.0
            
    async def get_trades(self, token_address: str) -> List[Dict[str, Any]]:
        """Get trade history for a token."""
        try:
            trades = []
            
            # Get all pairs with this token
            pairs = []
            pair_count = await self.factory.functions.allPairsLength().call()
            
            for i in range(pair_count):
                pair_address = await self.factory.functions.allPairs(i).call()
                pair = self.w3.eth.contract(address=pair_address, abi=self.pair_abi)
                
                token0 = await pair.functions.token0().call()
                token1 = await pair.functions.token1().call()
                
                if token0.lower() == token_address.lower() or token1.lower() == token_address.lower():
                    pairs.append(pair)
                    
            # Get Swap events from all pairs
            for pair in pairs:
                events = await pair.events.Swap.get_logs(
                    fromBlock=self.w3.eth.block_number - 7200,
                    toBlock='latest'
                )
                
                for event in events:
                    # Calculate profit/loss
                    token0_amount = event['args']['amount0Out'] - event['args']['amount0In']
                    token1_amount = event['args']['amount1Out'] - event['args']['amount1In']
                    
                    # Use the token amount that matches our token
                    token0 = await pair.functions.token0().call()
                    amount = token0_amount if token0.lower() == token_address.lower() else token1_amount
                    
                    trades.append({
                        'timestamp': (await self.w3.eth.get_block(event['blockNumber']))['timestamp'],
                        'amount': abs(float(amount)),
                        'profit': float(amount) if amount > 0 else 0.0,
                        'tx_hash': event['transactionHash'].hex(),
                        'block_number': event['blockNumber']
                    })
                    
            return sorted(trades, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []

