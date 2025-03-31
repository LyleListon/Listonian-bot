"""
Test cases for the ProfitTracker class.
"""

import asyncio
import unittest
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from arbitrage_bot.core.analytics.profit_tracker import ProfitTracker, create_profit_tracker


class TestProfitTracker(unittest.TestCase):
    """Test cases for the ProfitTracker class."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test storage
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a test configuration
        self.config = {
            'storage_dir': self.temp_dir.name,
            'cache_ttl': 60  # 1 minute
        }
        
        # Sample token addresses (checksummed)
        self.token_a = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"  # UNI
        self.token_b = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
        
        # Sample trade data
        self.sample_trade = {
            'token_in': self.token_a,
            'token_out': self.token_b,
            'amount_in': 10.0,
            'amount_out': 0.05,
            'profit': 0.02,
            'gas_cost': 0.005,
            'timestamp': datetime.utcnow(),
            'dexes': ['uniswap', 'sushiswap'],
            'path': [self.token_a, self.token_b]
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test initialization of ProfitTracker."""
        tracker = ProfitTracker(self.config)
        
        # Check initial state
        self.assertFalse(tracker.initialized)
        self.assertEqual(tracker.storage_dir, self.temp_dir.name)
        self.assertEqual(tracker.cache_ttl, 60)
        self.assertEqual(tracker._profit_history, [])
        self.assertEqual(tracker._token_pair_profits, {})
        self.assertEqual(list(tracker._timeframe_profits.keys()), ["1h", "24h", "7d", "30d", "all"])
    
    async def async_test_initialize(self):
        """Test async initialization."""
        tracker = ProfitTracker(self.config)
        result = await tracker.initialize()
        
        # Check initialization result
        self.assertTrue(result)
        self.assertTrue(tracker.initialized)
        self.assertTrue(os.path.exists(self.temp_dir.name))
    
    async def async_test_track_profit(self):
        """Test tracking a profit entry."""
        tracker = ProfitTracker(self.config)
        await tracker.initialize()
        
        # Track a profit entry
        await tracker.track_profit(self.sample_trade)
        
        # Check that the entry was added
        self.assertEqual(len(tracker._profit_history), 1)
        self.assertEqual(tracker._profit_history[0]['profit'], 0.02)
        
        # Check that the token pair was added
        token_pair = f"{self.token_a}_{self.token_b}"
        self.assertIn(token_pair, tracker._token_pair_profits)
        self.assertEqual(len(tracker._token_pair_profits[token_pair]), 1)
        
        # Check that the entry was added to all timeframes
        for timeframe in tracker._timeframe_profits:
            self.assertEqual(len(tracker._timeframe_profits[timeframe]), 1)
        
        # Check that the file was created
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir.name, 'profit_history.json')))
    
    async def async_test_get_profit_by_token_pair(self):
        """Test getting profit metrics by token pair."""
        tracker = ProfitTracker(self.config)
        await tracker.initialize()
        
        # Track multiple profit entries
        await tracker.track_profit(self.sample_trade)
        
        # Create a second trade with different profit
        second_trade = self.sample_trade.copy()
        second_trade['profit'] = 0.03
        second_trade['timestamp'] = datetime.utcnow() - timedelta(minutes=30)
        await tracker.track_profit(second_trade)
        
        # Get profit metrics for the token pair
        token_pair = f"{self.token_a}_{self.token_b}"
        metrics = await tracker.get_profit_by_token_pair(token_pair=token_pair, timeframe="24h")
        
        # Check metrics
        self.assertEqual(metrics['token_pair'], token_pair)
        self.assertEqual(metrics['timeframe'], "24h")
        self.assertEqual(metrics['total_profit'], 0.05)  # 0.02 + 0.03
        self.assertEqual(metrics['total_volume'], 20.0)  # 10.0 + 10.0
        self.assertEqual(metrics['trade_count'], 2)
        self.assertEqual(metrics['avg_profit'], 0.025)  # (0.02 + 0.03) / 2
        self.assertEqual(metrics['profit_per_volume'], 0.0025)  # 0.05 / 20.0
        
        # Get profit metrics for all token pairs
        all_metrics = await tracker.get_profit_by_token_pair(timeframe="24h")
        
        # Check metrics
        self.assertEqual(all_metrics['timeframe'], "24h")
        self.assertEqual(all_metrics['total_profit'], 0.05)
        self.assertEqual(all_metrics['total_volume'], 20.0)
        self.assertEqual(all_metrics['trade_count'], 2)
        self.assertEqual(len(all_metrics['token_pairs']), 1)
        self.assertIn(token_pair, all_metrics['token_pairs'])
    
    async def async_test_get_roi(self):
        """Test calculating ROI."""
        tracker = ProfitTracker(self.config)
        await tracker.initialize()
        
        # Track a profit entry
        await tracker.track_profit(self.sample_trade)
        
        # Get ROI
        roi = await tracker.get_roi(timeframe="24h")
        
        # Check ROI metrics
        self.assertEqual(roi['timeframe'], "24h")
        self.assertEqual(roi['total_investment'], 10.0)
        self.assertEqual(roi['total_profit'], 0.02)
        self.assertEqual(roi['total_gas_cost'], 0.005)
        self.assertEqual(roi['net_profit'], 0.015)  # 0.02 - 0.005
        self.assertEqual(roi['roi'], 0.15)  # (0.015 / 10.0) * 100
        self.assertEqual(roi['trade_count'], 1)
    
    async def async_test_get_profit_time_series(self):
        """Test getting profit time series data."""
        tracker = ProfitTracker(self.config)
        await tracker.initialize()
        
        # Track multiple profit entries at different times
        for i in range(5):
            trade = self.sample_trade.copy()
            trade['profit'] = 0.01 * (i + 1)
            trade['timestamp'] = datetime.utcnow() - timedelta(hours=i)
            await tracker.track_profit(trade)
        
        # Get profit time series
        time_series = await tracker.get_profit_time_series(timeframe="24h", interval="1h")
        
        # Check time series data
        self.assertEqual(len(time_series['timestamps']), len(time_series['profit']))
        self.assertEqual(len(time_series['timestamps']), len(time_series['cumulative_profit']))
        self.assertEqual(len(time_series['timestamps']), len(time_series['trade_count']))
        self.assertEqual(len(time_series['timestamps']), len(time_series['volume']))
        
        # Check that cumulative profit is increasing
        self.assertTrue(all(time_series['cumulative_profit'][i] <= time_series['cumulative_profit'][i+1] 
                           for i in range(len(time_series['cumulative_profit'])-1)))
    
    async def async_test_get_top_token_pairs(self):
        """Test getting top token pairs."""
        tracker = ProfitTracker(self.config)
        await tracker.initialize()
        
        # Track profit entries for multiple token pairs
        await tracker.track_profit(self.sample_trade)
        
        # Create a trade with a different token pair
        token_c = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
        second_trade = self.sample_trade.copy()
        second_trade['token_out'] = token_c
        second_trade['profit'] = 0.03
        await tracker.track_profit(second_trade)
        
        # Get top token pairs
        top_pairs = await tracker.get_top_token_pairs(timeframe="24h", limit=2)
        
        # Check top pairs
        self.assertEqual(len(top_pairs), 2)
        self.assertEqual(top_pairs[0]['total_profit'], 0.03)  # Higher profit first
        self.assertEqual(top_pairs[1]['total_profit'], 0.02)
    
    async def async_test_get_profit_summary(self):
        """Test getting profit summary."""
        tracker = ProfitTracker(self.config)
        await tracker.initialize()
        
        # Track profit entries
        await tracker.track_profit(self.sample_trade)
        
        # Get profit summary
        summary = await tracker.get_profit_summary()
        
        # Check summary
        self.assertIn('1h', summary)
        self.assertIn('24h', summary)
        self.assertIn('7d', summary)
        self.assertIn('30d', summary)
        self.assertIn('all', summary)
        self.assertIn('summary', summary)
        
        # Check summary metrics
        all_time = summary['all']
        self.assertEqual(all_time['total_profit'], 0.02)
        self.assertEqual(all_time['trade_count'], 1)
        
        # Check summary section
        self.assertEqual(summary['summary']['total_profit_all_time'], 0.02)
        self.assertEqual(summary['summary']['trade_count_all_time'], 1)
    
    async def async_test_create_profit_tracker(self):
        """Test create_profit_tracker factory function."""
        with patch('arbitrage_bot.core.analytics.profit_tracker.ProfitTracker') as mock_tracker:
            # Setup mock
            mock_instance = MagicMock()
            mock_instance.initialize.return_value = True
            mock_tracker.return_value = mock_instance
            
            # Call factory function
            tracker = await create_profit_tracker(self.config)
            
            # Check that ProfitTracker was created with config
            mock_tracker.assert_called_once_with(self.config)
            
            # Check that initialize was called
            mock_instance.initialize.assert_called_once()
    
    def test_all_async(self):
        """Run all async tests."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_test_initialize())
        loop.run_until_complete(self.async_test_track_profit())
        loop.run_until_complete(self.async_test_get_profit_by_token_pair())
        loop.run_until_complete(self.async_test_get_roi())
        loop.run_until_complete(self.async_test_get_profit_time_series())
        loop.run_until_complete(self.async_test_get_top_token_pairs())
        loop.run_until_complete(self.async_test_get_profit_summary())
        loop.run_until_complete(self.async_test_create_profit_tracker())


if __name__ == '__main__':
    unittest.main()