"""Market analysis utilities."""

import logging
import math
from typing import Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Analyzes market conditions and opportunities."""

    def __init__(self, dex_manager=None):
        """Initialize market analyzer."""
        logger.debug("Market analyzer initialized")
        self._price_cache = {}
        self._cache_duration = timedelta(seconds=5)  # Cache prices for 5 seconds only
        self.dex_manager = dex_manager
        self.min_liquidity = Decimal('10000')  # Minimum $10000 liquidity
        self.min_price_diff = Decimal('0.002')  # 0.2% minimum difference
        self.test_amounts = [
            Decimal('0.01'),  # 0.01 ETH
            Decimal('0.05'),  # 0.05 ETH
            Decimal('0.1'),  # 0.1 ETH
            Decimal('2.0'),  # 2.0 ETH
        ]

    def validate_price(self, price: float) -> bool:
        """
        Validate if a price is valid.

        Args:
            price (float): Price to validate

        Returns:
            bool: True if price is valid, False otherwise
        """
        if not isinstance(price, (int, float)):
            return False

        return price > 0 and not math.isinf(price) and not math.isnan(price)

    def calculate_price_difference(self, price1: float, price2: float) -> float:
        """
        Calculate percentage difference between two prices.

        Args:
            price1 (float): First price
            price2 (float): Second price

        Returns:
            float: Price difference as a decimal (e.g., 0.05 for 5%)
        """
        if not (self.validate_price(price1) and self.validate_price(price2)):
            raise ValueError("Invalid prices provided")

        return abs(price2 - price1) / price1

    def get_opportunities(self) -> List[Dict[str, Any]]:
        """Get current arbitrage opportunities."""
        try:
            opportunities = []
            
            # Get all enabled DEXes
            dexes = [
                dex for dex in self.dex_manager.get_all_dexes()
                if dex.is_enabled()
            ]
            
            if len(dexes) < 2:
                logger.warning("Not enough DEXes available for arbitrage")
                return []
                
            # Get WETH address
            weth_address = None
            for dex in dexes:
                if 'weth_address' in dex.config:
                    weth_address = dex.config['weth_address']
                    break
            
            if not weth_address:
                logger.error("No WETH address found in DEX configs")
                return []
            
            # Get common tokens across all DEXes
            common_tokens = set()
            for dex in dexes:
                tokens = dex.get_supported_tokens()
                if not common_tokens:
                    common_tokens = set(tokens)
                else:
                    common_tokens &= set(tokens)
            
            for token in common_tokens:
                if token == weth_address:
                    continue  # Skip WETH itself
                    
                prices = {}
                liquidity = {}
                
                for dex in dexes:
                    try:
                        # Get token price and liquidity
                        price = dex.get_token_price(token)
                        pool_liquidity = dex.get_total_liquidity()
                        
                        if price > 0 and pool_liquidity >= self.min_liquidity:
                            prices[dex.name] = float(price)
                            liquidity[dex.name] = float(pool_liquidity)
                    except Exception as e:
                        continue
                
                if len(prices) < 2:
                    continue
                    
                # Find arbitrage opportunities
                for i, (dex1_name, price1) in enumerate(prices.items()):
                    for dex2_name, price2 in list(prices.items())[i+1:]:
                        try:
                            # Calculate price difference
                            diff = self.calculate_price_difference(price1, price2)
                            
                            # If significant price difference found
                            if diff > float(self.min_price_diff):
                                # Determine buy/sell direction
                                if price1 < price2:
                                    dex_from, dex_to = dex1_name, dex2_name
                                    price_from, price_to = price1, price2
                                else:
                                    dex_from, dex_to = dex2_name, dex1_name
                                    price_from, price_to = price2, price1
                                
                                # Try different amounts to find best opportunity
                                for amount_in in self.test_amounts:
                                    # Calculate potential profit
                                    amount_out = amount_in * Decimal(str(price_to / price_from))
                                    profit = float(amount_out - amount_in)
                                    profit_usd = profit * price_to
                                    
                                    # Build token paths for each DEX
                                    dex_from_path = [weth_address, token]  # WETH -> Token on DEX A
                                    dex_to_path = [token, weth_address]    # Token -> WETH on DEX B
                                    
                                    opportunity = {
                                        'token': token,
                                        'dex_from': dex_from,
                                        'dex_to': dex_to,
                                        'price_from': price_from,
                                        'price_to': price_to,
                                        'price_diff': diff,
                                        'amount_in': float(amount_in),
                                        'amount_out': float(amount_out),
                                        'profit_usd': profit_usd,
                                        'dex_from_path': dex_from_path,  # Path for first DEX
                                        'dex_to_path': dex_to_path,      # Path for second DEX
                                        'liquidity_from': liquidity[dex_from],
                                        'liquidity_to': liquidity[dex_to],
                                        'timestamp': datetime.now().timestamp()
                                    }
                                    
                                    opportunities.append(opportunity)
                                    if profit_usd >= 1.0:  # Only log if profit is $1 or more
                                        logger.debug(
                                            f"Found opportunity: {dex_from} -> {dex_to}, "
                                            f"Token: {token}, "
                                            f"Profit: ${profit_usd:.2f}"
                                        )
                                
                        except Exception as e:
                            logger.error(f"Error calculating opportunity: {e}")
                            continue
            
            # Sort opportunities by profit
            opportunities.sort(key=lambda x: x['profit_usd'], reverse=True)
            return opportunities
            
        except Exception as e:
            logger.error(f"Error getting opportunities: {e}")
            return []

    def get_market_condition(self, token: str) -> Dict[str, Any]:
        """Get current market condition for token."""
        try:
            # Get actual market data from DEXes
            prices = []
            total_liquidity = Decimal(0)
            total_volume = Decimal(0)
            
            for dex in self.dex_manager.get_all_dexes():
                try:
                    price = dex.get_token_price(token)
                    if price > 0:
                        prices.append(price)
                    
                    liquidity = dex.get_total_liquidity()
                    if liquidity > 0:
                        total_liquidity += liquidity
                        
                    volume = dex.get_24h_volume(token)
                    if volume > 0:
                        total_volume += volume
                except Exception:
                    continue
            
            if not prices:
                return {}
                
            avg_price = sum(prices) / len(prices)
            volatility = max(abs(p - avg_price) / avg_price for p in prices)
            
            return {
                'price': float(avg_price),
                'volatility': float(volatility),
                'liquidity': float(total_liquidity),
                'volume': float(total_volume),
                'trend': 'stable' if volatility < 0.02 else 'volatile'
            }
        except Exception as e:
            logger.error(f"Error getting market condition: {e}")
            return {}

    def get_current_price(self, token: str) -> float:
        """
        Get current price from cache if available and not expired.

        Args:
            token (str): Token identifier

        Returns:
            float: Current price
        """
        cache_entry = self._price_cache.get(token)
        if cache_entry:
            timestamp, price = cache_entry
            if datetime.now() - timestamp < self._cache_duration:
                return price

        # Get actual price from DEXes
        prices = []
        for dex in self.dex_manager.get_all_dexes():
            try:
                price = dex.get_token_price(token)
                if price > 0:
                    prices.append(price)
            except Exception:
                continue
                
        if not prices:
            return 0.0
            
        # Use median price to avoid outliers
        price = sorted(prices)[len(prices) // 2]
        self._price_cache[token] = (datetime.now(), price)
        return price


def create_market_analyzer(dex_manager=None) -> MarketAnalyzer:
    """Create market analyzer instance."""
    analyzer = MarketAnalyzer(dex_manager=dex_manager)
    return analyzer
