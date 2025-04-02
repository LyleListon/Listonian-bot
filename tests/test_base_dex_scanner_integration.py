"""
Tests for Base DEX Scanner MCP integration.

This module contains tests for the Base DEX Scanner MCP integration.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from arbitrage_bot.integration.base_dex_scanner_mcp import BaseDexScannerMCP, BaseDexScannerSource
from arbitrage_bot.integration.base_dex_trading_executor import BaseDexTradingExecutor


class TestBaseDexScannerMCP(unittest.TestCase):
    """Tests for BaseDexScannerMCP."""

    def setUp(self):
        """Set up test fixtures."""
        self.scanner = BaseDexScannerMCP()
        
        # Mock MCP tool calls
        self.scanner._call_mcp_tool = AsyncMock()
        
        # Sample data
        self.sample_dexes = [
            {
                "name": "BaseSwap",
                "factory_address": "0x0000000000000000000000000000000000000001",
                "router_address": "0x0000000000000000000000000000000000000002",
                "type": "uniswap_v2",
                "version": "v2"
            },
            {
                "name": "Aerodrome",
                "factory_address": "0x0000000000000000000000000000000000000003",
                "router_address": "0x0000000000000000000000000000000000000004",
                "type": "uniswap_v2",
                "version": "v2"
            }
        ]
        
        self.sample_pools = [
            {
                "address": "0x0000000000000000000000000000000000000005",
                "token0": {
                    "address": "0x0000000000000000000000000000000000000006",
                    "symbol": "WETH",
                    "decimals": 18
                },
                "token1": {
                    "address": "0x0000000000000000000000000000000000000007",
                    "symbol": "USDC",
                    "decimals": 6
                },
                "liquidity_usd": 1000000.0
            }
        ]

    async def async_setup(self):
        """Async setup."""
        # Set up mock responses
        self.scanner._call_mcp_tool.return_value = self.sample_dexes

    async def test_scan_dexes(self):
        """Test scan_dexes method."""
        await self.async_setup()
        
        # Call the method
        dexes = await self.scanner.scan_dexes()
        
        # Verify the result
        self.assertEqual(dexes, self.sample_dexes)
        self.scanner._call_mcp_tool.assert_called_once_with(
            "scan_dexes", {}
        )

    async def test_get_factory_pools(self):
        """Test get_factory_pools method."""
        await self.async_setup()
        
        # Set up mock response for get_factory_pools
        self.scanner._call_mcp_tool.return_value = self.sample_pools
        
        # Call the method
        factory_address = "0x0000000000000000000000000000000000000001"
        pools = await self.scanner.get_factory_pools(factory_address)
        
        # Verify the result
        self.assertEqual(pools, self.sample_pools)
        self.scanner._call_mcp_tool.assert_called_once_with(
            "get_factory_pools", {"factory_address": factory_address}
        )


class TestBaseDexScannerSource(unittest.TestCase):
    """Tests for BaseDexScannerSource."""

    def setUp(self):
        """Set up test fixtures."""
        self.source = BaseDexScannerSource()
        
        # Mock MCP scanner
        self.source.scanner = MagicMock()
        self.source.scanner.scan_dexes = AsyncMock()
        self.source.scanner.get_factory_pools = AsyncMock()
        
        # Sample data
        self.sample_dexes = [
            {
                "name": "BaseSwap",
                "factory_address": "0x0000000000000000000000000000000000000001",
                "router_address": "0x0000000000000000000000000000000000000002",
                "type": "uniswap_v2",
                "version": "v2"
            }
        ]
        
        self.sample_pools = [
            {
                "address": "0x0000000000000000000000000000000000000005",
                "token0": {
                    "address": "0x0000000000000000000000000000000000000006",
                    "symbol": "WETH",
                    "decimals": 18
                },
                "token1": {
                    "address": "0x0000000000000000000000000000000000000007",
                    "symbol": "USDC",
                    "decimals": 6
                },
                "liquidity_usd": 1000000.0
            }
        ]
        
        self.sample_opportunities = [
            MagicMock(
                id="opp1",
                token_pair="WETH/USDC",
                buy_dex="BaseSwap",
                sell_dex="Aerodrome",
                is_profitable=True,
                net_profit_usd=Decimal("10.5"),
                expected_profit_wei=1000000000000000000,  # 1 ETH
                output_price_usd=Decimal("2000.0")
            )
        ]

    async def async_setup(self):
        """Async setup."""
        # Set up mock responses
        self.source.scanner.scan_dexes.return_value = self.sample_dexes
        self.source.scanner.get_factory_pools.return_value = self.sample_pools
        
        # Mock detect_arbitrage_opportunities
        self.source.detect_arbitrage_opportunities = AsyncMock(
            return_value=self.sample_opportunities
        )

    async def test_initialize(self):
        """Test initialize method."""
        # Call the method
        result = await self.source.initialize()
        
        # Verify the result
        self.assertTrue(result)

    async def test_fetch_dexes(self):
        """Test fetch_dexes method."""
        await self.async_setup()
        
        # Call the method
        dexes = await self.source.fetch_dexes()
        
        # Verify the result
        self.assertEqual(dexes, self.sample_dexes)
        self.source.scanner.scan_dexes.assert_called_once()

    async def test_get_pools_for_dex(self):
        """Test get_pools_for_dex method."""
        await self.async_setup()
        
        # Call the method
        dex = self.sample_dexes[0]
        pools = await self.source.get_pools_for_dex(dex)
        
        # Verify the result
        self.assertEqual(pools, self.sample_pools)
        self.source.scanner.get_factory_pools.assert_called_once_with(
            dex["factory_address"]
        )

    async def test_detect_arbitrage_opportunities(self):
        """Test detect_arbitrage_opportunities method."""
        await self.async_setup()
        
        # Call the method
        opportunities = await self.source.detect_arbitrage_opportunities()
        
        # Verify the result
        self.assertEqual(opportunities, self.sample_opportunities)


class TestBaseDexTradingExecutor(unittest.TestCase):
    """Tests for BaseDexTradingExecutor."""

    def setUp(self):
        """Set up test fixtures."""
        # Create executor with mock private key
        self.executor = BaseDexTradingExecutor(
            private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            wallet_address="0x1234567890123456789012345678901234567890",
            min_profit_usd=1.0
        )
        
        # Mock dependencies
        self.executor.source = MagicMock()
        self.executor.source.initialize = AsyncMock(return_value=True)
        self.executor.source.detect_arbitrage_opportunities = AsyncMock()
        
        self.executor.web3 = MagicMock()
        self.executor.web3.eth.block_number = 12345
        self.executor.web3.eth.gas_price = 20000000000  # 20 gwei
        self.executor.web3.eth.get_transaction_count = MagicMock(return_value=0)
        
        self.executor.flashbots_provider = MagicMock()
        
        # Sample data
        self.sample_opportunity = MagicMock(
            id="opp1",
            token_pair="WETH/USDC",
            buy_dex="BaseSwap",
            sell_dex="Aerodrome",
            is_profitable=True,
            net_profit_usd=Decimal("10.5"),
            expected_profit_wei=1000000000000000000,  # 1 ETH
            output_price_usd=Decimal("2000.0")
        )
        
        # Mock methods
        self.executor._validate_opportunity = AsyncMock(return_value=True)
        self.executor._create_transactions = AsyncMock(return_value=[{"from": "0x1234"}])
        self.executor._simulate_bundle = AsyncMock(
            return_value={"success": True, "profit_wei": 1000000000000000000}
        )
        self.executor._submit_bundle = AsyncMock(
            return_value={"success": True, "bundle_hash": "0x1234"}
        )
        self.executor._wait_for_inclusion = AsyncMock(
            return_value={
                "included": True,
                "transaction_hash": "0x1234",
                "block_number": 12346,
                "profit_wei": 1000000000000000000,
                "gas_used": 200000,
                "gas_price": 20000000000,
                "status": "included"
            }
        )

    async def test_initialize(self):
        """Test initialize method."""
        # Call the method
        result = await self.executor.initialize()
        
        # Verify the result
        self.assertTrue(result)
        self.executor.source.initialize.assert_called_once()

    @patch("asyncio.create_task")
    async def test_start_stop(self, mock_create_task):
        """Test start and stop methods."""
        # Call start
        await self.executor.start()
        
        # Verify start
        self.assertTrue(self.executor._running)
        mock_create_task.assert_called_once()
        
        # Call stop
        await self.executor.stop()
        
        # Verify stop
        self.assertFalse(self.executor._running)

    async def test_execute_trade(self):
        """Test _execute_trade method."""
        # Set up source to return our sample opportunity
        self.executor.source.detect_arbitrage_opportunities.return_value = [
            self.sample_opportunity
        ]
        
        # Call the method
        result = await self.executor._execute_trade(self.sample_opportunity)
        
        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["transaction_hash"], "0x1234")
        self.assertEqual(result["block_number"], 12346)
        self.assertEqual(result["profit_wei"], 1000000000000000000)
        
        # Verify method calls
        self.executor._validate_opportunity.assert_called_once_with(self.sample_opportunity)
        self.executor._create_transactions.assert_called_once()
        self.executor._simulate_bundle.assert_called_once()
        self.executor._submit_bundle.assert_called_once()
        self.executor._wait_for_inclusion.assert_called_once_with("0x1234")


if __name__ == "__main__":
    # Run tests
    unittest.main()