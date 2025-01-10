"""Aerodrome DEX integration with MCP price validation and gas optimization."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import json
from web3 import Web3

from ..gas.gas_optimizer import create_gas_optimizer, GasOptimizer
from ..monitoring.transaction_monitor import create_transaction_monitor, TransactionMonitor
from ..analysis.market_analyzer import create_market_analyzer, MarketAnalyzer

from ...utils.mcp_client import use_market_analysis
from ..web3.web3_manager import Web3Manager, Web3ConnectionError

logger = logging.getLogger(__name__)

class AerodromeDEX:
    """Aerodrome DEX interface with price validation."""
    
    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """
        Initialize Aerodrome interface.
        
        Args:
            web3_manager: Web3Manager instance
            config: DEX configuration
        """
        self.w3 = web3_manager
        self.config = config
        self.router_address = config['router']
        self.factory_address = config['factory']
        self.router = None
        self.factory = None
        self.gas_optimizer = None
        self.tx_monitor = None
        self.market_analyzer = None
        
    async def initialize(self):
        """Initialize contracts and verify connection."""
        try:
            # Load ABIs
            with open("abi/aerodrome_router.json", "r") as f:
                router_abi = json.load(f)
            with open("abi/aerodrome_factory.json", "r") as f:
                factory_abi = json.load(f)
            with open("abi/aerodrome_pool.json", "r") as f:
                self.pool_abi = json.load(f)
                
            # Initialize contracts
            self.router = self.w3.get_contract(self.router_address, router_abi)
            self.factory = self.w3.get_contract(self.factory_address, factory_abi)
            
            # Initialize components
            self.gas_optimizer = await create_gas_optimizer(self.w3, self.config)
            self.tx_monitor = await create_transaction_monitor(self.w3, self.config)
            self.market_analyzer = await create_market_analyzer(self.w3, self.config)
            
            logger.info("Aerodrome interface initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Aerodrome interface: {e}")
            return False
            
    async def get_amounts_out(
        self,
        amount_in: int,
        path: List[str],
        is_stable: Optional[List[bool]] = None
    ) -> List[int]:
        """
        Get output amounts for a given input amount and path.
        
        Args:
            amount_in: Input amount in wei
            path: Token path addresses
            is_stable: List of booleans indicating if each hop is stable
            
        Returns:
            List of output amounts in wei
        """
        try:
            # Default to volatile pools if not specified
            if is_stable is None:
                is_stable = [False] * (len(path) - 1)
                
            amounts = [amount_in]
            
            # Calculate amounts through path
            for i in range(len(path) - 1):
                token_in = path[i]
                token_out = path[i + 1]
                
                # Get pool info
                pool_info = await self.get_pool_info(token_in, token_out)
                
                # Get reserves and calculate output
                reserve_in = pool_info['reserve0'] if token_in < token_out else pool_info['reserve1']
                reserve_out = pool_info['reserve1'] if token_in < token_out else pool_info['reserve0']
                
                # Calculate output amount based on pool type
                if pool_info['stable']:
                    # Stable pool - use constant sum formula
                    decimals_in = pool_info['decimals0'] if token_in < token_out else pool_info['decimals1']
                    decimals_out = pool_info['decimals1'] if token_in < token_out else pool_info['decimals0']
                    
                    # Normalize amounts to 18 decimals for calculation
                    scale_in = 10 ** (18 - decimals_in)
                    scale_out = 10 ** (18 - decimals_out)
                    
                    amount_in_adjusted = amounts[-1] * scale_in
                    reserve_in_adjusted = reserve_in * scale_in
                    reserve_out_adjusted = reserve_out * scale_out
                    
                    # Calculate output maintaining constant sum (x + y = k)
                    amount_out = (amount_in_adjusted * reserve_out_adjusted) // (reserve_in_adjusted + amount_in_adjusted)
                    amount_out = amount_out // scale_out  # Convert back to token decimals
                else:
                    # Volatile pool - use constant product formula
                    amount_out = (amounts[-1] * reserve_out * 997) // (reserve_in * 1000 + amounts[-1] * 997)
                
                amounts.append(amount_out)
                
                logger.debug(
                    f"Swap calculation:\n"
                    f"  Pool: {pool_info['address']}\n"
                    f"  Stable: {pool_info['stable']}\n"
                    f"  Amount in: {amounts[-2]}\n"
                    f"  Amount out: {amounts[-1]}\n"
                    f"  Reserve in: {reserve_in}\n"
                    f"  Reserve out: {reserve_out}"
                )
            
            # Validate prices using MCP servers
            try:
                # Get current prices from crypto-price server
                token_ids = []
                if path[0].lower() == "0x4200000000000000000000000000000000000006".lower():
                    token_ids.append("ethereum")
                if path[-1].lower() == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower():
                    token_ids.append("usd-coin")
                
                if token_ids:
                    response = await self.w3.use_mcp_tool(
                        "crypto-price",
                        "get_prices",
                        {
                            "coins": token_ids,
                            "include_24h_change": True
                        }
                    )
                    
                    # Get market analysis for additional validation
                    market_response = await self.w3.use_mcp_tool(
                        "market-analysis",
                        "assess_market_conditions",
                        {
                            "token": token_ids[0],
                            "metrics": ["volatility", "volume", "trend"]
                        }
                    )
                    
                    # Calculate implied price
                    implied_price = amounts[-1] / amounts[0]
                    market_price = float(response['prices'][token_ids[0]]['price_usd'])
                    
                    # Check for significant price deviation
                    deviation = abs(implied_price - market_price) / market_price
                    if deviation > 0.05:
                        logger.warning(
                            f"Price deviation detected:\n"
                            f"  Implied: ${implied_price:,.2f}\n"
                            f"  Market: ${market_price:,.2f}\n"
                            f"  Deviation: {deviation*100:.1f}%"
                        )
                        
                        # Check market conditions
                        volatility = market_response.get("volatility", {}).get("value", 0)
                        volume = market_response.get("volume", {}).get("value", 0)
                        trend = market_response.get("trend", {}).get("direction", "neutral")
                        
                        logger.info(
                            f"Market conditions:\n"
                            f"  Volatility: {volatility:.2f}\n"
                            f"  Volume: ${volume:,.0f}\n"
                            f"  Trend: {trend}"
                        )
                        
                        # Adjust amounts based on market conditions
                        if volatility > 0.5 or trend == "down":
                            logger.warning("High risk conditions - adjusting amounts")
                            amounts = [int(amount * 0.8) for amount in amounts]  # Reduce amounts by 20%
                            
            except Exception as e:
                logger.warning(f"Failed to validate price with MCP servers: {e}")
            
            return amounts
            
        except Exception as e:
            logger.error(f"Failed to get amounts out: {e}")
            raise
            
    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int,
        is_stable: Optional[List[bool]] = None,
        expected_profit_usd: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Execute token swap.
        
        Args:
            amount_in: Input amount in wei
            amount_out_min: Minimum output amount in wei
            path: Token path addresses
            to: Recipient address
            deadline: Transaction deadline
            is_stable: List of booleans indicating if each hop is stable
            
        Returns:
            Transaction receipt
        """
        try:
            # Default to volatile pools if not specified
            if is_stable is None:
                is_stable = [False] * (len(path) - 1)
                
            # Get pool info for gas estimation
            pool_info = await self.get_pool_info(path[0], path[1])
            
            # Get gas estimate
            gas_estimate = await self.gas_optimizer.estimate_gas_for_pool(
                pool_info['address'],
                pool_info['stable'],
                amount_in
            )
            
            # Check market conditions
            if expected_profit_usd:
                # Check profitability
                if not self.gas_optimizer.should_execute(
                    expected_profit_usd,
                    gas_estimate
                ):
                    logger.warning("Transaction not profitable after gas costs")
                    return None
                    
                # Check market conditions
                should_execute, reason = await self.market_analyzer.should_execute(
                    "WETH",  # Using WETH as primary token
                    expected_profit_usd
                )
                if not should_execute:
                    logger.warning(f"Unfavorable market conditions: {reason}")
                    return None
            
            # Build transaction with optimized gas
            tx = await self.w3.build_contract_transaction(
                self.router,
                'swapExactTokensForTokens',
                amount_in,
                amount_out_min,
                path,
                to,
                deadline,
                is_stable,
                gas=gas_estimate.gas_limit,
                maxFeePerGas=gas_estimate.max_fee,
                maxPriorityFeePerGas=gas_estimate.priority_fee
            )
            
            # Execute and monitor transaction
            signed_tx = await self.w3.eth.account.sign_transaction(tx)
            tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Start monitoring
            await self.tx_monitor.add_transaction(tx_hash)
            
            # Wait for confirmation
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Record gas usage if successful
            if receipt['status'] == 1:  # Success
                self.gas_optimizer.record_gas_used(
                    pool_info['address'],
                    receipt['gasUsed']
                )
                
                logger.info(
                    f"Swap successful:\n"
                    f"  Hash: {tx_hash}\n"
                    f"  Block: {receipt['blockNumber']}\n"
                    f"  Gas Used: {receipt['gasUsed']:,}\n"
                    f"  Gas Price: {receipt['effectiveGasPrice'] / 10**9:.1f} GWEI"
                )
            else:
                logger.error(f"Swap failed: {tx_hash}")
            
            return receipt
            
        except Exception as e:
            logger.error(f"Failed to execute swap: {e}")
            raise
            
    async def get_price(self, token_in: str, token_out: str) -> float:
        """
        Get token price from pool.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            
        Returns:
            float: Price of token_out in terms of token_in
        """
        try:
            # Get pool info
            pool_info = await self.get_pool_info(token_in, token_out)
            
            # Calculate price based on reserves
            reserve_in = pool_info['reserve0'] if token_in < token_out else pool_info['reserve1']
            reserve_out = pool_info['reserve1'] if token_in < token_out else pool_info['reserve0']
            decimals_in = pool_info['decimals0'] if token_in < token_out else pool_info['decimals1']
            decimals_out = pool_info['decimals1'] if token_in < token_out else pool_info['decimals0']
            
            # Normalize reserves to account for decimals
            reserve_in_adjusted = reserve_in / (10 ** decimals_in)
            reserve_out_adjusted = reserve_out / (10 ** decimals_out)
            
            # Calculate price
            if pool_info['stable']:
                # For stable pools, price is close to 1:1
                price = reserve_out_adjusted / reserve_in_adjusted
            else:
                # For volatile pools, use constant product formula
                price = reserve_out_adjusted / reserve_in_adjusted
            
            return float(price)
            
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            raise
            
    async def check_pool_exists(self, token0: str, token1: str) -> bool:
        """Check if pool exists for token pair."""
        try:
            # Try getting amounts out with minimal amount
            path = [token0, token1]
            await self.get_amounts_out(1000, path)
            return True
        except Exception:
            return False
            
    async def get_pool_info(self, token0: str, token1: str) -> Dict[str, Any]:
        """Get pool information including reserves and stability."""
        try:
            # Get pool address from factory
            pool_address = await self.factory.functions.getPool(token0, token1, True).call()
            if pool_address == "0x0000000000000000000000000000000000000000":
                pool_address = await self.factory.functions.getPool(token0, token1, False).call()
                is_stable = False
            else:
                is_stable = True
                
            if pool_address == "0x0000000000000000000000000000000000000000":
                raise ValueError("Pool not found")
                
            # Get pool contract
            pool_contract = self.w3.get_contract(pool_address, self.pool_abi)
            
            try:
                # Get pool metadata
                metadata = await self.w3.call_contract_method(pool_contract, 'metadata')
                decimals0, decimals1 = int(metadata[0]), int(metadata[1])
                reserve0, reserve1 = int(metadata[2]), int(metadata[3])
                is_stable = metadata[4]
            except Exception as e:
                logger.error(f"Failed to get metadata: {e}")
                # Fallback to individual calls
                try:
                    reserves = await self.w3.call_contract_method(pool_contract, 'getReserves')
                    reserve0, reserve1 = int(reserves[0]), int(reserves[1])
                    is_stable = await self.w3.call_contract_method(pool_contract, 'stable')
                    decimals0 = decimals1 = 18  # Default to 18 decimals
                except Exception as e:
                    logger.error(f"Failed to get reserves: {e}")
                    raise
            
            # Get USD values using crypto-price server
            try:
                token0_id = "ethereum" if token0.lower() == "0x4200000000000000000000000000000000000006".lower() else None
                token1_id = "usd-coin" if token1.lower() == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower() else None
                
                if token0_id or token1_id:
                    response = await self.w3.use_mcp_tool(
                        "crypto-price",
                        "get_prices",
                        {
                            "coins": [id for id in [token0_id, token1_id] if id],
                            "include_24h_change": False
                        }
                    )
                    
                    if token0_id and token0_id in response.get('prices', {}):
                        eth_price = float(response['prices'][token0_id]['price_usd'])
                        reserve0_usd = float(Web3.from_wei(reserve0, 'ether')) * eth_price
                        reserve1_usd = reserve1 / (10 ** decimals1)
                    else:
                        reserve0_usd = reserve0 / (10 ** decimals0)
                        reserve1_usd = reserve1 / (10 ** decimals1)
                else:
                    # Fallback to approximate values
                    reserve0_usd = reserve0 / (10 ** decimals0)
                    reserve1_usd = reserve1 / (10 ** decimals1)
            except Exception as e:
                logger.warning(f"Failed to get prices from MCP server: {e}")
                # Fallback to approximate values
                reserve0_usd = reserve0 / (10 ** decimals0)
                reserve1_usd = reserve1 / (10 ** decimals1)
                
            total_liquidity = reserve0_usd + reserve1_usd
            
            logger.info(
                f"Pool {pool_address} info:\n"
                f"  Stable: {is_stable}\n"
                f"  Reserve0: {reserve0_usd:,.2f} USD\n"
                f"  Reserve1: {reserve1_usd:,.2f} USD\n"
                f"  Total Liquidity: {total_liquidity:,.2f} USD"
            )
            
            return {
                "address": pool_address,
                "stable": is_stable,
                "reserve0": reserve0,
                "reserve1": reserve1,
                "decimals0": decimals0,
                "decimals1": decimals1,
                "liquidity_usd": total_liquidity
            }
            
        except Exception as e:
            logger.error(f"Failed to get pool info: {e}")
            raise
