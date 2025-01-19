"""
Start script for monitoring arbitrage opportunities without executing trades.
This allows safe testing of opportunity detection and validation.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any
from datetime import datetime
from arbitrage_bot.core.execution.detect_opportunities import (
    OpportunityDetector,
    ArbitrageOpportunity
)
from arbitrage_bot.utils.config_loader import create_config_loader
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.metrics.metrics_manager import MetricsManager
from arbitrage_bot.core.balance_manager import BalanceManager
from arbitrage_bot.core.analytics.analytics_system import AnalyticsSystem, create_analytics_system
from arbitrage_bot.core.ml.ml_system import MLSystem
from arbitrage_bot.core.monitoring.transaction_monitor import TransactionMonitor
from arbitrage_bot.core.dex.dex_manager import DEXManager
from arbitrage_bot.core.metrics.portfolio_tracker import PortfolioTracker
from arbitrage_bot.core.gas.gas_optimizer import GasOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ArbitrageMonitor')

async def monitor_opportunities():
    """Monitor arbitrage opportunities without executing trades."""
    try:
        # Load configuration
        config_loader = create_config_loader()
        config = config_loader.get_config()
        
        # Initialize Web3
        web3_config = config.get('web3', {})
        os.environ['BASE_RPC_URL'] = web3_config.get('provider_url')
        os.environ['CHAIN_ID'] = str(web3_config.get('chain_id', 8453))
        # Use existing environment variables for wallet credentials
        if not os.environ.get('WALLET_ADDRESS') or not os.environ.get('PRIVATE_KEY'):
            raise ValueError("WALLET_ADDRESS and PRIVATE_KEY environment variables must be set")
        
        web3_manager = await create_web3_manager()  # Use real network connection
        
        # Initialize metrics
        metrics_manager = MetricsManager(config=config)
        await metrics_manager.initialize()
        
        # Initialize components for monitoring mode
        from arbitrage_bot.core.metrics.portfolio_tracker import create_portfolio_tracker
        portfolio_tracker = await create_portfolio_tracker(
            web3_manager=web3_manager,
            wallet_address=os.environ['WALLET_ADDRESS'],
            config=config
        )
        if not portfolio_tracker:
            raise ValueError("Failed to create portfolio tracker")
        logger.info("Portfolio tracker initialized successfully")
        
        # Initialize DEX manager first
        from arbitrage_bot.core.dex.dex_manager import create_dex_manager
        dex_manager = await create_dex_manager(
            web3_manager=web3_manager,
            configs=config.get('dexes', {})
        )
        if not dex_manager:
            raise ValueError("Failed to create DEX manager")
        logger.info("DEX manager initialized successfully")
        
        # Initialize gas optimizer with DEX manager
        from arbitrage_bot.core.gas.gas_optimizer import create_gas_optimizer
        gas_optimizer = await create_gas_optimizer(dex_manager=dex_manager)
        if not gas_optimizer:
            raise ValueError("Failed to create gas optimizer")
        logger.info("Gas optimizer initialized successfully")
        
        # Initialize market analyzer
        from arbitrage_bot.core.analysis.market_analyzer import create_market_analyzer
        market_analyzer = await create_market_analyzer(
            web3_manager=web3_manager,
            config=config
        )
        if not market_analyzer:
            raise ValueError("Failed to create market analyzer")
        logger.info("Market analyzer initialized successfully")
        
        # Initialize analytics system before ML
        analytics = await create_analytics_system(
            web3_manager=web3_manager,
            tx_monitor=None,  # Will be set later
            market_analyzer=market_analyzer,
            portfolio_tracker=portfolio_tracker,
            gas_optimizer=gas_optimizer,
            config=config
        )
        if not analytics:
            raise ValueError("Failed to create analytics system")
        logger.info("Analytics system initialized successfully")
        
        # Initialize ML system with required dependencies
        from arbitrage_bot.core.ml.ml_system import create_ml_system
        ml_system = await create_ml_system(
            analytics=analytics,
            market_analyzer=market_analyzer,
            config=config
        )
        if not ml_system:
            raise ValueError("Failed to create ML system")
        logger.info("ML system initialized successfully")
        
        # Initialize monitor and update analytics with monitor
        monitor = None
        balance_manager = None
        detector = None
        
        try:
            # Initialize monitor
            from arbitrage_bot.core.monitoring.transaction_monitor import create_transaction_monitor
            monitor = await create_transaction_monitor(
                web3_manager=web3_manager,
                analytics=analytics,
                ml_system=ml_system,
                dex_manager=dex_manager
            )
            # Start monitoring in background task
            monitoring_task = asyncio.create_task(monitor.start_monitoring())
            logger.info("Monitor initialized and started monitoring")
            
            # Update analytics with monitor
            analytics.tx_monitor = monitor
            
            # Initialize balance manager singleton
            balance_manager = await BalanceManager.get_instance(
                web3_manager=web3_manager,
                analytics=analytics,
                ml_system=ml_system,
                monitor=monitor,
                dex_manager=dex_manager,
                max_position_size=float(config["risk"]["max_position_size"]),
                min_reserve_ratio=float(config["trading"]["balance_targets"]["rebalance_threshold_percent"]) / 100,
                rebalance_threshold=float(config["trading"]["balance_targets"]["rebalance_threshold_percent"]) / 100,
                risk_per_trade=float(config["trading"]["safety"]["max_price_impact"])
            )
            logger.info("Balance manager singleton initialized successfully")
            
            # Initialize opportunity detector
            detector = OpportunityDetector(
                config=config,
                web3_manager=web3_manager
            )
            await detector.ensure_initialized()
            logger.info("Detector initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            # Cleanup in reverse order of initialization
            if detector:
                try:
                    await detector.cleanup()
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up detector: {cleanup_error}")
            if balance_manager:
                try:
                    await balance_manager.cleanup()
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up balance manager: {cleanup_error}")
            if analytics:
                try:
                    await analytics.cleanup()
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up analytics: {cleanup_error}")
            if monitor:
                try:
                    await monitor.cleanup()
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up monitor: {cleanup_error}")
            raise
        
        logger.info(
            "Starting opportunity monitor:\n"
            f"  Network: Base\n"
            f"  Primary DEX: Aerodrome\n"
            f"  Pair: WETH/USDC\n"
            f"  Min Profit: ${config['trading']['min_profit_usd']}\n"
            f"  Max Trade Size: ${config['trading']['max_trade_size_usd']}"
        )
        
        opportunity_count = 0
        total_profit_potential = 0
        
        # Start metrics update task
        metrics_update_task = asyncio.create_task(metrics_manager._update_loop())
        
        while True:
            try:
                # Detect opportunities
                opportunities = await detector.detect_opportunities()
                
                if opportunities:
                    # Log each opportunity
                    for opp in opportunities:
                        opportunity_count += 1
                        total_profit_potential += opp.net_profit
                        
                        logger.info(
                            f"\nOpportunity #{opportunity_count}:\n"
                            f"  Route: {opp.buy_dex} -> {opp.sell_dex}\n"
                            f"  Pair: {opp.token_pair}\n"
                            f"  Profit: ${opp.net_profit:.2f} ({opp.profit_percent*100:.2f}%)\n"
                            f"  Gas Cost: ${opp.estimated_gas:.4f}\n"
                            f"  Confidence: {opp.confidence_score:.2f}\n"
                            f"  Route Type: {opp.route_type}"
                        )
                        
                        # Log market conditions if available
                        if opp.market_conditions:
                            conditions = opp.market_conditions
                            logger.info(
                                "Market Conditions:\n"
                                f"  Volatility: {conditions['risk_factors'].get('volatility', 0):.3f}\n"
                                f"  Volume Ratio: {conditions['risk_factors'].get('volume_ratio', 0):.3f}\n"
                                f"  Trend Alignment: {conditions['risk_factors'].get('trend_alignment', False)}"
                            )
                        
                        # Record opportunity metrics
                        await metrics_manager.update_metrics('performance', {
                            'pair': opp.token_pair,
                            'profit_usd': float(opp.net_profit),
                            'profit_percent': float(opp.profit_percent),
                            'gas_cost': float(opp.estimated_gas),
                            'confidence_score': float(opp.confidence_score),
                            'route_type': opp.route_type,
                            'buy_dex': opp.buy_dex,
                            'sell_dex': opp.sell_dex,
                            'timestamp': datetime.now().isoformat()
                        })
                
                # Log summary every minute
                if opportunity_count > 0 and opportunity_count % 60 == 0:
                    logger.info(
                        f"\nMonitoring Summary:\n"
                        f"  Total Opportunities: {opportunity_count}\n"
                        f"  Total Potential Profit: ${total_profit_potential:.2f}\n"
                        f"  Average Profit: ${total_profit_potential/opportunity_count:.2f}"
                    )
                
                # Sleep briefly
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Longer delay on error
                
    except Exception as e:
        logger.error(f"Fatal error in monitor: {e}")
        raise
    finally:
        # Cancel metrics update task
        if 'metrics_update_task' in locals():
            metrics_update_task.cancel()
            try:
                await metrics_update_task
            except asyncio.CancelledError:
                pass
        if metrics_manager:
            await metrics_manager.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(monitor_opportunities())
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
