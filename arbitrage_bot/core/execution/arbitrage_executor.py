"""Arbitrage execution engine."""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

from ..web3.web3_manager import Web3Manager, create_web3_manager
from ..dex.dex_manager import DEXManager, create_dex_manager
from ..gas.gas_optimizer import GasOptimizer, create_gas_optimizer
from ..dex.utils import (
    calculate_price_impact,
    estimate_gas_cost,
    format_amount_with_decimals,
    COMMON_TOKENS
)
from ..gas.gas_optimizer import GasOptimizer

logger = logging.getLogger(__name__)

class ArbitrageExecutor:
    """Executes arbitrage opportunities across multiple DEXs."""

    def __init__(
        self,
        dex_manager: DEXManager,
        web3_manager: Web3Manager,
        gas_optimizer: GasOptimizer,
        min_profit_usd: float = 10.0,  # Minimum profit in USD
        max_price_impact: float = 0.02,  # Maximum 2% price impact
        slippage_tolerance: float = 0.005,  # 0.5% slippage tolerance
        tx_monitor: Optional[Any] = None,
        market_analyzer: Optional[Any] = None
    ):
        """Initialize arbitrage executor."""
        self.dex_manager = dex_manager
        self.web3_manager = web3_manager
        self.gas_optimizer = gas_optimizer
        self.min_profit_usd = min_profit_usd
        self.wallet_address = web3_manager.wallet_address
        self.max_price_impact = max_price_impact
        self.slippage_tolerance = slippage_tolerance
        self.tx_monitor = tx_monitor
        self.market_analyzer = market_analyzer

    async def find_opportunities(
        self,
        base_tokens: Optional[List[str]] = None,
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities across DEXs.
        
        Args:
            base_tokens: List of base tokens to check (default: WETH, USDC)
            max_hops: Maximum hops per DEX (default: 2)
            
        Returns:
            List[Dict[str, Any]]: List of opportunities with details
        """
        if not base_tokens:
            base_tokens = [
                COMMON_TOKENS['WETH'],
                COMMON_TOKENS['USDC']
            ]
            
        opportunities = []
        dexes = self.dex_manager.get_all_dexes()
        
        # Get current gas price
        gas_price = await self.gas_optimizer.get_optimal_gas_price()
        
        # Check all token pairs across DEXs
        for token_in in base_tokens:
            for token_out in base_tokens:
                if token_in == token_out:
                    continue
                    
                # Get quotes from all DEXs
                quotes = await asyncio.gather(*[
                    self._get_dex_quote(dex, token_in, token_out, max_hops)
                    for dex in dexes
                ])
                
                # Find arbitrage opportunities
                for i, buy_quote in enumerate(quotes):
                    if not buy_quote:
                        continue
                        
                    for j, sell_quote in enumerate(quotes):
                        if i == j or not sell_quote:
                            continue
                            
                        opportunity = await self._analyze_opportunity(
                            buy_quote=buy_quote,
                            sell_quote=sell_quote,
                            gas_price=gas_price
                        )
                        
                        if opportunity:
                            opportunities.append(opportunity)
        
        # Sort by profit
        opportunities.sort(key=lambda x: x['profit_usd'], reverse=True)
        return opportunities

    async def execute_opportunity(
        self,
        opportunity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute an arbitrage opportunity.
        
        Args:
            opportunity: Opportunity details from find_opportunities
            
        Returns:
            Optional[Dict[str, Any]]: Execution results if successful
        """
        try:
            # Verify opportunity is still valid
            current_profit = await self._verify_opportunity(opportunity)
            if not current_profit or current_profit['profit_usd'] < self.min_profit_usd:
                logger.info("Opportunity no longer profitable")
                return None
            
            # Get DEX instances
            buy_dex = self.dex_manager.get_dex(opportunity['buy_dex'])
            sell_dex = self.dex_manager.get_dex(opportunity['sell_dex'])
            if not buy_dex or not sell_dex:
                logger.error("DEX not available")
                return None
            
            # Execute trades
            buy_tx = await buy_dex.swap_exact_tokens_for_tokens(
                amount_in=opportunity['amount_in'],
                amount_out_min=int(opportunity['buy_amount_out'] * (1 - self.slippage_tolerance)),
                path=opportunity['buy_path'],
                to=self.web3_manager.wallet_address,
                deadline=self._get_deadline()
            )
            
            if not buy_tx:
                logger.error("Buy transaction failed")
                return None
            
            # Wait for buy transaction
            buy_receipt = await self.web3_manager.wait_for_transaction(buy_tx)
            if not buy_receipt or not buy_receipt['status']:
                logger.error("Buy transaction reverted")
                return None
            
            # Execute sell
            sell_tx = await sell_dex.swap_exact_tokens_for_tokens(
                amount_in=opportunity['buy_amount_out'],
                amount_out_min=int(opportunity['sell_amount_out'] * (1 - self.slippage_tolerance)),
                path=opportunity['sell_path'],
                to=self.web3_manager.wallet_address,
                deadline=self._get_deadline()
            )
            
            if not sell_tx:
                logger.error("Sell transaction failed")
                return None
            
            # Wait for sell transaction
            sell_receipt = await self.web3_manager.wait_for_transaction(sell_tx)
            if not sell_receipt or not sell_receipt['status']:
                logger.error("Sell transaction reverted")
                return None
            
            # Calculate actual profit
            actual_profit = await self._calculate_actual_profit(
                buy_receipt=buy_receipt,
                sell_receipt=sell_receipt,
                opportunity=opportunity
            )
            
            return {
                'success': True,
                'buy_tx': buy_tx,
                'sell_tx': sell_tx,
                'profit_usd': actual_profit,
                'gas_used': buy_receipt['gasUsed'] + sell_receipt['gasUsed'],
                'timestamp': self.web3_manager.w3.eth.get_block('latest')['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error executing opportunity: {e}")
            return None

    async def _get_dex_quote(
        self,
        dex: Any,
        token_in: str,
        token_out: str,
        max_hops: int
    ) -> Optional[Dict[str, Any]]:
        """Get quote from a DEX."""
        try:
            # Find best path
            path = await dex.get_best_path(
                token_in=token_in,
                token_out=token_out,
                amount_in=1000000,  # 1M units for price impact calculation
                max_hops=max_hops
            )
            
            if not path:
                return None
            
            # Get quote with impact
            quote = await dex.get_quote_with_impact(
                amount_in=path['amounts'][0],
                path=path['path']
            )
            
            if not quote:
                return None
            
            return {
                'dex_name': dex.name,
                'path': path['path'],
                'amounts': path['amounts'],
                'price_impact': quote['price_impact'],
                'gas_estimate': quote['estimated_gas']
            }
            
        except Exception as e:
            logger.error(f"Error getting quote from {dex.name}: {e}")
            return None

    async def _analyze_opportunity(
        self,
        buy_quote: Dict[str, Any],
        sell_quote: Dict[str, Any],
        gas_price: int
    ) -> Optional[Dict[str, Any]]:
        """Analyze potential arbitrage opportunity."""
        try:
            # Check price impact
            total_impact = buy_quote['price_impact'] + sell_quote['price_impact']
            if total_impact > self.max_price_impact:
                return None
            
            # Calculate gas cost
            total_gas = buy_quote['gas_estimate'] + sell_quote['gas_estimate']
            gas_cost_wei = total_gas * gas_price
            gas_cost_usd = await self._convert_wei_to_usd(gas_cost_wei)
            
            # Calculate profit
            amount_out = sell_quote['amounts'][-1]
            amount_in = buy_quote['amounts'][0]
            profit_wei = amount_out - amount_in
            profit_usd = await self._convert_wei_to_usd(profit_wei)
            
            # Subtract gas cost
            net_profit_usd = profit_usd - gas_cost_usd
            
            if net_profit_usd < self.min_profit_usd:
                return None
            
            return {
                'buy_dex': buy_quote['dex_name'],
                'sell_dex': sell_quote['dex_name'],
                'buy_path': buy_quote['path'],
                'sell_path': sell_quote['path'],
                'amount_in': amount_in,
                'buy_amount_out': buy_quote['amounts'][-1],
                'sell_amount_out': amount_out,
                'profit_usd': net_profit_usd,
                'gas_cost_usd': gas_cost_usd,
                'price_impact': total_impact,
                'gas_estimate': total_gas,
                'timestamp': self.web3_manager.w3.eth.get_block('latest')['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity: {e}")
            return None

    async def _verify_opportunity(
        self,
        opportunity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Verify opportunity is still valid and profitable."""
        try:
            # Get current quotes
            buy_dex = self.dex_manager.get_dex(opportunity['buy_dex'])
            sell_dex = self.dex_manager.get_dex(opportunity['sell_dex'])
            
            if not buy_dex or not sell_dex:
                return None
            
            # Get new quotes
            buy_quote = await buy_dex.get_quote_with_impact(
                amount_in=opportunity['amount_in'],
                path=opportunity['buy_path']
            )
            
            if not buy_quote:
                return None
            
            sell_quote = await sell_dex.get_quote_with_impact(
                amount_in=buy_quote['amount_out'],
                path=opportunity['sell_path']
            )
            
            if not sell_quote:
                return None
            
            # Get current gas price
            gas_price = await self.gas_optimizer.get_optimal_gas_price()
            
            # Analyze with current prices
            return await self._analyze_opportunity(
                buy_quote=buy_quote,
                sell_quote=sell_quote,
                gas_price=gas_price
            )
            
        except Exception as e:
            logger.error(f"Error verifying opportunity: {e}")
            return None

    async def _calculate_actual_profit(
        self,
        buy_receipt: Dict[str, Any],
        sell_receipt: Dict[str, Any],
        opportunity: Dict[str, Any]
    ) -> float:
        """Calculate actual profit from transaction receipts."""
        try:
            # Get token transfers from receipts
            buy_transfer = self._get_token_transfer(
                receipt=buy_receipt,
                token=opportunity['buy_path'][-1]
            )
            sell_transfer = self._get_token_transfer(
                receipt=sell_receipt,
                token=opportunity['sell_path'][-1]
            )
            
            if not buy_transfer or not sell_transfer:
                return 0.0
            
            # Calculate profit
            profit_wei = sell_transfer['value'] - buy_transfer['value']
            
            # Subtract gas costs
            total_gas = buy_receipt['gasUsed'] + sell_receipt['gasUsed']
            gas_cost_wei = total_gas * buy_receipt['effectiveGasPrice']
            
            net_profit_wei = profit_wei - gas_cost_wei
            return await self._convert_wei_to_usd(net_profit_wei)
            
        except Exception as e:
            logger.error(f"Error calculating actual profit: {e}")
            return 0.0

    def _get_token_transfer(
        self,
        receipt: Dict[str, Any],
        token: str
    ) -> Optional[Dict[str, Any]]:
        """Get token transfer details from transaction receipt."""
        try:
            # Find Transfer event for target token
            for log in receipt['logs']:
                if (
                    log['address'].lower() == token.lower() and
                    len(log['topics']) == 3 and
                    log['topics'][0].hex() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  # Transfer
                ):
                    return {
                        'from': '0x' + log['topics'][1].hex()[-40:],
                        'to': '0x' + log['topics'][2].hex()[-40:],
                        'value': int(log['data'], 16)
                    }
            return None
            
        except Exception as e:
            logger.error(f"Error parsing token transfer: {e}")
            return None

    async def _convert_wei_to_usd(self, amount_wei: int) -> float:
        """Convert wei amount to USD value."""
        try:
            # Get ETH price from crypto-price server
            response = await self.web3_manager.use_mcp_tool(
                "crypto-price",
                "get_prices",
                {
                    "coins": ["ethereum"],
                    "include_24h_change": False
                }
            )
            
            if not response or "ethereum" not in response:
                self.logger.error("Failed to get ETH price from MCP server")
                return 0.0
                
            eth_price = float(response["ethereum"]["usd"])
            eth_amount = amount_wei / 1e18
            return eth_amount * eth_price
            
        except Exception as e:
            self.logger.error(f"Error converting wei to USD: {e}")
            return 0.0

    def _get_deadline(self) -> int:
        """Get transaction deadline timestamp."""
        current_block = self.web3_manager.w3.eth.get_block('latest')
        return current_block['timestamp'] + 300  # 5 minutes

    async def initialize(self) -> bool:
        """Initialize arbitrage executor."""
        try:
            # Connect to Web3
            await self.web3_manager.connect()

            # Initialize DEX manager
            if not await self.dex_manager.initialize():
                logger.error("Failed to initialize DEX manager")
                return False

            # Initialize gas optimizer
            if not await self.gas_optimizer.initialize():
                logger.error("Failed to initialize gas optimizer")
                return False

            # Check wallet balance
            balance = await self.web3_manager.get_eth_balance()
            if balance == 0:
                logger.warning("Wallet has no ETH balance")

            logger.info("Arbitrage executor initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize arbitrage executor: {e}")
            return False

    # Alias for find_opportunities to maintain compatibility
    detect_opportunities = find_opportunities


async def create_arbitrage_executor(
    web3_manager: Optional[Web3Manager] = None,
    dex_manager: Optional[DEXManager] = None,
    gas_optimizer: Optional[GasOptimizer] = None,
    min_profit_usd: float = 10.0,
    max_price_impact: float = 0.02,
    slippage_tolerance: float = 0.005,
    tx_monitor: Optional[Any] = None,
    market_analyzer: Optional[Any] = None
) -> ArbitrageExecutor:
    """
    Create arbitrage executor instance.

    Args:
        web3_manager: Web3Manager instance
        dex_manager: Optional DEXManager instance
        gas_optimizer: Optional GasOptimizer instance
        min_profit_usd: Minimum profit in USD
        max_price_impact: Maximum price impact
        slippage_tolerance: Slippage tolerance

    Returns:
        ArbitrageExecutor: Arbitrage executor instance
    """
    if not web3_manager:
        web3_manager = await create_web3_manager()
    if not isinstance(web3_manager, Web3Manager):
        raise TypeError(f"Expected Web3Manager instance, got {type(web3_manager)}")
    if not dex_manager:
        dex_manager = await create_dex_manager(web3_manager)
    if not gas_optimizer:
        gas_optimizer = await create_gas_optimizer(dex_manager=dex_manager, web3_manager=web3_manager)

    return ArbitrageExecutor(
        dex_manager=dex_manager,
        web3_manager=web3_manager,
        gas_optimizer=gas_optimizer,
        min_profit_usd=min_profit_usd,
        max_price_impact=max_price_impact,
        slippage_tolerance=slippage_tolerance,
        tx_monitor=tx_monitor,
        market_analyzer=market_analyzer
    )
