#!/usr/bin/env python
"""Main entry point for the arbitrage bot."""

import argparse
import logging
import signal
import sys
import time
from typing import Dict, List, Any, Optional

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


class ArbitrageBot:
    """Main class for the arbitrage bot."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the arbitrage bot.

        Args:
            config: The configuration dictionary.
        """
        self.config = config
        self.logger = setup_logger(config, "arbitrage_bot")
        self.running = False
        self.start_time = time.time()

        # Create event bus
        self.event_bus = EventBus()

        # Create blockchain connectors
        self.blockchain_connectors = create_all_blockchain_connectors(config)
        self.logger.info(f"Created {len(self.blockchain_connectors)} blockchain connectors")

        # Create DEX connectors
        self.dex_connectors = create_all_dex_connectors(config, self.blockchain_connectors)
        self.logger.info(f"Created {len(self.dex_connectors)} DEX connectors")

        # Create flash loan providers
        self.flash_loan_providers = create_all_flash_loan_providers(config, self.blockchain_connectors)
        self.logger.info(f"Created {len(self.flash_loan_providers)} flash loan providers")

        # Create MEV protection service
        self.mev_protection = create_mev_protection_service(config, self.blockchain_connectors)
        if self.mev_protection:
            self.logger.info(f"Created MEV protection service: {self.mev_protection.name}")

        # Create core components
        self.market_monitor = MarketMonitor(self.event_bus, config)
        self.transaction_manager = TransactionManager(self.event_bus, config)
        self.arbitrage_engine = create_arbitrage_engine(config, self.event_bus)

        # Add DEX connectors to market monitor
        for connector in self.dex_connectors:
            self.market_monitor.add_dex_connector(connector)

        # Set blockchain connectors for transaction manager
        self.transaction_manager.set_blockchain_connectors(self.blockchain_connectors)

        # Set DEX connectors for transaction manager
        self.transaction_manager.set_dex_connectors(self.dex_connectors)

        # Set flash loan provider and MEV protection for transaction manager
        if self.flash_loan_providers:
            default_provider = config.get("flash_loans", {}).get("default_provider")
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

        # Set up event handlers
        self._setup_event_handlers()

        self.logger.info("Arbitrage bot initialized")

    def _setup_event_handlers(self) -> None:
        """Set up event handlers."""
        # Handle market data updates
        self.event_bus.subscribe(
            "market_data_updated",
            self._handle_market_data_updated
        )

        # Handle opportunity detection
        self.event_bus.subscribe(
            "opportunity_detected",
            self._handle_opportunity_detected
        )

        # Handle trade completion
        self.event_bus.subscribe(
            "trade_completed",
            self._handle_trade_completed
        )

    def _handle_market_data_updated(self, event: Any) -> None:
        """Handle market data updated event.

        Args:
            event: The event object.
        """
        data = event.data

        # Update arbitrage engine with new market data
        self.arbitrage_engine.update_market_data(data.get("market_data", {}))
        self.arbitrage_engine.update_token_prices(data.get("token_prices", {}))
        self.arbitrage_engine.update_token_info(data.get("token_info", {}))

        # Find arbitrage opportunities
        self.arbitrage_engine.find_opportunities()

    def _handle_opportunity_detected(self, event: Any) -> None:
        """Handle opportunity detected event.

        Args:
            event: The event object.
        """
        opportunity = event.data

        # Check if trading is enabled
        trading_enabled = self.config.get("trading", {}).get("trading_enabled", False)
        if not trading_enabled:
            self.logger.info(
                f"Opportunity {opportunity.get('id')} detected, but trading is disabled"
            )
            return

        # Prepare execution plan
        execution_plan = self.arbitrage_engine.prepare_execution_plan(opportunity)

        # Execute trade
        self.transaction_manager.execute_trade(execution_plan)

    def _handle_trade_completed(self, event: Any) -> None:
        """Handle trade completed event.

        Args:
            event: The event object.
        """
        trade = event.data

        if trade.get("status") == "success":
            self.logger.info(
                f"Trade {trade.get('id')} completed successfully with "
                f"profit {trade.get('net_profit_usd', 0.0):.2f} USD"
            )
        else:
            self.logger.warning(
                f"Trade {trade.get('id')} failed: {trade.get('error', 'Unknown error')}"
            )

    def start(self, block: bool = True) -> None:
        """Start the arbitrage bot.

        Args:
            block: Whether to block the main thread.
        """
        self.running = True
        self.logger.info("Starting arbitrage bot")

        # Start components
        self.market_monitor.start()

        if block:
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.stop()

    def stop(self) -> None:
        """Stop the arbitrage bot."""
        self.running = False
        self.logger.info("Stopping arbitrage bot")

        # Stop components
        self.market_monitor.stop()

        # Disconnect blockchain connectors
        for name, connector in self.blockchain_connectors.items():
            try:
                connector.disconnect()
                self.logger.info(f"Disconnected from {name} blockchain")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name} blockchain: {e}")

        self.logger.info("Arbitrage bot stopped")

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from the arbitrage bot.

        Returns:
            A dictionary of metrics.
        """
        # Calculate uptime
        uptime = int(time.time() - self.start_time)

        # Get recent trades
        recent_trades = self.get_recent_trades(limit=100)

        # Calculate trading metrics
        total_trades = len(recent_trades)
        successful_trades = sum(1 for t in recent_trades if t.get("status") == "success")
        failed_trades = total_trades - successful_trades

        total_profit_usd = sum(t.get("net_profit_usd", 0.0) for t in recent_trades if t.get("status") == "success")
        total_gas_cost_usd = sum(t.get("estimated_gas_cost_usd", 0.0) for t in recent_trades)

        return {
            "status": "running" if self.running else "stopped",
            "uptime": uptime,
            "trading": {
                "total_trades": total_trades,
                "successful_trades": successful_trades,
                "failed_trades": failed_trades,
                "total_profit_usd": total_profit_usd,
                "total_gas_cost_usd": total_gas_cost_usd,
                "net_profit_usd": total_profit_usd - total_gas_cost_usd,
            },
        }

    def get_recent_trades(self, limit: int = 10) -> list:
        """Get recent trades from the arbitrage bot.

        Args:
            limit: The maximum number of trades to return.

        Returns:
            A list of recent trades.
        """
        return self.transaction_manager.get_recent_trades(limit)


def main():
    """Main entry point for the arbitrage bot."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Arbitrage Bot")
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Environment to use (development, production, test)",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.env)

    # Set up logging
    logger = setup_logger(config)

    # Create and start the bot
    bot = ArbitrageBot(config)

    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the bot
    try:
        logger.info("Starting the bot...")
        bot.start()
        logger.info("Bot started successfully")
    except Exception as e:
        logger.error(f"Error starting the bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
