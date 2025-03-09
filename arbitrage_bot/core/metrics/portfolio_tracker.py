"""Portfolio tracking and performance metrics."""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import copy
import json
import aiohttp
from ...utils.config_loader import resolve_secure_values
import os

logger = logging.getLogger(__name__)

class PortfolioTracker:
    """Tracks portfolio performance and metrics."""
    
    def __init__(self, web3_manager: Any, wallet_address: str, config: Dict[str, Any]):
        """Initialize portfolio tracker."""
        self.web3_manager = web3_manager
        self.wallet_address = wallet_address
        self.config = config
        self.trades = []
        self.profits = []
        self.start_time = datetime.now()
        self._session = None
        logger.debug("Portfolio tracker initialized")

    async def _get_token_price_from_alchemy(self, token_address: str) -> Optional[float]:
        """Get token price from Alchemy Price API."""
        try:
            # Get price from web3 manager
            price = await self.web3_manager.get_token_price(token_address)
            if price is None:
                logger.debug("No price data for %s", token_address)
                return None

            # Convert to float and validate
            try:
                price_float = float(price)
                if price_float <= 0:
                    return None
                return price_float
            except (ValueError, TypeError):
                logger.error("Invalid price format: %s", str(price))
                return None
            
        except Exception as e:
            logger.error("Error getting Alchemy price: %s", str(e))
            return None
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        try:
            total_trades = len(self.trades)
            total_profit = sum(self.profits) if self.profits else 0
            avg_profit = total_profit / total_trades if total_trades > 0 else 0
            
            # Get ETH balance
            eth_balance = await self.web3_manager.get_eth_balance()
            
            # Get ETH price from Alchemy
            weth_address = self.config.get('tokens', {}).get('WETH', {}).get('address')
            eth_price = None
            portfolio_value_usd = 0.0
            
            try:
                if weth_address:
                    eth_price = await self._get_token_price_from_alchemy(weth_address)
                    if eth_price:
                        portfolio_value_usd = float(eth_balance) * eth_price
                        logger.debug("Portfolio value: $%.2f (ETH price: $%.2f)", portfolio_value_usd, eth_price)
                
            except Exception as e:
                logger.error("Error calculating portfolio value: %s", str(e))
                eth_price = None
                portfolio_value_usd = 0.0
                    
            return {
                'total_trades': total_trades,
                'total_profit_usd': float(total_profit),
                'average_profit_usd': float(avg_profit),
                'eth_balance': float(eth_balance),
                'portfolio_value_usd': portfolio_value_usd,
                'eth_price_usd': eth_price,
                'runtime': str(datetime.now() - self.start_time),
                'wallet_address': self.wallet_address
            }
            
        except Exception as e:
            logger.error("Error getting performance summary: %s", str(e))
            return {
                'total_trades': 0,
                'total_profit_usd': 0.0,
                'average_profit_usd': 0.0,
                'eth_balance': 0.0,
                'runtime': '0:00:00',
                'portfolio_value_usd': 0.0,
                'eth_price_usd': None,
                'wallet_address': self.wallet_address
            }
    
    async def add_trade(self, trade_data: Dict[str, Any]) -> None:
        """Add trade to history."""
        try:
            # Create a clean trade record without nested data
            clean_trade = {
                'buy_dex': trade_data.get('opportunity', {}).get('buy_dex'),
                'sell_dex': trade_data.get('opportunity', {}).get('sell_dex'),
                'token_pair': trade_data.get('opportunity', {}).get('token_pair'),
                'profit_percent': trade_data.get('opportunity', {}).get('profit_percent'),
                'success': trade_data.get('success', False),
                'timestamp': trade_data.get('timestamp', datetime.now().timestamp()),
                'net_profit': trade_data.get('net_profit'),
                'gas_cost': trade_data.get('gas_cost'),
                'tx_hash': trade_data.get('tx_hash'),
                'error': trade_data.get('error')
            }
            
            # Add to memory
            self.trades.append(clean_trade)
            if clean_trade.get('net_profit'):
                self.profits.append(Decimal(str(clean_trade['net_profit'])))
            
            # Persist to memory bank
            try:
                from ..memory import get_memory_bank
                memory_bank = get_memory_bank()
                await memory_bank.store_trade_result(
                    opportunity=clean_trade,
                    success=clean_trade['success'],
                    net_profit=clean_trade.get('net_profit'),
                    gas_cost=clean_trade.get('gas_cost'),
                    tx_hash=clean_trade.get('tx_hash'),
                    error=clean_trade.get('error')
                )
                logger.info("Trade recorded: profit=$%.2f, gas=$%.2f", 
                          clean_trade.get('net_profit', 0), 
                          clean_trade.get('gas_cost', 0))
                
                # Update performance metrics immediately
                _ = await self.get_performance_summary()
            except Exception as e:
                logger.error("Failed to store trade result: %s", str(e))
                # Continue even if memory bank storage fails
            
        except Exception as e:
            logger.error("Error recording trade: %s", str(e))


async def create_portfolio_tracker(
    web3_manager: Optional[Any] = None,
    wallet_address: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> PortfolioTracker:
    """
    Create and initialize a portfolio tracker instance.
    
    Args:
        web3_manager: Optional Web3Manager instance
        wallet_address: Optional wallet address
        config: Optional configuration dictionary
        
    Returns:
        PortfolioTracker: Initialized portfolio tracker
    """
    try:
        if not web3_manager or not wallet_address or not config:
            from ..web3.web3_manager import create_web3_manager
            from ...utils.config_loader import load_config
            
            if not config:
                config = load_config()
            
            if not web3_manager:
                web3_manager = await create_web3_manager(config)
            
            if not wallet_address:
                wallet_address = web3_manager.wallet_address
        
        tracker = PortfolioTracker(
            web3_manager=web3_manager,
            wallet_address=wallet_address,
            config=config
        )
        logger.debug("Portfolio tracker created")
        return tracker
        
    except Exception as e:
        logger.error("Failed to create portfolio tracker: %s", str(e))
        raise
