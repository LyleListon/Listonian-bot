#!/usr/bin/env python
"""Integration test for the arbitrage bot."""

import argparse
import logging
import os
import sys
import time
import threading
from typing import Dict, Any, List, Optional

from arbitrage_bot.common.config.config_loader import load_config
from arbitrage_bot.common.logging.logger import setup_logger
from arbitrage_bot.common.events.event_bus import EventBus
from arbitrage_bot.core.arbitrage.factory import create_arbitrage_engine
from arbitrage_bot.core.market.market_monitor import MarketMonitor
from arbitrage_bot.core.transaction.transaction_manager import TransactionManager
from arbitrage_bot.integration.blockchain.factory import create_all_blockchain_connectors
from arbitrage_bot.integration.dex.factory import create_all_dex_connectors
from arbitrage_bot.integration.flash_loans.factory import create_all_flash_loan_providers
from arbitrage_bot.integration.mev_protection.factory import create_mev_protection_service
from arbitrage_bot.api.server import APIServer
from arbitrage_bot.dashboard.backend.server import DashboardServer
from arbitrage_bot.mcp.server import MCPServer
from arbitrage_bot.mcp.client import MCPClient


class IntegrationTest:
    """Integration test for the arbitrage bot."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the integration test.

        Args:
            config: Configuration dictionary.
        """
        self.config = config
        self.logger = setup_logger(config, "arbitrage_bot.test")

        # Create event bus
        self.event_bus = EventBus()

        # Initialize components
        self.blockchain_connectors = None
        self.dex_connectors = None
        self.flash_loan_providers = None
        self.mev_protection = None
        self.market_monitor = None
        self.transaction_manager = None
        self.arbitrage_engine = None
        self.api_server = None
        self.dashboard_server = None
        self.mcp_server = None
        self.mcp_client = None

        # Initialize test state
        self.test_results = {}
        self.test_passed = True

        self.logger.info("Integration test initialized")

    def run_tests(self) -> bool:
        """Run all integration tests.

        Returns:
            True if all tests passed, False otherwise.
        """
        self.logger.info("Starting integration tests")

        try:
            # Test component initialization
            self.test_init_components()

            # Test event bus
            self.test_event_bus()

            # Test blockchain connectors
            self.test_blockchain_connectors()

            # Test DEX connectors
            self.test_dex_connectors()

            # Test market monitor
            self.test_market_monitor()

            # Test arbitrage engine
            self.test_arbitrage_engine()

            # Test transaction manager
            self.test_transaction_manager()

            # Test API server
            self.test_api_server()

            # Test dashboard server
            self.test_dashboard_server()

            # Test MCP server and client
            self.test_mcp()

            # Print test results
            self.print_results()

            return self.test_passed

        except Exception as e:
            self.logger.error(f"Error running tests: {e}")
            return False

        finally:
            # Clean up
            self.cleanup()

    def test_init_components(self) -> None:
        """Test component initialization."""
        self.logger.info("Testing component initialization")

        try:
            # Initialize blockchain connectors
            self.blockchain_connectors = create_all_blockchain_connectors(self.config)
            self.logger.info(f"Created {len(self.blockchain_connectors)} blockchain connectors")

            # Initialize DEX connectors
            self.dex_connectors = create_all_dex_connectors(self.config, self.blockchain_connectors)
            self.logger.info(f"Created {len(self.dex_connectors)} DEX connectors")

            # Initialize flash loan providers
            self.flash_loan_providers = create_all_flash_loan_providers(self.config, self.blockchain_connectors)
            self.logger.info(f"Created {len(self.flash_loan_providers)} flash loan providers")

            # Initialize MEV protection
            self.mev_protection = create_mev_protection_service(self.config, self.blockchain_connectors)
            if self.mev_protection:
                self.logger.info(f"Created MEV protection service: {self.mev_protection.name}")

            # Initialize market monitor
            self.market_monitor = MarketMonitor(self.event_bus, self.config)

            # Add DEX connectors to market monitor
            for connector in self.dex_connectors:
                self.market_monitor.add_dex_connector(connector)

            # Initialize transaction manager
            self.transaction_manager = TransactionManager(self.event_bus, self.config)

            # Set flash loan provider and MEV protection for transaction manager
            if self.flash_loan_providers:
                default_provider = self.config.get("flash_loans", {}).get("default_provider")
                if default_provider and default_provider in self.flash_loan_providers:
                    self.transaction_manager.set_flash_loan_provider(
                        self.flash_loan_providers[default_provider]
                    )
                else:
                    # Use first provider
                    provider_name = next(iter(self.flash_loan_providers))
                    self.transaction_manager.set_flash_loan_provider(
                        self.flash_loan_providers[provider_name]
                    )

            if self.mev_protection:
                self.transaction_manager.set_mev_protection(self.mev_protection)

            # Initialize arbitrage engine
            self.arbitrage_engine = create_arbitrage_engine(self.config, self.event_bus)

            # Initialize API server
            self.api_server = APIServer(self, self.config)

            # Initialize dashboard server
            self.dashboard_server = DashboardServer(self, self.config)

            # Initialize MCP server
            self.mcp_server = MCPServer(self.config)

            # Initialize MCP client
            mcp_config = self.config.get("mcp", {})
            self.mcp_client = MCPClient(
                server_host=mcp_config.get("host", "127.0.0.1"),
                server_port=mcp_config.get("port", 9000),
                worker_id="test-worker",
                capabilities=["test"]
            )

            self.test_results["component_initialization"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            self.test_results["component_initialization"] = f"FAILED: {e}"
            self.test_passed = False

    def test_event_bus(self) -> None:
        """Test event bus."""
        self.logger.info("Testing event bus")

        try:
            # Create test event
            test_event_received = False

            # Define event handler
            def test_event_handler(event):
                nonlocal test_event_received
                test_event_received = True
                self.logger.info(f"Received test event: {event.data}")

            # Subscribe to test event
            self.event_bus.subscribe("test_event", test_event_handler)

            # Publish test event
            self.event_bus.publish_event("test_event", {"message": "Hello, world!"})

            # Check if event was received
            if test_event_received:
                self.test_results["event_bus"] = "PASSED"
            else:
                self.test_results["event_bus"] = "FAILED: Event not received"
                self.test_passed = False

        except Exception as e:
            self.logger.error(f"Error testing event bus: {e}")
            self.test_results["event_bus"] = f"FAILED: {e}"
            self.test_passed = False

    def test_blockchain_connectors(self) -> None:
        """Test blockchain connectors."""
        self.logger.info("Testing blockchain connectors")

        if not self.blockchain_connectors:
            self.test_results["blockchain_connectors"] = "SKIPPED: No connectors"
            return

        try:
            # Test each connector
            for name, connector in self.blockchain_connectors.items():
                # Test connection
                is_connected = connector.is_connected()
                self.logger.info(f"Connector {name} is connected: {is_connected}")

                # Test getting latest block number
                try:
                    block_number = connector.get_latest_block_number()
                    self.logger.info(f"Connector {name} latest block: {block_number}")
                except Exception as e:
                    self.logger.warning(f"Error getting latest block from {name}: {e}")

            self.test_results["blockchain_connectors"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing blockchain connectors: {e}")
            self.test_results["blockchain_connectors"] = f"FAILED: {e}"
            self.test_passed = False

    def test_dex_connectors(self) -> None:
        """Test DEX connectors."""
        self.logger.info("Testing DEX connectors")

        if not self.dex_connectors:
            self.test_results["dex_connectors"] = "SKIPPED: No connectors"
            return

        try:
            # Test each connector
            for connector in self.dex_connectors:
                # Test getting pairs
                pairs = connector.get_pairs()
                self.logger.info(f"Connector {connector.name} pairs: {len(pairs)}")

                # Test getting token prices
                prices = connector.get_token_prices()
                self.logger.info(f"Connector {connector.name} token prices: {len(prices)}")

                # Test getting token info
                info = connector.get_token_info()
                self.logger.info(f"Connector {connector.name} token info: {len(info)}")

            self.test_results["dex_connectors"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing DEX connectors: {e}")
            self.test_results["dex_connectors"] = f"FAILED: {e}"
            self.test_passed = False

    def test_market_monitor(self) -> None:
        """Test market monitor."""
        self.logger.info("Testing market monitor")

        try:
            # Start market monitor
            self.market_monitor.start()

            # Wait for market data to be updated
            time.sleep(2)

            # Get market data
            market_data = self.market_monitor.get_market_data()
            self.logger.info(f"Market data pairs: {len(market_data.get('pairs', []))}")

            # Get token prices
            token_prices = self.market_monitor.get_token_prices()
            self.logger.info(f"Token prices: {len(token_prices)}")

            # Get token info
            token_info = self.market_monitor.get_token_info()
            self.logger.info(f"Token info: {len(token_info)}")

            # Stop market monitor
            self.market_monitor.stop()

            self.test_results["market_monitor"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing market monitor: {e}")
            self.test_results["market_monitor"] = f"FAILED: {e}"
            self.test_passed = False

    def test_arbitrage_engine(self) -> None:
        """Test arbitrage engine."""
        self.logger.info("Testing arbitrage engine")

        try:
            # Update market data
            market_data = self.market_monitor.get_market_data()
            token_prices = self.market_monitor.get_token_prices()
            token_info = self.market_monitor.get_token_info()

            self.arbitrage_engine.update_market_data(market_data)
            self.arbitrage_engine.update_token_prices(token_prices)
            self.arbitrage_engine.update_token_info(token_info)

            # Find opportunities
            opportunities = self.arbitrage_engine.find_opportunities()
            self.logger.info(f"Found {len(opportunities)} arbitrage opportunities")

            # Test preparing execution plan
            if opportunities:
                opportunity = opportunities[0]
                execution_plan = self.arbitrage_engine.prepare_execution_plan(opportunity)
                self.logger.info(f"Prepared execution plan for opportunity {opportunity.get('id')}")

                # Test trade execution
                self.test_trade_execution(execution_plan)

            self.test_results["arbitrage_engine"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing arbitrage engine: {e}")
            self.test_results["arbitrage_engine"] = f"FAILED: {e}"
            self.test_passed = False

    def test_transaction_manager(self) -> None:
        """Test transaction manager."""
        self.logger.info("Testing transaction manager")

        try:
            # Get recent trades
            trades = self.transaction_manager.get_recent_trades()
            self.logger.info(f"Recent trades: {len(trades)}")

            self.test_results["transaction_manager"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing transaction manager: {e}")
            self.test_results["transaction_manager"] = f"FAILED: {e}"
            self.test_passed = False

    def test_trade_execution(self, execution_plan: Dict[str, Any]) -> None:
        """Test trade execution.

        Args:
            execution_plan: Execution plan for a trade.
        """
        self.logger.info("Testing trade execution")

        try:
            # Execute trade
            trade = self.transaction_manager.execute_trade(execution_plan)

            # Check trade result
            self.logger.info(f"Trade executed with status: {trade.get('status')}")

            if trade.get("status") == "failed":
                self.logger.warning(f"Trade failed: {trade.get('error')}")

            self.test_results["trade_execution"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing trade execution: {e}")
            self.test_results["trade_execution"] = f"FAILED: {e}"
            self.test_passed = False

    def test_api_server(self) -> None:
        """Test API server."""
        self.logger.info("Testing API server")

        try:
            # Start API server
            self.api_server.start()

            # Wait for server to start
            time.sleep(1)

            # Stop API server
            self.api_server.stop()

            self.test_results["api_server"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing API server: {e}")
            self.test_results["api_server"] = f"FAILED: {e}"
            self.test_passed = False

    def test_dashboard_server(self) -> None:
        """Test dashboard server."""
        self.logger.info("Testing dashboard server")

        try:
            # Start dashboard server
            self.dashboard_server.start()

            # Wait for server to start
            time.sleep(1)

            # Stop dashboard server
            self.dashboard_server.stop()

            self.test_results["dashboard_server"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing dashboard server: {e}")
            self.test_results["dashboard_server"] = f"FAILED: {e}"
            self.test_passed = False

    def test_mcp(self) -> None:
        """Test MCP server and client."""
        self.logger.info("Testing MCP server and client")

        try:
            # Start MCP server
            self.mcp_server.start()

            # Wait for server to start
            time.sleep(1)

            # Register task handler
            def test_task_handler(data):
                self.logger.info(f"Handling test task: {data}")
                return {"result": "success"}

            self.mcp_client.register_task_handler("test", test_task_handler)

            # Start MCP client
            self.mcp_client.start()

            # Wait for client to register
            time.sleep(1)

            # Add a task
            task_id = self.mcp_client.add_task("test", {"message": "Hello, world!"})
            self.logger.info(f"Added task: {task_id}")

            # Wait for task to be processed
            time.sleep(2)

            # Get task result
            task = self.mcp_client.get_task(task_id)
            self.logger.info(f"Task result: {task.get('result')}")

            # Stop MCP client
            self.mcp_client.stop()

            # Stop MCP server
            self.mcp_server.stop()

            self.test_results["mcp"] = "PASSED"

        except Exception as e:
            self.logger.error(f"Error testing MCP: {e}")
            self.test_results["mcp"] = f"FAILED: {e}"
            self.test_passed = False

    def print_results(self) -> None:
        """Print test results."""
        self.logger.info("Test results:")

        for test, result in self.test_results.items():
            self.logger.info(f"  {test}: {result}")

        if self.test_passed:
            self.logger.info("All tests PASSED")
        else:
            self.logger.info("Some tests FAILED")

    def cleanup(self) -> None:
        """Clean up after tests."""
        self.logger.info("Cleaning up")

        # Stop components
        if self.market_monitor:
            self.market_monitor.stop()

        if self.api_server:
            self.api_server.stop()

        if self.dashboard_server:
            self.dashboard_server.stop()

        if self.mcp_client:
            self.mcp_client.stop()

        if self.mcp_server:
            self.mcp_server.stop()

        # Disconnect blockchain connectors
        if self.blockchain_connectors:
            for name, connector in self.blockchain_connectors.items():
                try:
                    connector.disconnect()
                except Exception as e:
                    self.logger.error(f"Error disconnecting from {name}: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics for API and dashboard servers.

        Returns:
            Metrics dictionary.
        """
        return {
            "status": "running",
            "uptime": 0,
            "trading": {
                "total_trades": 0,
                "successful_trades": 0,
                "failed_trades": 0,
                "total_profit_usd": 0.0,
                "total_gas_cost_usd": 0.0,
                "net_profit_usd": 0.0,
            },
        }

    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades for API and dashboard servers.

        Args:
            limit: Maximum number of trades to return.

        Returns:
            List of recent trades.
        """
        if self.transaction_manager:
            return self.transaction_manager.get_recent_trades(limit)

        return []


def main():
    """Main entry point for the integration test."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Arbitrage Bot Integration Test")
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Environment to use (development, production, test)",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.env)

    # Run integration test
    test = IntegrationTest(config)
    success = test.run_tests()

    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
