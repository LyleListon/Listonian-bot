"""Portfolio tracking and analysis system."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta

from ..web3.web3_manager import Web3Manager
from ...utils.database import Database

logger = logging.getLogger(__name__)

class PortfolioTracker:
    """Tracks and analyzes portfolio performance."""

    def __init__(
        self,
        web3_manager: Web3Manager,
        wallet_address: str,
        config: Dict[str, Any],
        db: Optional[Database] = None
    ):
        """
        Initialize portfolio tracker.

        Args:
            web3_manager: Web3Manager instance
            wallet_address: Wallet address to track
            config: Configuration dictionary
            db: Optional Database instance
        """
        self.web3_manager = web3_manager
        self.wallet_address = wallet_address
        self.config = config
        self.db = db if db else Database()
        
        # Initialize tracking
        self.start_time = datetime.now()
        self.total_trades = 0
        self.successful_trades = 0
        self.total_profit = Decimal('0')
        self.total_gas_spent = Decimal('0')
        
        # Performance metrics
        self.metrics = {
            'success_rate': 0.0,
            'avg_profit_per_trade': Decimal('0'),
            'roi': Decimal('0'),
            'sharpe_ratio': 0.0,
            'max_drawdown': Decimal('0'),
            'win_loss_ratio': 0.0
        }
        
        # Historical data
        self.trade_history: List[Dict[str, Any]] = []
        self.balance_history: List[Dict[str, Any]] = []
        self.profit_history: List[Dict[str, Any]] = []

    async def initialize(self) -> bool:
        """Initialize tracker and load historical data."""
        try:
            # Load historical data from database
            trades = await self.db.get_trades({})
            for trade in trades:
                self._process_trade(trade)
            
            # Update metrics
            self._update_metrics()
            
            logger.info(f"Portfolio tracker initialized for {self.wallet_address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize portfolio tracker: {e}")
            return False

    async def track_trade(self, trade_data: Dict[str, Any]) -> bool:
        """
        Track a new trade.

        Args:
            trade_data: Trade details including:
                - transaction_hash
                - token_in
                - token_out
                - amount_in
                - amount_out
                - gas_used
                - gas_price
                - status
                - timestamp

        Returns:
            bool: True if tracking successful
        """
        try:
            # Save trade to database
            trade_id = await self.db.save_trade(trade_data)
            
            # Process trade data
            self._process_trade(trade_data)
            
            # Update metrics
            self._update_metrics()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to track trade: {e}")
            return False

    async def get_portfolio_value(self) -> Dict[str, Any]:
        """Get current portfolio value and composition."""
        try:
            total_value = Decimal('0')
            composition = {}
            
            # Get token balances
            for token, details in self.config.get('tokens', {}).items():
                balance = await self.web3_manager.get_token_balance(
                    token_address=details['address'],
                    wallet_address=self.wallet_address
                )
                if balance > 0:
                    # Get token price
                    price = await self._get_token_price(token)
                    value = Decimal(str(balance)) * price
                    
                    composition[token] = {
                        'balance': balance,
                        'value': value,
                        'price': price
                    }
                    total_value += value
            
            return {
                'total_value': total_value,
                'composition': composition,
                'profit_loss': self.total_profit,
                'roi': self.metrics['roi']
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio value: {e}")
            return {}

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'success_rate': self.metrics['success_rate'],
            'total_profit': self.total_profit,
            'avg_profit_per_trade': self.metrics['avg_profit_per_trade'],
            'roi': self.metrics['roi'],
            'sharpe_ratio': self.metrics['sharpe_ratio'],
            'max_drawdown': self.metrics['max_drawdown'],
            'win_loss_ratio': self.metrics['win_loss_ratio'],
            'gas_efficiency': self.total_profit / self.total_gas_spent if self.total_gas_spent else 0
        }

    async def get_trade_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered trade history."""
        try:
            if not start_time:
                start_time = self.start_time
            if not end_time:
                end_time = datetime.now()
                
            query = {
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }
            
            return await self.db.get_trades(query)
            
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            return []

    def _process_trade(self, trade_data: Dict[str, Any]) -> None:
        """Process trade data and update tracking."""
        try:
            self.total_trades += 1
            
            if trade_data['status'] == 'completed':
                self.successful_trades += 1
                
                # Calculate profit
                gas_cost = Decimal(str(trade_data['gas_used'])) * Decimal(str(trade_data['gas_price']))
                self.total_gas_spent += gas_cost
                
                profit = (
                    Decimal(str(trade_data['amount_out'])) -
                    Decimal(str(trade_data['amount_in'])) -
                    gas_cost
                )
                self.total_profit += profit
                
                # Update histories
                self.trade_history.append(trade_data)
                self.profit_history.append({
                    'timestamp': trade_data['timestamp'],
                    'profit': profit
                })
                
        except Exception as e:
            logger.error(f"Failed to process trade: {e}")

    def _update_metrics(self) -> None:
        """Update performance metrics."""
        try:
            if self.total_trades > 0:
                # Basic metrics
                self.metrics['success_rate'] = self.successful_trades / self.total_trades
                self.metrics['avg_profit_per_trade'] = (
                    self.total_profit / self.successful_trades
                    if self.successful_trades > 0 else Decimal('0')
                )
                
                # Calculate ROI
                initial_value = Decimal('1000')  # Example initial value
                current_value = initial_value + self.total_profit
                self.metrics['roi'] = (
                    (current_value - initial_value) / initial_value
                    if initial_value > 0 else Decimal('0')
                )
                
                # Calculate Sharpe ratio
                if len(self.profit_history) > 1:
                    returns = [
                        float(p['profit']) for p in self.profit_history
                    ]
                    avg_return = sum(returns) / len(returns)
                    std_dev = (
                        sum((r - avg_return) ** 2 for r in returns) /
                        len(returns)
                    ) ** 0.5
                    self.metrics['sharpe_ratio'] = (
                        avg_return / std_dev if std_dev > 0 else 0
                    )
                
                # Calculate maximum drawdown
                peak = Decimal('0')
                max_drawdown = Decimal('0')
                current_value = initial_value
                
                for profit in self.profit_history:
                    current_value += Decimal(str(profit['profit']))
                    peak = max(peak, current_value)
                    drawdown = (peak - current_value) / peak
                    max_drawdown = max(max_drawdown, drawdown)
                
                self.metrics['max_drawdown'] = max_drawdown
                
                # Calculate win/loss ratio
                winning_trades = len([
                    t for t in self.trade_history
                    if Decimal(str(t.get('profit', 0))) > 0
                ])
                losing_trades = self.successful_trades - winning_trades
                self.metrics['win_loss_ratio'] = (
                    winning_trades / losing_trades
                    if losing_trades > 0 else float('inf')
                )
                
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    async def _get_token_price(self, token: str) -> Decimal:
        """Get current token price in USD."""
        try:
            # Map token symbols to coingecko IDs
            token_ids = {
                'WETH': 'ethereum',
                'USDC': 'usd-coin',
                'DAI': 'dai'
            }
            
            if token not in token_ids:
                logger.warning(f"No price feed mapping for token: {token}")
                return Decimal('0')
            
            # Get price from crypto-price MCP server
            response = await self.web3_manager.use_mcp_tool(
                "crypto-price",
                "get_prices",
                {
                    "coins": [token_ids[token]],
                    "include_24h_change": False
                }
            )
            
            if not response or token_ids[token] not in response:
                logger.error(f"Failed to get price for {token}")
                return Decimal('0')
                
            price = response[token_ids[token]]["usd"]
            return Decimal(str(price))
            
        except Exception as e:
            logger.error(f"Failed to get token price: {e}")
            return Decimal('0')


async def create_portfolio_tracker(
    web3_manager: Web3Manager,
    wallet_address: str,
    config: Dict[str, Any],
    db: Optional[Database] = None
) -> Optional[PortfolioTracker]:
    """
    Create portfolio tracker instance.

    Args:
        web3_manager: Web3Manager instance
        wallet_address: Wallet address to track
        config: Configuration dictionary
        db: Optional Database instance

    Returns:
        Optional[PortfolioTracker]: Portfolio tracker instance
    """
    try:
        tracker = PortfolioTracker(
            web3_manager=web3_manager,
            wallet_address=wallet_address,
            config=config,
            db=db
        )
        
        success = await tracker.initialize()
        if not success:
            raise ValueError("Failed to initialize portfolio tracker")
            
        return tracker
        
    except Exception as e:
        logger.error(f"Failed to create portfolio tracker: {e}")
        return None
