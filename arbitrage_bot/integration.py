"""Integration utilities for new components.

This module provides helper functions to integrate the new Gas Optimizer, 
Enhanced Multi-Hop Paths, and Testing Framework into the existing system.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

# Import core components
from .core.web3.web3_manager import Web3Manager
from .core.dex.dex_manager import DexManager
from .core.gas.gas_optimizer import GasOptimizer
from .core.path_finder import PathFinder

logger = logging.getLogger(__name__)

async def setup_gas_optimizer(
    web3_manager: Web3Manager,
    config: Dict[str, Any]
) -> GasOptimizer:
    """
    Set up and integrate the Gas Optimizer with Web3Manager.
    
    Args:
        web3_manager: Web3Manager instance
        config: Configuration dictionary
        
    Returns:
        Initialized GasOptimizer instance
    """
    try:
        # Create gas optimizer
        gas_optimizer = await GasOptimizer.create_gas_optimizer(
            web3_manager=web3_manager,
            config=config
        )
        
        # Attach to web3_manager for global access
        web3_manager.gas_optimizer = gas_optimizer
        
        logger.info("Gas Optimizer integrated with Web3Manager")
        return gas_optimizer
    
    except Exception as e:
        logger.error(f"Failed to set up Gas Optimizer: {e}")
        raise

async def use_enhanced_multi_hop(
    dex_manager: DexManager
) -> bool:
    """
    Configure DEX instances to use enhanced multi-hop implementation.
    
    Args:
        dex_manager: DexManager instance
        
    Returns:
        True if successful
    """
    try:
        # Import the enhanced BaseDEXV3 implementation
        from .core.dex.base_dex_v3_enhanced import BaseDEXV3
        
        # Count of DEXs updated
        updated_count = 0
        
        # Replace base class for each V3 DEX instance
        for dex_name, dex in dex_manager.dex_instances.items():
            # Check if it's a V3 DEX
            if dex.__class__.__name__.endswith('V3') or 'V3' in dex.__class__.__name__:
                try:
                    # Save original attributes that we'll need to preserve
                    original_attrs = {
                        'name': dex.name,
                        'web3_manager': dex.web3_manager,
                        'config': dex.config,
                        'router_address': dex.router_address,
                        'factory_address': dex.factory_address,
                        'weth_address': dex.weth_address,
                        'initialized': dex.initialized
                    }
                    
                    # Create new instance with enhanced base class
                    # This is a hack to change the base class, but we're not actually
                    # recreating the instance - just injecting new methods
                    dex.__class__.__bases__ = (BaseDEXV3,)
                    
                    # Re-initialize if necessary
                    if not hasattr(dex, 'supported_fees'):
                        dex.supported_fees = dex.config.get('supported_fees', [500, 3000, 10000])
                        dex.fee_tier_names = {
                            100: "0.01%",
                            500: "0.05%",
                            3000: "0.3%",
                            10000: "1%"
                        }
                        dex._pool_existence_cache = {}
                    
                    updated_count += 1
                    logger.info(f"Enhanced {dex_name} with improved multi-hop support")
                    
                except Exception as e:
                    logger.error(f"Failed to enhance {dex_name}: {e}")
        
        logger.info(f"Enhanced {updated_count} DEX instances with improved multi-hop support")
        return updated_count > 0
    
    except Exception as e:
        logger.error(f"Failed to set up enhanced multi-hop: {e}")
        return False

async def setup_optimized_system(
    web3_manager: Optional[Web3Manager] = None,
    dex_manager: Optional[DexManager] = None,
    config: Optional[Dict[str, Any]] = None,
    path_finder: Optional[PathFinder] = None
) -> Dict[str, Any]:
    """
    Set up a fully optimized system with all enhancements.
    
    Args:
        web3_manager: Web3Manager instance (optional)
        dex_manager: DexManager instance (optional)
        config: Configuration dictionary (optional)
        path_finder: PathFinder instance (optional)
        
    Returns:
        Dictionary with initialized components
    """
    try:
        # Import components as needed
        if config is None:
            from .utils.config_loader import load_config
            config = load_config()
        
        if web3_manager is None:
            from .core.web3.web3_manager import create_web3_manager
            web3_manager = await create_web3_manager(config)
        
        if dex_manager is None:
            dex_manager = await DexManager(web3_manager, config).initialize()
        
        # Setup gas optimizer
        gas_optimizer = await setup_gas_optimizer(web3_manager, config)
        
        # Enhance DEXs with multi-hop support
        await use_enhanced_multi_hop(dex_manager)
        
        # Set up path finder if needed
        if path_finder is None:
            from .core.path_finder import create_path_finder
            path_finder = await create_path_finder(
                web3_manager=web3_manager,
                dex_manager=dex_manager,
                config=config
            )
        
        # Return the optimized components
        return {
            'web3_manager': web3_manager,
            'dex_manager': dex_manager,
            'gas_optimizer': gas_optimizer,
            'path_finder': path_finder,
            'config': config
        }
    
    except Exception as e:
        logger.error(f"Failed to set up optimized system: {e}")
        raise

async def run_optimization_test(
    components: Optional[Dict[str, Any]] = None,
    test_token_pairs: Optional[List[Dict[str, str]]] = None,
    count: int = 5
) -> Dict[str, Any]:
    """
    Run a quick test of the optimization features.
    
    Args:
        components: Dictionary of system components (optional)
        test_token_pairs: List of token pairs to test (optional)
        count: Number of tests to run
        
    Returns:
        Test results dictionary
    """
    try:
        # Set up components if not provided
        if components is None:
            components = await setup_optimized_system()
        
        web3_manager = components['web3_manager']
        dex_manager = components['dex_manager']
        path_finder = components['path_finder']
        config = components['config']
        
        # Default test token pairs if not provided
        if test_token_pairs is None:
            # Use WETH and other common tokens
            weth_address = config.get('tokens', {}).get('WETH', {}).get('address')
            usdc_address = config.get('tokens', {}).get('USDC', {}).get('address', '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
            usdt_address = config.get('tokens', {}).get('USDT', {}).get('address', '0x4D15a3a2286D883AF0AA1B3f21367843FAc63E07')
            dai_address = config.get('tokens', {}).get('DAI', {}).get('address', '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb')
            
            test_token_pairs = [
                {'token_in': weth_address, 'token_out': usdc_address},
                {'token_in': usdc_address, 'token_out': weth_address},
                {'token_in': weth_address, 'token_out': usdt_address},
                {'token_in': weth_address, 'token_out': dai_address},
                {'token_in': usdc_address, 'token_out': usdt_address}
            ]
        
        # Limit to requested count
        test_token_pairs = test_token_pairs[:count]
        
        results = []
        
        # Run tests
        logger.info(f"Running {len(test_token_pairs)} optimization tests")
        
        for pair in test_token_pairs:
            token_in = pair['token_in']
            token_out = pair['token_out']
            
            # Use 0.1 ETH for test amount
            amount_in = web3_manager.w3.to_wei(0.1, 'ether')
            
            # Find paths
            start_time = asyncio.get_event_loop().time()
            paths = await path_finder.find_arbitrage_paths(
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in
            )
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Record results
            pair_result = {
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': amount_in,
                'execution_time': execution_time,
                'paths_found': len(paths),
                'best_path': None
            }
            
            # Add best path details if available
            if paths:
                best_path = paths[0]
                
                # Get gas estimate
                gas_estimate = best_path.gas_estimate
                
                pair_result['best_path'] = {
                    'tokens': best_path.tokens,
                    'dexes': best_path.dexes,
                    'expected_output': best_path.output_amount,
                    'gas_estimate': gas_estimate,
                    'hop_count': len(best_path.tokens) - 1
                }
            
            results.append(pair_result)
            logger.info(f"Test {token_in[-6:]} → {token_out[-6:]} completed in {execution_time:.3f}s - Paths found: {len(paths)}")
        
        # Calculate summary statistics
        success_count = sum(1 for r in results if r.get('paths_found', 0) > 0)
        avg_execution_time = sum(r['execution_time'] for r in results) / len(results) if results else 0
        multi_hop_count = sum(1 for r in results if r.get('best_path') and len(r.get('best_path', {}).get('tokens', [])) > 2)
        
        summary = {
            'test_count': len(results),
            'success_count': success_count,
            'success_rate': success_count / len(results) if results else 0,
            'avg_execution_time': avg_execution_time,
            'multi_hop_paths': multi_hop_count,
            'results': results
        }
        
        logger.info(f"Optimization test completed: {success_count}/{len(results)} successful")
        return summary
    
    except Exception as e:
        logger.error(f"Error running optimization test: {e}")
        return {'error': str(e)}


# Command-line script for integration
async def main():
    """Run integration as command-line script."""
    import argparse
    from pathlib import Path
    import json
    
    # Parse command line args
    parser = argparse.ArgumentParser(description='Integrate optimization components')
    parser.add_argument('--test', action='store_true', help='Run a quick test after integration')
    parser.add_argument('--count', type=int, default=5, help='Number of test pairs to run')
    parser.add_argument('--output', type=str, help='Save test results to file')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up optimized system
    logger.info("Setting up optimized system")
    components = await setup_optimized_system()
    logger.info("System optimization complete")
    
    # Run test if requested
    if args.test:
        logger.info(f"Running integration test with {args.count} token pairs")
        results = await run_optimization_test(components, count=args.count)
        
        # Print summary
        print("\nTest Results:")
        print(f"Success rate: {results['success_rate']*100:.1f}%")
        print(f"Avg execution time: {results['avg_execution_time']*1000:.1f}ms")
        print(f"Multi-hop paths found: {results['multi_hop_paths']}")
        
        # Save results if output path provided
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Test results saved to {output_path}")
    
    logger.info("Integration completed successfully")
    return 0


if __name__ == "__main__":
    asyncio.run(main())