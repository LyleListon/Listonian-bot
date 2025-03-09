#!/usr/bin/env python
"""
MEV Protection Example

This script demonstrates how to use the MEV Protection Optimizer to enhance arbitrage 
transactions with advanced protection against MEV attacks, working in conjunction with 
Flashbots RPC integration and Flash Loan Manager.
"""

import asyncio
import logging
import json
from decimal import Decimal
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_mev_protection():
    """Demonstrate the MEV Protection features."""
    logger.info("=" * 70)
    logger.info("MEV PROTECTION OPTIMIZER EXAMPLE")
    logger.info("=" * 70)
    
    try:
        # Step 1: Import required components
        logger.info("\n[Step 1] Importing required components")
        from arbitrage_bot.utils.config_loader import load_config
        from arbitrage_bot.core.web3.web3_manager import create_web3_manager
        from arbitrage_bot.integration.flashbots_integration import setup_flashbots_rpc
        from arbitrage_bot.core.flash_loan_manager_async import create_flash_loan_manager
        from arbitrage_bot.integration.mev_protection import create_mev_protection_optimizer
        
        logger.info("✓ Successfully imported required components")
        
        # Step 2: Load configuration and initialize Web3Manager
        logger.info("\n[Step 2] Loading configuration and initializing Web3Manager")
        config = load_config()
        
        # Configure MEV protection settings if not present
        if 'mev_protection' not in config:
            config['mev_protection'] = {
                'enabled': True,
                'use_flashbots': True,
                'max_bundle_size': 5,
                'max_blocks_ahead': 3,
                'min_priority_fee': '1.5',
                'max_priority_fee': '3',
                'sandwich_detection': True,
                'frontrun_detection': True,
                'adaptive_gas': True
            }
        
        # Get token addresses for examples
        weth_address = config.get('tokens', {}).get('WETH', '0x4200000000000000000000000000000000000006')
        usdc_address = config.get('tokens', {}).get('USDC', '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
        
        # Initialize Web3Manager
        web3_manager = await create_web3_manager(
            provider_url=config.get('provider_url'),
            chain_id=config.get('chain_id'),
            private_key=config.get('private_key')
        )
        
        logger.info(f"✓ Configuration loaded and Web3Manager initialized")
        logger.info(f"  Connected to: {web3_manager.provider_url}")
        logger.info(f"  Wallet: {web3_manager.wallet_address}")
        
        # Step 3: Set up Flashbots RPC integration
        logger.info("\n[Step 3] Setting up Flashbots RPC integration")
        flashbots_components = await setup_flashbots_rpc(
            web3_manager=web3_manager,
            config=config
        )
        
        flashbots_manager = flashbots_components['flashbots_manager']
        balance_validator = flashbots_components['balance_validator']
        
        logger.info(f"✓ Flashbots RPC integration set up")
        logger.info(f"  Relay URL: {flashbots_manager.relay_url}")
        
        # Step 4: Initialize Flash Loan Manager
        logger.info("\n[Step 4] Initializing Flash Loan Manager")
        flash_loan_manager = await create_flash_loan_manager(
            web3_manager=web3_manager,
            config=config,
            flashbots_manager=flashbots_manager
        )
        
        logger.info("✓ Flash Loan Manager initialized")
        
        # Step 5: Initialize MEV Protection Optimizer
        logger.info("\n[Step 5] Initializing MEV Protection Optimizer")
        mev_optimizer = await create_mev_protection_optimizer(
            web3_manager=web3_manager,
            config=config,
            flashbots_manager=flashbots_manager
        )
        
        logger.info("✓ MEV Protection Optimizer initialized")
        logger.info(f"  Max bundle size: {mev_optimizer.max_bundle_size}")
        logger.info(f"  Max blocks ahead: {mev_optimizer.max_blocks_ahead}")
        logger.info(f"  Min priority fee: {mev_optimizer.min_priority_fee / 1e9} gwei")
        logger.info(f"  Max priority fee: {mev_optimizer.max_priority_fee / 1e9} gwei")
        
        # Step 6: Analyze mempool for MEV risk
        logger.info("\n[Step 6] Analyzing mempool for MEV risk")
        risk_assessment = await mev_optimizer.analyze_mempool_risk()
        
        logger.info(f"✓ Mempool risk assessment completed")
        logger.info(f"  Risk level: {risk_assessment['risk_level'].upper()}")
        logger.info(f"  Current gas price: {web3_manager.w3.from_wei(risk_assessment['gas_price'], 'gwei'):.2f} gwei")
        logger.info(f"  Average gas price: {web3_manager.w3.from_wei(risk_assessment['avg_gas_price'], 'gwei'):.2f} gwei")
        logger.info(f"  Gas price volatility: {risk_assessment['gas_volatility']:.2f}")
        
        if 'risk_factors' in risk_assessment:
            logger.info(f"  Risk factors: {', '.join(risk_assessment['risk_factors'])}")
        
        # Step 7: Create a sample arbitrage route for demonstration
        logger.info("\n[Step 7] Creating sample arbitrage transaction")
        
        # Amount to borrow in the example
        weth_amount = web3_manager.w3.to_wei(0.1, 'ether')  # 0.1 WETH
        
        # Sample route for arbitrage
        route = [
            {
                "dex_id": 1,  # BaseSwap
                "dex": "baseswap",
                "token_in": weth_address,
                "token_out": usdc_address,
                "amount_in": weth_amount,
                "amount_out": 180 * 10**6  # 180 USDC
            },
            {
                "dex_id": 2,  # PancakeSwap
                "dex": "pancakeswap",
                "token_in": usdc_address,
                "token_out": weth_address,
                "amount_in": 180 * 10**6,  # 180 USDC
                "amount_out": weth_amount + web3_manager.w3.to_wei(0.003, 'ether')  # 0.103 WETH
            }
        ]
        
        # Create sample transaction (simulated)
        sample_tx = {
            'from': web3_manager.wallet_address,
            'to': weth_address,
            'value': 0,
            'gas': 200000,
            'gasPrice': web3_manager.w3.to_wei(2, 'gwei'),
            'data': '0x',
            'nonce': await web3_manager.w3.eth.get_transaction_count(web3_manager.wallet_address)
        }
        
        # Create second transaction (simulated)
        sample_tx2 = {
            'from': web3_manager.wallet_address,
            'to': usdc_address,
            'value': 0,
            'gas': 200000,
            'gasPrice': web3_manager.w3.to_wei(2, 'gwei'),
            'data': '0x',
            'nonce': await web3_manager.w3.eth.get_transaction_count(web3_manager.wallet_address) + 1
        }
        
        transactions = [sample_tx, sample_tx2]
        
        logger.info(f"✓ Sample transactions created")
        logger.info(f"  Transaction count: {len(transactions)}")
        
        # Step 8: Optimize bundle strategy
        logger.info("\n[Step 8] Optimizing bundle strategy")
        
        bundle_strategy = await mev_optimizer.optimize_bundle_strategy(
            transactions=transactions,
            target_token_addresses=[weth_address, usdc_address],
            expected_profit=web3_manager.w3.to_wei(0.003, 'ether'),  # 0.003 WETH
            priority_level="medium"
        )
        
        logger.info(f"✓ Bundle strategy optimized")
        logger.info(f"  Gas settings:")
        logger.info(f"    Max fee per gas: {web3_manager.w3.from_wei(bundle_strategy['gas_settings']['max_fee_per_gas'], 'gwei'):.2f} gwei")
        logger.info(f"    Max priority fee: {web3_manager.w3.from_wei(bundle_strategy['gas_settings']['max_priority_fee_per_gas'], 'gwei'):.2f} gwei")
        logger.info(f"  Target blocks: {bundle_strategy['block_targets']}")
        logger.info(f"  MEV risk level: {bundle_strategy['mev_risk_assessment']['risk_level'].upper()}")
        logger.info(f"  Recommendation:\n    {bundle_strategy['recommendation']}")
        
        # Step 9: Detect MEV attacks
        logger.info("\n[Step 9] Detecting MEV attacks")
        
        # Detect attacks in the last 10 blocks
        attacks = await mev_optimizer.detect_mev_attacks()
        
        if attacks:
            logger.info(f"✓ Detected {len(attacks)} potential MEV attacks")
            for i, attack in enumerate(attacks, 1):
                logger.info(f"  Attack {i}:")
                logger.info(f"    Type: {attack['type']}")
                logger.info(f"    Severity: {attack['severity']}")
                logger.info(f"    Block: {attack['block_number']}")
                logger.info(f"    Details: {attack['details']}")
                logger.info(f"    Confidence: {attack['confidence']:.2f}")
        else:
            logger.info("✓ No MEV attacks detected")
        
        # Step 10: Get MEV attack statistics
        logger.info("\n[Step 10] Getting MEV attack statistics")
        
        stats = await mev_optimizer.get_mev_attack_statistics()
        
        logger.info(f"✓ MEV attack statistics")
        logger.info(f"  Total attacks detected: {stats['total_attacks']}")
        
        if stats['attack_types']:
            logger.info(f"  Attack types:")
            for attack_type, count in stats['attack_types'].items():
                logger.info(f"    {attack_type}: {count}")
        
        logger.info(f"  Current risk level: {stats['risk_level'].upper()}")
        logger.info(f"  Recommendation:\n    {stats['recommendation']}")
        
        # Step 11: Integrate with Flash Loan Manager
        logger.info("\n[Step 11] Integrating with Flash Loan Manager")
        
        # Validate the arbitrage opportunity with flash loan costs
        validation = await flash_loan_manager.validate_arbitrage_opportunity(
            input_token=weth_address,
            output_token=weth_address,  # Circular arbitrage
            input_amount=weth_amount,
            expected_output=weth_amount + web3_manager.w3.to_wei(0.003, 'ether'),  # 0.103 WETH
            route=route
        )
        
        logger.info(f"✓ Flash loan arbitrage validation")
        logger.info(f"  Is profitable: {validation['is_profitable']}")
        if validation['is_profitable']:
            logger.info(f"  Net profit: {web3_manager.w3.from_wei(validation['net_profit'], 'ether'):.6f} WETH")
            logger.info(f"  Profit margin: {validation['profit_margin'] * 100:.2f}%")
        
        # Step 12: Integration with complete workflow
        logger.info("\n[Step 12] Integration with complete workflow")
        logger.info("""
        # In your arbitrage system, integrate MEV protection:
        
        async def execute_protected_arbitrage():
            # 1. Find profitable paths
            paths = await path_finder.find_arbitrage_paths(
                token_in=weth_address,
                token_out=weth_address,
                amount_in=amount_in
            )
            
            for path in paths:
                # 2. Convert path to proper route format
                route = convert_path_to_route(path)
                
                # 3. Validate profitability with flash loan costs
                validation = await flash_loan_manager.validate_arbitrage_opportunity(
                    input_token=path.input_token,
                    output_token=path.output_token,
                    input_amount=path.amount_in,
                    expected_output=path.expected_output,
                    route=route
                )
                
                if validation['is_profitable']:
                    # 4. Create flash loan transaction
                    tx_preparation = await flash_loan_manager.prepare_flash_loan_transaction(
                        token_address=path.input_token,
                        amount=path.amount_in,
                        route=route,
                        min_profit=validation['net_profit']
                    )
                    
                    # 5. Optimize bundle strategy with MEV protection
                    transactions = [tx_preparation['transaction']]
                    
                    bundle_strategy = await mev_optimizer.optimize_bundle_strategy(
                        transactions=transactions,
                        target_token_addresses=[path.input_token, path.output_token],
                        expected_profit=validation['net_profit'],
                        priority_level="high"  # High priority for arbitrage
                    )
                    
                    # 6. Create and simulate bundle with optimized parameters
                    bundle = await create_and_simulate_bundle(
                        web3_manager=web3_manager,
                        transactions=transactions,
                        token_addresses=[path.input_token, path.output_token],
                        gas_settings=bundle_strategy['gas_settings']
                    )
                    
                    if bundle['success']:
                        # 7. Optimize submission with MEV protection
                        submission = await mev_optimizer.optimize_bundle_submission(
                            bundle_id=bundle['bundle_id'],
                            gas_settings=bundle_strategy['gas_settings'],
                            min_profit=validation['net_profit']
                        )
                        
                        if submission['success']:
                            logger.info(f"Protected arbitrage executed successfully!")
                            return submission
        """)
        
        logger.info("=" * 70)
        logger.info("MEV PROTECTION EXAMPLE COMPLETED")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Error in MEV protection example: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    """Run the MEV protection demonstration."""
    asyncio.run(demonstrate_mev_protection())