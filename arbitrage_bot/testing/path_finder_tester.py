"""Production testing framework for path finding algorithms."""

import asyncio
import logging
import time
import json
import os
import csv
from typing import Dict, List, Any, Optional, Tuple, Set
from decimal import Decimal
from web3 import Web3

from ..core.web3.web3_manager import Web3Manager
from ..core.dex.dex_manager import DexManager
from ..core.path_finder import PathFinder
from ..core.gas.gas_optimizer import GasOptimizer
from ..utils.config_loader import load_config

logger = logging.getLogger(__name__)

class PathFinderTester:
    """
    Testing framework for path finding algorithms in production.
    
    Provides functionality to test path finding effectiveness, measure performance,
    and validate gas estimations on production networks.
    """
    
    def __init__(
        self,
        web3_manager: Optional[Web3Manager] = None,
        dex_manager: Optional[DexManager] = None,
        config: Optional[Dict[str, Any]] = None,
        output_dir: str = "data/tests"
    ):
        """
        Initialize the path finder tester.
        
        Args:
            web3_manager: Web3Manager instance (optional)
            dex_manager: DexManager instance (optional)
            config: Configuration dictionary (optional)
            output_dir: Directory for test results
        """
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.config = config or load_config()
        self.output_dir = output_dir
        self.path_finder = None
        self.gas_optimizer = None
        
        # Test configuration
        self.test_config = self.config.get('path_finder_test', {})
        self.test_tokens = self.test_config.get('test_tokens', [])
        self.batch_size = self.test_config.get('batch_size', 5)
        self.max_test_paths = self.test_config.get('max_test_paths', 20)
        self.min_token_liquidity = self.test_config.get('min_token_liquidity', 1000)
        self.test_amounts = self.test_config.get('test_amounts', [
            0.1,  # 0.1 ETH
            1.0,  # 1 ETH
            5.0   # 5 ETH
        ])
        
        # Performance metrics
        self.execution_times = []
        self.success_rates = []
        self.gas_estimation_accuracy = []
        
        # Test results
        self.test_results = []
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("Path finder tester initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the tester with required components.
        
        Returns:
            True if initialization succeeded
        """
        try:
            # Initialize Web3Manager if not provided
            if not self.web3_manager:
                # Import here to avoid circular imports
                from ..core.web3.web3_manager import create_web3_manager
                self.web3_manager = await create_web3_manager(self.config)
            
            # Initialize DexManager if not provided
            if not self.dex_manager:
                self.dex_manager = await DexManager(self.web3_manager, self.config).initialize()
            
            # Initialize GasOptimizer
            self.gas_optimizer = await GasOptimizer.create_gas_optimizer(
                self.web3_manager,
                self.config
            )
            
            # Add gas optimizer to web3_manager for DEX access
            self.web3_manager.gas_optimizer = self.gas_optimizer
            
            # Initialize PathFinder
            from ..core.path_finder import create_path_finder
            self.path_finder = await create_path_finder(
                self.web3_manager,
                self.dex_manager,
                self.config
            )
            
            logger.info("Path finder tester initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize path finder tester: {e}")
            return False
    
    async def discover_test_tokens(self) -> List[str]:
        """
        Discover tokens with sufficient liquidity for testing.
        
        Returns:
            List of token addresses
        """
        try:
            # If test tokens are explicitly defined, use those
            if self.test_tokens:
                logger.info(f"Using {len(self.test_tokens)} predefined test tokens")
                return self.test_tokens
            
            # Otherwise, discover tokens with sufficient liquidity
            discovered_tokens = []
            
            # Get common tokens from all DEXes
            for dex_name, dex in self.dex_manager.dex_instances.items():
                try:
                    if hasattr(dex, 'get_supported_tokens'):
                        tokens = await dex.get_supported_tokens()
                        for token in tokens:
                            if token not in discovered_tokens:
                                # Check if token has sufficient liquidity
                                has_liquidity = False
                                
                                for check_dex in self.dex_manager.dex_instances.values():
                                    if token.lower() == check_dex.weth_address.lower():
                                        # WETH always has liquidity
                                        has_liquidity = True
                                        break
                                        
                                    try:
                                        if hasattr(check_dex, '_get_pool_liquidity_by_tokens'):
                                            liquidity = await check_dex._get_pool_liquidity_by_tokens(
                                                token,
                                                check_dex.weth_address
                                            )
                                            if liquidity > self.min_token_liquidity:
                                                has_liquidity = True
                                                break
                                    except Exception as e:
                                        logger.debug(f"Error checking liquidity for {token}: {e}")
                                
                                if has_liquidity:
                                    discovered_tokens.append(token)
                                    if len(discovered_tokens) >= 10:  # Limit discovery to 10 tokens
                                        break
                except Exception as e:
                    logger.warning(f"Error discovering tokens from {dex_name}: {e}")
            
            # If we found tokens, use them
            if discovered_tokens:
                logger.info(f"Discovered {len(discovered_tokens)} tokens with sufficient liquidity")
                return discovered_tokens
            
            # Fallback to common tokens
            logger.warning("Could not discover tokens with sufficient liquidity, using fallback tokens")
            return [
                self.config.get('tokens', {}).get('WETH', {}).get('address'),  # WETH
                self.config.get('tokens', {}).get('USDC', {}).get('address'),  # USDC
                self.config.get('tokens', {}).get('USDT', {}).get('address'),  # USDT
                self.config.get('tokens', {}).get('DAI', {}).get('address')    # DAI
            ]
            
        except Exception as e:
            logger.error(f"Error discovering test tokens: {e}")
            return []
    
    async def generate_test_cases(self) -> List[Dict[str, Any]]:
        """
        Generate test cases for path finding.
        
        Returns:
            List of test case dictionaries
        """
        try:
            # Discover test tokens
            test_tokens = await self.discover_test_tokens()
            if not test_tokens:
                logger.error("No test tokens available")
                return []
            
            test_cases = []
            
            # Generate test cases for all token pairs
            for i, token_in in enumerate(test_tokens):
                for j, token_out in enumerate(test_tokens):
                    # Skip same token
                    if i == j:
                        continue
                    
                    # Skip if tokens aren't valid addresses
                    try:
                        Web3.to_checksum_address(token_in)
                        Web3.to_checksum_address(token_out)
                    except:
                        continue
                    
                    # Generate test cases with different amounts
                    for amount in self.test_amounts:
                        amount_wei = Web3.to_wei(amount, 'ether')
                        test_cases.append({
                            'token_in': token_in,
                            'token_out': token_out,
                            'amount_in': amount_wei,
                            'description': f"{amount} ETH {token_in[-6:]}→{token_out[-6:]}"
                        })
            
            # Shuffle and limit test cases
            import random
            random.shuffle(test_cases)
            test_cases = test_cases[:self.max_test_paths]
            
            logger.info(f"Generated {len(test_cases)} test cases")
            return test_cases
            
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return []
    
    async def run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single test case.
        
        Args:
            test_case: Test case dictionary
            
        Returns:
            Test results dictionary
        """
        try:
            token_in = test_case['token_in']
            token_out = test_case['token_out']
            amount_in = test_case['amount_in']
            description = test_case['description']
            
            logger.info(f"Testing path: {description}")
            
            # Record start time
            start_time = time.time()
            
            # Find paths
            paths = await self.path_finder.find_arbitrage_paths(
                token_in,
                token_out,
                amount_in
            )
            
            # Record execution time
            execution_time = time.time() - start_time
            self.execution_times.append(execution_time)
            
            # Check if any paths were found
            success = len(paths) > 0
            
            # Record success/failure
            self.success_rates.append(1 if success else 0)
            
            # Create result dictionary
            result = {
                'token_in': token_in,
                'token_out': token_out,
                'amount_in': amount_in,
                'description': description,
                'execution_time': execution_time,
                'success': success,
                'paths_found': len(paths),
                'timestamp': time.time()
            }
            
            # If paths were found, analyze the best path
            if paths:
                best_path = paths[0]  # Paths are sorted by profitability
                
                # Get gas estimate from path finder
                estimated_gas = best_path.gas_estimate
                
                # Get path details
                result['best_path'] = {
                    'tokens': best_path.tokens,
                    'dexes': best_path.dexes,
                    'expected_output': best_path.output_amount,
                    'profit_estimate': best_path.profit,
                    'gas_estimate': estimated_gas,
                    'profitability_score': best_path.profitability_score
                }
                
                # Analyze gas estimation accuracy
                try:
                    # Calculate gas by individual hops
                    hop_gas = 0
                    for i in range(len(best_path.dexes)):
                        dex = self.dex_manager.get_dex(best_path.dexes[i])
                        hop_tokens = best_path.tokens[i:i+2]
                        if len(hop_tokens) == 2:
                            if hasattr(dex, 'estimate_gas'):
                                hop_gas += await dex.estimate_gas(hop_tokens[0], hop_tokens[1])
                            else:
                                hop_gas += 150000  # Default estimate
                    
                    # Compare with path finder's estimate
                    gas_accuracy = abs(estimated_gas - hop_gas) / max(estimated_gas, hop_gas)
                    gas_accuracy = 1.0 - min(gas_accuracy, 1.0)  # Convert to accuracy percentage
                    
                    result['best_path']['gas_accuracy'] = gas_accuracy
                    self.gas_estimation_accuracy.append(gas_accuracy)
                    
                except Exception as e:
                    logger.warning(f"Error analyzing gas estimation: {e}")
            
            logger.info(f"Test case {description} completed: {'success' if success else 'no paths found'}")
            return result
            
        except Exception as e:
            logger.error(f"Error running test case: {e}")
            return {
                'token_in': test_case.get('token_in', ''),
                'token_out': test_case.get('token_out', ''),
                'amount_in': test_case.get('amount_in', 0),
                'description': test_case.get('description', ''),
                'execution_time': 0,
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def run_test_batch(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run a batch of test cases.
        
        Args:
            test_cases: List of test case dictionaries
            
        Returns:
            List of test results
        """
        results = []
        
        # Run test cases in batches
        for i in range(0, len(test_cases), self.batch_size):
            batch = test_cases[i:i+self.batch_size]
            batch_results = await asyncio.gather(*[self.run_test_case(case) for case in batch])
            results.extend(batch_results)
            
            # Allow some time between batches to avoid rate limiting
            if i + self.batch_size < len(test_cases):
                await asyncio.sleep(2)
        
        return results
    
    async def run_tests(self) -> Dict[str, Any]:
        """
        Run the full test suite.
        
        Returns:
            Test summary dictionary
        """
        try:
            # Generate test cases
            test_cases = await self.generate_test_cases()
            if not test_cases:
                return {'error': 'No test cases could be generated'}
            
            # Reset metrics
            self.execution_times = []
            self.success_rates = []
            self.gas_estimation_accuracy = []
            self.test_results = []
            
            # Run tests
            logger.info(f"Running {len(test_cases)} test cases")
            start_time = time.time()
            self.test_results = await self.run_test_batch(test_cases)
            total_time = time.time() - start_time
            
            # Calculate metrics
            avg_execution_time = sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0
            success_rate = sum(self.success_rates) / len(self.success_rates) if self.success_rates else 0
            avg_gas_accuracy = sum(self.gas_estimation_accuracy) / len(self.gas_estimation_accuracy) if self.gas_estimation_accuracy else 0
            
            # Create summary
            summary = {
                'test_count': len(test_cases),
                'success_count': sum(self.success_rates),
                'failure_count': len(self.success_rates) - sum(self.success_rates),
                'success_rate': success_rate,
                'avg_execution_time': avg_execution_time,
                'total_time': total_time,
                'avg_gas_accuracy': avg_gas_accuracy,
                'timestamp': time.time(),
                'network': self.config.get('network', 'mainnet')
            }
            
            # Save results
            await self.save_results(summary)
            
            logger.info(f"Tests completed: {summary['success_count']}/{summary['test_count']} successful ({summary['success_rate']*100:.1f}%)")
            return summary
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return {'error': str(e)}
    
    async def save_results(self, summary: Dict[str, Any]) -> None:
        """
        Save test results to files.
        
        Args:
            summary: Test summary dictionary
        """
        try:
            # Create timestamp for filenames
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # Save detailed results to JSON
            json_path = os.path.join(self.output_dir, f"path_test_{timestamp}.json")
            with open(json_path, 'w') as f:
                json.dump({
                    'summary': summary,
                    'results': self.test_results
                }, f, indent=2)
            
            # Save summary to CSV
            csv_path = os.path.join(self.output_dir, "path_test_summary.csv")
            csv_exists = os.path.exists(csv_path)
            
            with open(csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                
                # Write header if file doesn't exist
                if not csv_exists:
                    writer.writerow([
                        'timestamp',
                        'network',
                        'test_count',
                        'success_count',
                        'success_rate',
                        'avg_execution_time',
                        'total_time',
                        'avg_gas_accuracy'
                    ])
                
                # Write summary row
                writer.writerow([
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    summary.get('network', 'unknown'),
                    summary.get('test_count', 0),
                    summary.get('success_count', 0),
                    summary.get('success_rate', 0),
                    summary.get('avg_execution_time', 0),
                    summary.get('total_time', 0),
                    summary.get('avg_gas_accuracy', 0)
                ])
            
            logger.info(f"Test results saved to {json_path} and {csv_path}")
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")


async def run_path_finder_tests():
    """Run path finder tests from command line."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Path Finder Testing Framework')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--output-dir', type=str, default='data/tests', help='Output directory for test results')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size for test execution')
    parser.add_argument('--max-tests', type=int, default=20, help='Maximum number of test cases to run')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load config
    config = None
    if args.config:
        from ..utils.config_loader import load_config_from_file
        config = load_config_from_file(args.config)
    else:
        from ..utils.config_loader import load_config
        config = load_config()
    
    # Update config with command line options
    if not config.get('path_finder_test'):
        config['path_finder_test'] = {}
    config['path_finder_test']['batch_size'] = args.batch_size
    config['path_finder_test']['max_test_paths'] = args.max_tests
    
    # Create and initialize tester
    tester = PathFinderTester(
        config=config,
        output_dir=args.output_dir
    )
    if not await tester.initialize():
        logger.error("Failed to initialize path finder tester")
        return
    
    # Run tests
    summary = await tester.run_tests()
    
    # Print summary
    if 'error' in summary:
        logger.error(f"Tests failed: {summary['error']}")
    else:
        logger.info(f"Tests completed successfully:")
        logger.info(f"  Success rate: {summary['success_rate']*100:.1f}%")
        logger.info(f"  Average execution time: {summary['avg_execution_time']*1000:.1f}ms")
        logger.info(f"  Gas estimation accuracy: {summary['avg_gas_accuracy']*100:.1f}%")


if __name__ == "__main__":
    asyncio.run(run_path_finder_tests())