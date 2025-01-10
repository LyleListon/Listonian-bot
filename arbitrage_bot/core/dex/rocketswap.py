"""RocketSwap DEX interface."""

import logging
from typing import Dict, Any, List
from decimal import Decimal
from web3.types import TxReceipt

from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)

class RocketSwapDEX:
    """Interface for RocketSwap DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize RocketSwap interface."""
        self.w3 = web3_manager.w3
        self.config = config
        self.router_address = config['router']
        self.factory_address = config['factory']
        self.fee = config.get('fee', 2500)  # RocketSwap uses 0.25% fee
        
        # Load contract ABIs
        self.router_abi = web3_manager.load_abi('baseswap_router')  # RocketSwap uses similar ABI
        self.factory_abi = web3_manager.load_abi('baseswap_factory')
        self.pair_abi = web3_manager.load_abi('baseswap_pair')
        
        # Initialize contracts
        self.router = self.w3.eth.contract(
            address=self.router_address,
            abi=self.router_abi
        )
        self.factory = self.w3.eth.contract(
            address=self.factory_address,
            abi=self.factory_abi
        )

    async def initialize(self) -> bool:
        """Initialize the DEX interface."""
        try:
            # Test connection to router
            await self.router.functions.factory().call()
            logger.info("RocketSwap interface initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RocketSwap: {e}")
            return False

    async def get_price(self, token0: str, token1: str) -> float:
        """Get price between two tokens."""
        try:
            # Get pair address
            pair_address = await self.factory.functions.getPair(token0, token1).call()
            if pair_address == "0x0000000000000000000000000000000000000000":
                return 0
                
            # Get pair contract
            pair = self.w3.eth.contract(address=pair_address, abi=self.pair_abi)
            
            # Get reserves
            reserves = await pair.functions.getReserves().call()
            reserve0, reserve1 = reserves[0], reserves[1]
            
            if reserve0 == 0 or reserve1 == 0:
                return 0
                
            # Calculate price (token1 per token0)
            # Apply RocketSwap's fee structure
            price = reserve1 / reserve0
            fee_multiplier = 1 - (self.fee / 10000)  # Convert basis points to percentage
            return price * fee_multiplier
            
        except Exception as e:
            logger.error(f"Failed to get RocketSwap price: {e}")
            return 0

    async def get_amounts_out(self, amount_in: int, path: List[str]) -> List[int]:
        """Get expected output amounts for a trade."""
        try:
            return await self.router.functions.getAmountsOut(amount_in, path).call()
        except Exception as e:
            logger.error(f"Failed to get RocketSwap amounts out: {e}")
            return []

    async def find_alternative_paths(
        self,
        token0: str,
        token1: str,
        max_hops: int = 3
    ) -> List[List[str]]:
        """Find alternative paths between tokens for MEV protection."""
        try:
            paths = []
            visited = set()

            async def find_paths(current: str, target: str, path: List[str], hops: int):
                if hops > max_hops:
                    return
                    
                if current == target and len(path) > 1:
                    paths.append(path[:])
                    return
                    
                # Get all pairs for current token
                pairs = await self.factory.functions.getPairsWithToken(current).call()
                for pair in pairs:
                    token = pair['token0'] if pair['token1'] == current else pair['token1']
                    if token not in visited:
                        visited.add(token)
                        path.append(token)
                        await find_paths(token, target, path, hops + 1)
                        path.pop()
                        visited.remove(token)

            # Start path finding
            visited.add(token0)
            await find_paths(token0, token1, [token0], 0)
            
            # Sort paths by total liquidity
            paths_with_liquidity = []
            for path in paths:
                liquidity = await self._get_path_liquidity(path)
                paths_with_liquidity.append((path, liquidity))
            
            # Return top paths sorted by liquidity
            sorted_paths = sorted(paths_with_liquidity, key=lambda x: x[1], reverse=True)
            return [path for path, _ in sorted_paths[:5]]  # Return top 5 paths
            
        except Exception as e:
            logger.error(f"Failed to find alternative paths: {e}")
            return []

    async def _get_path_liquidity(self, path: List[str]) -> float:
        """Get total liquidity for a path."""
        try:
            total_liquidity = 0
            for i in range(len(path) - 1):
                pair_address = await self.factory.functions.getPair(
                    path[i],
                    path[i + 1]
                ).call()
                
                if pair_address != "0x0000000000000000000000000000000000000000":
                    pair = self.w3.eth.contract(
                        address=pair_address,
                        abi=self.pair_abi
                    )
                    reserves = await pair.functions.getReserves().call()
                    total_liquidity += min(reserves[0], reserves[1])
                    
            return total_liquidity
            
        except Exception as e:
            logger.error(f"Failed to get path liquidity: {e}")
            return 0

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int,
        mev_protection: bool = True
    ) -> TxReceipt:
        """Execute a token swap with MEV protection."""
        try:
            if mev_protection:
                # Find alternative paths
                alt_paths = await self.find_alternative_paths(path[0], path[-1])
                if alt_paths:
                    # Randomly select path with preference for higher liquidity
                    from random import choices
                    weights = [1/i for i in range(1, len(alt_paths) + 1)]  # Higher weight for better paths
                    selected_path = choices(alt_paths, weights=weights, k=1)[0]
                    logger.info(f"Using alternative path for MEV protection: {selected_path}")
                    path = selected_path
                
                # Get current block for timing
                current_block = await self.w3.eth.block_number
                pending_txs = len(await self.w3.eth.get_block('pending'))
                
                # Dynamic timing based on network conditions
                if pending_txs > 20:  # High congestion
                    from asyncio import sleep
                    await sleep(2)  # Brief delay
                    deadline = current_block + 3  # Longer deadline
                else:
                    deadline = current_block + 2  # Standard deadline
                
                # Add slippage buffer for MEV protection
                amount_out_min = int(amount_out_min * 0.995)  # 0.5% additional slippage
            
            # Build transaction with MEV protection
            tx = await self.router.functions.swapExactTokensForTokens(
                amount_in,
                amount_out_min,
                path,
                to,
                deadline
            ).build_transaction({
                'from': to,
                'gas': 300000,  # RocketSwap typically needs less gas
                'nonce': await self.w3.eth.get_transaction_count(to),
                'maxFeePerGas': await self._get_dynamic_gas_price(pending_txs),
                'maxPriorityFeePerGas': await self._get_priority_fee(pending_txs)
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                private_key=self.config.get('wallet', {}).get('private_key')
            )
            tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for receipt with timeout
            receipt = await self.w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=30  # 30 second timeout
            )
            
            # Log transaction details
            logger.info(
                f"Swap executed:\n"
                f"  Path: {' -> '.join(path)}\n"
                f"  Amount In: {amount_in}\n"
                f"  Min Out: {amount_out_min}\n"
                f"  Gas Used: {receipt['gasUsed']}\n"
                f"  Block: {receipt['blockNumber']}"
            )
            
            return receipt
        except Exception as e:
            logger.error(f"Failed to execute RocketSwap swap: {e}")
            raise

    async def _get_dynamic_gas_price(self, pending_txs: int) -> int:
        """Calculate dynamic gas price based on network conditions."""
        try:
            base_fee = await self.w3.eth.gas_price
            
            # Add dynamic multiplier based on congestion
            if pending_txs > 20:  # High congestion
                multiplier = 1.1 + (pending_txs / 1000)  # Max 10% increase
            else:
                multiplier = 1.02  # 2% increase
                
            return int(base_fee * multiplier)
            
        except Exception as e:
            logger.error(f"Failed to get dynamic gas price: {e}")
            return await self.w3.eth.gas_price

    async def _get_priority_fee(self, pending_txs: int) -> int:
        """Calculate priority fee based on network conditions."""
        try:
            base_priority = await self.w3.eth.max_priority_fee
            
            # Adjust based on congestion
            if pending_txs > 20:  # High congestion
                multiplier = 1.2  # 20% increase
            else:
                multiplier = 1.1  # 10% increase
                
            return int(base_priority * multiplier)
            
        except Exception as e:
            logger.error(f"Failed to get priority fee: {e}")
            return 1500000000  # 1.5 gwei default
