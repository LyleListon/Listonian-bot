"""
Start script for monitoring arbitrage opportunities without executing trades.
This allows safe testing of opportunity detection and validation.
"""

import asyncio
import logging
from typing import List, Dict, Any
from arbitrage_bot.core.execution.detect_opportunities import OpportunityDetector, ArbitrageOpportunity
from arbitrage_bot.utils.config_loader import create_config_loader
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.core.metrics.metrics_manager import create_metrics_manager

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
        network_config = config.get('network', {})
        web3_manager = await create_web3_manager(
            provider_url=network_config.get('rpc_url'),
            chain_id=network_config.get('chain_id')
        )
        
        # Initialize metrics
        metrics_manager = create_metrics_manager(config)
        
        # Create opportunity detector
        detector = OpportunityDetector(
            config=config,
            web3_manager=web3_manager,
            balance_manager=None  # Not needed for monitoring only
        )
        
        logger.info(
            "Starting opportunity monitor:\n"
            f"  Network: {network_config.get('name')}\n"
            f"  Primary DEX: Aerodrome\n"
            f"  Pair: WETH/USDC\n"
            f"  Min Profit: ${config['trading']['min_profit_usd']}\n"
            f"  Max Trade Size: ${config['trading']['max_trade_size_usd']}"
        )
        
        opportunity_count = 0
        total_profit_potential = 0
        
        # Start metrics saving task
        metrics_save_task = asyncio.create_task(metrics_manager.save_metrics())
        
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
                        await metrics_manager.record_opportunity({
                            'pair': opp.token_pair,
                            'profit_usd': opp.net_profit,
                            'profit_percent': opp.profit_percent,
                            'gas_cost': opp.estimated_gas,
                            'confidence_score': opp.confidence_score,
                            'route_type': opp.route_type,
                            'buy_dex': opp.buy_dex,
                            'sell_dex': opp.sell_dex
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
        # Cancel metrics saving task
        if 'metrics_save_task' in locals():
            metrics_save_task.cancel()
            try:
                await metrics_save_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(monitor_opportunities())
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
