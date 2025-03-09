"""BaseSwap V3 DEX implementation."""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from web3 import Web3

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager

class BaseSwapV3(BaseDEXV3):
    """BaseSwap V3 DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize BaseSwap V3 interface."""
        super().__init__(web3_manager, config)
        self.name = "BaseSwap"

    async def get_quote_from_quoter(self, amount_in: int, path: List[str]) -> Optional[int]:
        """Get quote from quoter contract if available."""
        if not self.quoter:
            return None

        try:
            # If path has more than 2 tokens, use multi-hop quote
            if len(path) > 2:
                self.logger.debug("Getting multi-hop quote for path with %d tokens", len(path))
                return await self.get_multi_hop_quote(amount_in, path)
            else:
                # Use quoteExactInputSingle for single-hop (more efficient)
                quote_result = await self.web3_manager.call_contract_function(
                    self.quoter.functions.quoteExactInputSingle,
                    Web3.to_checksum_address(path[0]),  # tokenIn
                    Web3.to_checksum_address(path[1]),  # tokenOut
                    self.fee,  # fee
                    amount_in,  # amountIn
                    0  # sqrtPriceLimitX96 (0 for no limit)
                )
                # Return just the amount_out from the tuple
                return quote_result[0] if isinstance(quote_result, (list, tuple)) else quote_result

        except Exception as e:
            # Log more context about the path
            path_str = "->".join([token[:8] + "..." + token[-6:] for token in path])
            self.logger.error("Failed to get quote for path %s: %s", path_str, str(e))
            return None
    
    async def estimate_swap_gas(self, token_in: str, token_out: str, amount_in: int) -> int:
        """Estimate gas cost for a swap."""
        try:
            path = [token_in, token_out]
            return 150000  # Standard estimate for single hop
        except Exception as e:
            self.logger.error("Failed to estimate swap gas: %s", str(e))
            return 200000  # Return a conservative estimate
            
    async def estimate_multi_hop_swap_gas(self, path: List[str], amount_in: int) -> int:
        """Estimate gas cost for a multi-hop swap."""
        try:
            # Estimate based on number of hops
            # Base cost (150k) + 50k per additional hop
            return await self.get_multi_hop_gas_estimate(path)
        except Exception as e:
            self.logger.error("Failed to estimate multi-hop swap gas: %s", str(e))
            return 250000  # Return a conservative estimate

    async def find_best_path(self, token_in: str, token_out: str, amount_in: int, 
                           max_hops: int = 3) -> Optional[Dict[str, Any]]:
        """
        Find the best path between two tokens, considering multi-hop routes.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in token units
            max_hops: Maximum number of hops to consider
        
        Returns:
            Dictionary with best path information or None if no path found
        """
        try:
            self.logger.info("Finding best path from %s to %s", token_in[:8], token_out[:8])
            
            # Get common tokens to use as intermediate hops
            common_tokens = await self.get_supported_tokens()
            if not common_tokens:
                # Fallback to direct swap
                amount_out = await self.get_quote_from_quoter(amount_in, [token_in, token_out])
                if amount_out:
                    return {
                        'path': [token_in, token_out],
                        'amount_out': amount_out,
                        'gas_estimate': 150000
                    }
                return None
                
            # Start with direct path
            best_path = None
            best_amount_out = 0
            
            # Try direct swap first
            direct_amount = await self.get_quote_from_quoter(amount_in, [token_in, token_out])
            if direct_amount:
                best_path = [token_in, token_out]
                best_amount_out = direct_amount
                
            # Try 2-hop paths (A->B->C)
            if max_hops >= 2:
                for intermediate in common_tokens:
                    # Skip if intermediate is the same as input or output
                    if intermediate.lower() in [token_in.lower(), token_out.lower()]:
                        continue
                        
                    # Try path: token_in -> intermediate -> token_out
                    path = [token_in, intermediate, token_out]
                    try:
                        amount_out = await self.get_quote_from_quoter(amount_in, path)
                        if amount_out and amount_out > best_amount_out:
                            best_path = path
                            best_amount_out = amount_out
                    except Exception as e:
                        self.logger.debug("Error checking 2-hop path %s: %s", 
                                         "->".join([t[:6] for t in path]), str(e))
                        continue
                        
            # Try 3-hop paths (A->B->C->D) if requested
            if max_hops >= 3:
                for intermediate1 in common_tokens:
                    # Skip if intermediate1 is the same as input or output
                    if intermediate1.lower() in [token_in.lower(), token_out.lower()]:
                        continue
                        
                    for intermediate2 in common_tokens:
                        # Skip if intermediate2 is the same as any other token
                        if intermediate2.lower() in [token_in.lower(), token_out.lower(), 
                                                  intermediate1.lower()]:
                            continue
                            
                        # Try path: token_in -> intermediate1 -> intermediate2 -> token_out
                        path = [token_in, intermediate1, intermediate2, token_out]
                        try:
                            amount_out = await self.get_quote_from_quoter(amount_in, path)
                            if amount_out and amount_out > best_amount_out:
                                best_path = path
                                best_amount_out = amount_out
                        except Exception as e:
                            # Just debug level for these errors as they're expected
                            self.logger.debug("Error checking 3-hop path %s: %s", 
                                             "->".join([t[:6] for t in path]), str(e))
                            continue
            
            if best_path:
                # Get gas estimate based on path length
                gas_estimate = 150000 if len(best_path) == 2 else await self.get_multi_hop_gas_estimate(best_path)
                
                return {
                    'path': best_path,
                    'amount_out': best_amount_out,
                    'gas_estimate': gas_estimate
                }
                
            return None
            
        except Exception as e:
            self.logger.error("Failed to get quote: %s", str(e))
            return None

    async def get_quote_with_impact(self, amount_in: int, path: List[str]) -> Optional[Dict[str, Any]]:
        """Get quote with price impact calculation."""
        try:
            # Get quote from quoter
            self.logger.debug("Getting quote with impact for path of length %d", len(path))
            
            # Handle multi-hop paths
            if len(path) > 2:
                # For multi-hop paths, we calculate impact based on full path
                amount_out = await self.get_quote_from_quoter(amount_in, path)
                self.logger.debug("Multi-hop quote amount_out: %s", amount_out)
                if not amount_out:
                    self.logger.warning("Failed to get quote for amount_in: %s, path length: %d", 
                                      amount_in, len(path))
                    return None
                    
                # Calculate price impact by comparing large vs small amount
                small_amount = amount_in // 1000 if amount_in > 1000 else amount_in
                baseline_out = await self.get_quote_from_quoter(small_amount, path)
                
                # Calculate gas estimate based on path length
                gas_estimate = await self.get_multi_hop_gas_estimate(path)
                
            else:
                # Original logic for single-hop paths
                amount_out = await self.get_quote_from_quoter(amount_in, path)
                self.logger.debug("Quote amount_out: %s", amount_out)
                if not amount_out:
                    self.logger.warning("Failed to get quote for amount_in: %s, path: %s", amount_in, path)
                    return None

                # Calculate price impact
                # Use a smaller amount to get baseline price
                small_amount = amount_in // 1000 if amount_in > 1000 else amount_in
                baseline_out = await self.get_quote_from_quoter(small_amount, path)
                self.logger.debug("Baseline quote amount_out: %s", baseline_out)
                if not baseline_out:
                    self.logger.warning("Failed to get baseline quote for amount_in: %s, path: %s", small_amount, path)
                    return None
                    
                # Get gas estimate for single hop
                gas_estimate = 150000

            # Calculate impact and validate
            try:
                impact = 1 - (amount_out * small_amount) / (baseline_out * amount_in)
                if impact < -1 or impact > 1:
                    self.logger.warning("Invalid price impact calculated: %s", impact)
                    return None
            except ZeroDivisionError:
                self.logger.error("Division by zero when calculating price impact")
                return None

            return {
                'amount_out': amount_out,
                'impact': float(impact),  # Convert to float for JSON serialization
                'fee_rate': float(self.fee) / 1000000,  # Convert to float to avoid decimal division
                'fee': self.fee,  # Include raw fee value
                'path': path,  # Include the full path
                'estimated_gas': gas_estimate  # Use actual gas estimate from quoter
            }

        except Exception as e:
            self.logger.error("Failed to get quote with impact: %s", str(e))
            return None

    async def get_token_price(self, token_address: str) -> float:
        """Get current price for a token."""
        try:
            # If token is WETH, return 1.0 since price is in WETH
            if token_address.lower() == self.weth_address.lower():
                return 1.0

            # Get quote for 1 token worth of WETH
            amount_in = 10**18  # 1 WETH
            quote = await self.get_quote_from_quoter(
                amount_in,
                [self.weth_address, token_address]
            )

            if quote:
                # Convert quote to float after ensuring it's a number
                quote_value = float(quote) if isinstance(quote, (int, float, str, Decimal)) else 0
                return quote_value / (10**18)

            return 0.0

        except Exception as e:
            self.logger.error("Failed to get token price: %s", str(e))
            return 0.0

    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        try:
            # Get pool address
            pool_address = await self._get_pool_address(token0, token1)
            if pool_address == "0x0000000000000000000000000000000000000000":
                return Decimal(0)

            # Get pool contract
            pool = await self._get_pool_contract(pool_address)
            if not pool:
                return Decimal(0)

            # Get volume from Swap events in last 24h
            current_block = await self.web3_manager.w3.eth.block_number
            from_block = current_block - 7200  # ~24h of blocks

            # Get events
            events = await self._get_pool_events(pool, 'Swap', from_block)

            # Calculate volume
            volume = Decimal(0)
            for event in events:
                amount0 = abs(Decimal(event['args']['amount0']))
                amount1 = abs(Decimal(event['args']['amount1']))
                volume += max(amount0, amount1)

            return volume

        except Exception as e:
            self.logger.error("Failed to get 24h volume: %s", str(e))
            return Decimal(0)

    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        try:
            total_liquidity = Decimal(0)

            # Get event signature
            event_abi = next(e for e in self.factory.abi if e['type'] == 'event' and e['name'] == 'PoolCreated')
            event_topic = Web3.keccak(text=event_abi['name']).hex()

            # Get logs
            logs = await self.web3_manager.w3.eth.get_logs({
                'address': self.factory_address,
                'fromBlock': 0,
                'toBlock': 'latest',
                'topics': [event_topic]
            })

            # Limit to most recent 100 pools for performance
            for log in logs[-100:]:
                try:
                    decoded = self.factory.events.PoolCreated().process_log(log)
                    pool_address = Web3.to_checksum_address(decoded['args']['pool'])
                    pool = await self._get_pool_contract(pool_address)
                    if pool:
                        liquidity = await self._get_pool_liquidity(pool)
                        total_liquidity += liquidity

                except Exception as e:
                    self.logger.warning("Failed to get liquidity for pool %s: %s", pool_address, str(e))
                    continue

            return total_liquidity

        except Exception as e:
            self.logger.error("Failed to get total liquidity: %s", str(e))
            return Decimal(0)
            
    async def supports_token(self, token_address: str) -> bool:
        """Check if token is supported by this DEX."""
        try:
            # BaseSwap supports many tokens, check against a standard
            return token_address.lower() != "0x0000000000000000000000000000000000000000"
        except Exception as e:
            self.logger.error("Failed to check token support: %s", str(e))
            return False
            
    async def get_pairs_for_token(self, token_address: str) -> List[List[str]]:
        """Get pairs involving a specific token."""
        try:
            # For BaseSwapV3, we need to return common pairs for the token
            # This is a simplified implementation - in a real scenario, we would
            # query the factory for all pools involving this token
            common_tokens = await self.get_supported_tokens()
            pairs = []
            
            for other_token in common_tokens:
                if other_token.lower() != token_address.lower():
                    # Check if pool exists
                    pool_address = await self._get_pool_address(
                        token_address, 
                        other_token
                    )
                    if pool_address != "0x0000000000000000000000000000000000000000":
                        pairs.append([token_address, other_token])
            
            return pairs
        except Exception as e:
            self.logger.error("Failed to get pairs for token: %s", str(e))
            return []
            
    async def build_swap_transaction(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        to: str,
        deadline: int
    ) -> Dict[str, Any]:
        """Build a swap transaction for the given parameters."""
        try:
            path = [token_in, token_out]
            
            # Check for best multi-hop path if direct swap is not optimal
            best_path_info = await self.find_best_path(token_in, token_out, amount_in)
            if best_path_info and best_path_info['amount_out'] > min_amount_out:
                path = best_path_info['path']
                min_amount_out = int(best_path_info['amount_out'] * 0.95)  # 5% slippage
            
            # Encode path for V3
            encoded_path = self._encode_path(path)
            
            # Build exactInput parameters
            params = {
                'path': encoded_path,
                'recipient': Web3.to_checksum_address(to),
                'deadline': deadline,
                'amountIn': amount_in,
                'amountOutMinimum': min_amount_out
            }
            
            # Build transaction
            tx = {
                'to': self.router_address,
                'data': self.router.encodeABI(
                    fn_name='exactInput',
                    args=[params]
                ),
                'value': 0 if token_in != self.weth_address else amount_in,
                'gas': await self.estimate_multi_hop_swap_gas(path, amount_in)
            }
            
            return tx
            
        except Exception as e:
            self.logger.error("Failed to build swap transaction: %s", str(e))
            raise