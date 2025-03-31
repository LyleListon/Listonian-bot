"""
Tests for the AdvancedPathFinder class.

This module contains tests for the AdvancedPathFinder class, which is responsible
for finding arbitrage paths using the Bellman-Ford algorithm and other advanced
path finding techniques.
"""

import asyncio
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arbitrage_bot.core.arbitrage.path.advanced_path_finder import AdvancedPathFinder
from arbitrage_bot.core.arbitrage.path.interfaces import ArbitragePath, Pool


class MockGraphExplorer:
    """Mock GraphExplorer for testing."""
    
    def __init__(self, mock_cycles=None):
        self.mock_cycles = mock_cycles or []
        self.initialize_called = False
        self.close_called = False
    
    async def initialize(self):
        self.initialize_called = True
        return True
    
    async def get_graph(self):
        return {}
    
    async def find_cycles(self, start_token, max_length, max_cycles, filters):
        return self.mock_cycles
    
    async def close(self):
        self.close_called = True


class TestAdvancedPathFinder(unittest.IsolatedAsyncioTestCase):
    """Test cases for the AdvancedPathFinder class."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Create mock cycles
        self.mock_cycles = [
            {
                'tokens': [
                    '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                    '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC
                    '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT
                    '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                ],
                'pools': [
                    {
                        'address': '0x1234567890123456789012345678901234567890',
                        'token0': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                        'token1': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                        'reserves0': Decimal('100'),
                        'reserves1': Decimal('100000'),
                        'fee': 3000,
                        'pool_type': 'constant_product',
                        'dex': 'uniswap_v2'
                    },
                    {
                        'address': '0x2345678901234567890123456789012345678901',
                        'token0': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                        'token1': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                        'reserves0': Decimal('100000'),
                        'reserves1': Decimal('100000'),
                        'fee': 3000,
                        'pool_type': 'constant_product',
                        'dex': 'uniswap_v2'
                    },
                    {
                        'address': '0x3456789012345678901234567890123456789012',
                        'token0': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                        'token1': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                        'reserves0': Decimal('100000'),
                        'reserves1': Decimal('100'),
                        'fee': 3000,
                        'pool_type': 'constant_product',
                        'dex': 'uniswap_v2'
                    }
                ],
                'dexes': ['uniswap_v2', 'uniswap_v2', 'uniswap_v2'],
                'profit': Decimal('0.01'),
                'optimal_amount': Decimal('1.0'),
                'expected_output': Decimal('1.01')
            },
            {
                'tokens': [
                    '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                    '0x6B175474E89094C44Da98b954EedeAC495271d0F',  # DAI
                    '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                ],
                'pools': [
                    {
                        'address': '0x4567890123456789012345678901234567890123',
                        'token0': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                        'token1': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                        'reserves0': Decimal('100'),
                        'reserves1': Decimal('100000'),
                        'fee': 3000,
                        'pool_type': 'constant_product',
                        'dex': 'uniswap_v3'
                    },
                    {
                        'address': '0x5678901234567890123456789012345678901234',
                        'token0': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                        'token1': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                        'reserves0': Decimal('100000'),
                        'reserves1': Decimal('101'),
                        'fee': 3000,
                        'pool_type': 'constant_product',
                        'dex': 'uniswap_v3'
                    }
                ],
                'dexes': ['uniswap_v3', 'uniswap_v3'],
                'profit': Decimal('0.005'),
                'optimal_amount': Decimal('1.0'),
                'expected_output': Decimal('1.005')
            }
        ]
        
        # Create mock graph explorer
        self.graph_explorer = MockGraphExplorer(self.mock_cycles)
        
        # Create path finder
        self.path_finder = AdvancedPathFinder(
            graph_explorer=self.graph_explorer,
            max_hops=5,
            max_paths_per_token=20,
            concurrency_limit=10
        )
        
        # Initialize path finder
        await self.path_finder.initialize()
    
    async def asyncTearDown(self):
        """Tear down test fixtures."""
        await self.path_finder.close()
    
    async def test_initialization(self):
        """Test initialization of the path finder."""
        self.assertTrue(self.graph_explorer.initialize_called)
        self.assertEqual(self.path_finder.max_hops, 5)
        self.assertEqual(self.path_finder.max_paths_per_token, 20)
        self.assertEqual(self.path_finder.concurrency_limit, 10)
    
    async def test_find_paths(self):
        """Test finding arbitrage paths."""
        # Find paths
        paths = await self.path_finder.find_paths(
            start_token='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            max_paths=10,
            filters={
                'max_hops': 4,
                'min_profit': Decimal('0.001')
            }
        )
        
        # Check paths
        self.assertEqual(len(paths), 2)
        
        # Check first path
        path1 = paths[0]
        self.assertEqual(path1.tokens, self.mock_cycles[0]['tokens'])
        self.assertEqual(len(path1.pools), 3)
        self.assertEqual(path1.dexes, self.mock_cycles[0]['dexes'])
        self.assertEqual(path1.profit, self.mock_cycles[0]['profit'])
        self.assertEqual(path1.optimal_amount, self.mock_cycles[0]['optimal_amount'])
        self.assertEqual(path1.expected_output, self.mock_cycles[0]['expected_output'])
        
        # Check second path
        path2 = paths[1]
        self.assertEqual(path2.tokens, self.mock_cycles[1]['tokens'])
        self.assertEqual(len(path2.pools), 2)
        self.assertEqual(path2.dexes, self.mock_cycles[1]['dexes'])
        self.assertEqual(path2.profit, self.mock_cycles[1]['profit'])
        self.assertEqual(path2.optimal_amount, self.mock_cycles[1]['optimal_amount'])
        self.assertEqual(path2.expected_output, self.mock_cycles[1]['expected_output'])
    
    async def test_find_paths_with_filters(self):
        """Test finding arbitrage paths with filters."""
        # Find paths with min_profit filter
        paths = await self.path_finder.find_paths(
            start_token='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            max_paths=10,
            filters={
                'min_profit': Decimal('0.006')
            }
        )
        
        # Check paths (only the first path should be returned)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].tokens, self.mock_cycles[0]['tokens'])
        
        # Find paths with max_hops filter
        paths = await self.path_finder.find_paths(
            start_token='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            max_paths=10,
            filters={
                'max_hops': 2
            }
        )
        
        # Check paths (only the second path should be returned)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].tokens, self.mock_cycles[1]['tokens'])
    
    async def test_find_paths_with_max_paths(self):
        """Test finding arbitrage paths with max_paths limit."""
        # Find paths with max_paths=1
        paths = await self.path_finder.find_paths(
            start_token='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            max_paths=1,
            filters={}
        )
        
        # Check paths (only the first path should be returned)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].tokens, self.mock_cycles[0]['tokens'])
    
    async def test_find_paths_with_invalid_start_token(self):
        """Test finding arbitrage paths with invalid start token."""
        # Find paths with invalid start token
        paths = await self.path_finder.find_paths(
            start_token='0x0000000000000000000000000000000000000000',  # Invalid token
            max_paths=10,
            filters={}
        )
        
        # Check paths (no paths should be returned)
        self.assertEqual(len(paths), 0)
    
    async def test_close(self):
        """Test closing the path finder."""
        # Close path finder
        await self.path_finder.close()
        
        # Check if graph explorer was closed
        self.assertTrue(self.graph_explorer.close_called)


if __name__ == '__main__':
    unittest.main()