"""
Opportunity Tracker Module

Tracks and stores arbitrage opportunity checks with their details.
"""

import time
import json
import logging
import threading
from typing import Dict, List, Any
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

class OpportunityTracker:
    """Tracks arbitrage opportunity checks and their results."""
    
    def __init__(self, max_entries=1000):
        """
        Initialize the opportunity tracker.
        
        Args:
            max_entries: Maximum number of opportunity entries to store
        """
        self.opportunities = deque(maxlen=max_entries)
        self.lock = threading.Lock()
    
    def add_opportunity(self, data: Dict[str, Any]):
        """
        Add a new opportunity check to the tracker.
        
        Args:
            data: Dictionary containing opportunity details:
                - timestamp: Time of the check (ISO format string or datetime object)
                - pair: Trading pair (e.g., "WETH/USDC")
                - source_dex: Source DEX name
                - target_dex: Target DEX name
                - source_price: Price on the source DEX
                - target_price: Price on the target DEX
                - amount: Amount of source token to trade (optional)
                - profit_usd: Potential profit in USD
                - gas_cost_usd: Estimated gas cost in USD (optional)
                - net_profit_usd: Net profit after gas costs (optional)
                - executed: Whether the opportunity was executed (optional)
        """
        # Ensure timestamp is a string in ISO format
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        elif 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        # Calculate net profit if not provided
        if 'net_profit_usd' not in data and 'profit_usd' in data:
            gas_cost = data.get('gas_cost_usd', 0)
            data['net_profit_usd'] = data['profit_usd'] - gas_cost
        
        # Add unique ID if not provided
        if 'id' not in data:
            data['id'] = str(int(time.time() * 1000))
        
        with self.lock:
            self.opportunities.appendleft(data)
            logger.debug(f"Added opportunity: {data['pair']} with profit: ${data.get('net_profit_usd', 0):.2f}")
    
    def get_opportunities(self, limit=100, min_profit=None, pair=None, dex=None) -> List[Dict[str, Any]]:
        """
        Get recent opportunity checks from the tracker.
        
        Args:
            limit: Maximum number of opportunities to return
            min_profit: Filter by minimum profit in USD
            pair: Filter by trading pair
            dex: Filter by DEX name (source or target)
            
        Returns:
            List of opportunity dictionaries
        """
        with self.lock:
            # Convert deque to list for easier filtering
            opps = list(self.opportunities)
        
        # Apply filters
        if min_profit is not None:
            opps = [o for o in opps if o.get('net_profit_usd', 0) >= min_profit]
        
        if pair is not None:
            opps = [o for o in opps if o.get('pair') == pair]
        
        if dex is not None:
            opps = [o for o in opps if dex in (o.get('source_dex', ''), o.get('target_dex', ''))]
        
        # Return limited number of opportunities
        return opps[:limit]
    
    def get_profitable_opportunities(self, min_profit=0.0, limit=100) -> List[Dict[str, Any]]:
        """
        Get profitable opportunity checks.
        
        Args:
            min_profit: Minimum net profit in USD
            limit: Maximum number of opportunities to return
            
        Returns:
            List of profitable opportunity dictionaries
        """
        return self.get_opportunities(limit=limit, min_profit=min_profit)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tracked opportunities.
        
        Returns:
            Dictionary with statistics
        """
        with self.lock:
            total_opps = len(self.opportunities)
            profitable_opps = sum(1 for o in self.opportunities if o.get('net_profit_usd', 0) > 0)
            
            if total_opps > 0:
                max_profit = max((o.get('net_profit_usd', 0) for o in self.opportunities), default=0)
                avg_profit = sum(o.get('net_profit_usd', 0) for o in self.opportunities) / total_opps
            else:
                max_profit = 0
                avg_profit = 0
            
            return {
                'total_checks': total_opps,
                'profitable_opportunities': profitable_opps,
                'max_profit_usd': max_profit,
                'avg_profit_usd': avg_profit,
                'profit_rate': profitable_opps / total_opps if total_opps > 0 else 0,
                'last_update': datetime.now().isoformat()
            }
    
    def clear(self):
        """Clear all stored opportunities."""
        with self.lock:
            self.opportunities.clear()

# Create a global instance for easy importing
opportunity_tracker = OpportunityTracker()

def simulate_opportunity_check(token_prices, token_pair):
    """
    Simulate an arbitrage opportunity check between two DEXes.
    
    Args:
        token_prices: Dictionary of token prices by DEX
        token_pair: Tuple of (base_token, quote_token) symbols
        
    Returns:
        Opportunity data dictionary or None if no valid check could be made
    """
    base_token, quote_token = token_pair
    pair_name = f"{base_token}/{quote_token}"
    
    # Find DEXes that have prices for both tokens
    valid_dexes = []
    for dex_name, dex_data in token_prices.items():
        if (base_token in dex_data.get('prices', {}) and 
            quote_token in dex_data.get('prices', {}) and
            dex_data['prices'][base_token].get('formatted', 0) > 0 and
            dex_data['prices'][quote_token].get('formatted', 0) > 0):
            valid_dexes.append(dex_name)
    
    if len(valid_dexes) < 2:
        return None  # Not enough DEXes with valid prices
    
    # Choose two random DEXes from the valid ones
    import random
    source_dex = random.choice(valid_dexes)
    valid_dexes.remove(source_dex)
    target_dex = random.choice(valid_dexes)
    
    # Get prices for the pair on both DEXes
    source_base_price = token_prices[source_dex]['prices'][base_token]['formatted']
    source_quote_price = token_prices[source_dex]['prices'][quote_token]['formatted']
    target_base_price = token_prices[target_dex]['prices'][base_token]['formatted']
    target_quote_price = token_prices[target_dex]['prices'][quote_token]['formatted']
    
    # Calculate price ratio (how much quote token per base token)
    source_price_ratio = source_quote_price / source_base_price
    target_price_ratio = target_quote_price / target_base_price
    
    # Determine price difference percentage
    price_diff_pct = (abs(source_price_ratio - target_price_ratio) / 
                      min(source_price_ratio, target_price_ratio)) * 100
    
    # Simulate a trade with a random amount
    trade_amount_base = random.uniform(0.1, 1.0)  # Trade between 0.1 and 1.0 base tokens
    
    # Calculate potential profit
    # If source_price_ratio < target_price_ratio, buy on source, sell on target
    # Otherwise, buy on target, sell on source
    if source_price_ratio < target_price_ratio:
        buy_dex, sell_dex = source_dex, target_dex
        buy_price = source_price_ratio
        sell_price = target_price_ratio
    else:
        buy_dex, sell_dex = target_dex, source_dex
        buy_price = target_price_ratio
        sell_price = source_price_ratio
    
    # Calculate gross profit (before fees and gas)
    quote_received = trade_amount_base * sell_price
    quote_paid = trade_amount_base * buy_price
    gross_profit_quote = quote_received - quote_paid
    
    # Convert to USD for easier understanding
    # For simplicity, assume quote token is a stablecoin like USDC
    gross_profit_usd = gross_profit_quote
    
    # Simulate fees and gas costs
    fee_rate = 0.003  # 0.3% fee per trade
    fees_usd = (trade_amount_base * buy_price * fee_rate) + (quote_received * fee_rate)
    gas_cost_usd = random.uniform(5, 15)  # Gas costs between $5-$15
    
    # Calculate net profit
    net_profit_usd = gross_profit_usd - fees_usd - gas_cost_usd
    
    # Timestamp for the opportunity check
    timestamp = datetime.now()
    
    # Create opportunity data
    opportunity = {
        'timestamp': timestamp.isoformat(),
        'pair': pair_name,
        'source_dex': buy_dex,
        'target_dex': sell_dex,
        'source_price': buy_price,
        'target_price': sell_price,
        'price_diff_pct': price_diff_pct,
        'amount': trade_amount_base,
        'profit_usd': gross_profit_usd,
        'fees_usd': fees_usd,
        'gas_cost_usd': gas_cost_usd,
        'net_profit_usd': net_profit_usd,
        'executed': net_profit_usd > 0.1,  # Only execute if profit > $0.10
        'execution_time_ms': random.randint(100, 500) if net_profit_usd > 0.1 else None
    }
    
    return opportunity