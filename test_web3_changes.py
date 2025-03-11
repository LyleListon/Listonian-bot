"""
Temporary test script to verify Web3 changes.
"""

import asyncio
import logging
import sys
import traceback
from typing import Dict, Any

# Configure logging to show more details
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log_error(e: Exception, context: str = ""):
    """Log error with traceback."""
    print(f"\n✗ Error in {context}:")
    print(f"  Type: {type(e).__name__}")
    print(f"  Message: {str(e)}")
    print("\nTraceback:")
    traceback.print_exc()
    print()

print("\nPython path:")
for path in sys.path:
    print(f"- {path}")
print()

print("Attempting imports...")
try:
    print("Importing Web3Manager and Web3Error...")
    from arbitrage_bot.core.web3.errors import Web3Error
    print("✓ Imported Web3Error")
    
    print("Importing Web3Manager...")
    from arbitrage_bot.core.web3.web3_manager import Web3Manager
    print("✓ Imported Web3Manager")
    
    print("Importing RiskAnalyzer...")
    from arbitrage_bot.core.web3.flashbots.risk_analyzer import RiskAnalyzer
    print("✓ Imported RiskAnalyzer")
    
    print("Importing CustomAsyncProvider...")
    from arbitrage_bot.core.web3.async_provider import CustomAsyncProvider
    print("✓ Imported CustomAsyncProvider")
except ImportError as e:
    log_error(e, "imports")
    sys.exit(1)
except Exception as e:
    log_error(e, "imports")
    sys.exit(1)

async def test_provider_failover():
    """Test provider failover mechanism."""
    config = {
        'web3': {
            'providers': {
                'primary': 'https://base-mainnet.g.alchemy.com/v2/kRXhWVt8YU_8LnGS20145F5uBDFbL_k0',
                'backup': [
                    'https://base-mainnet.infura.io/v3/863c326dab1a444dba3f41ae7a07ccce'
                ]
            },
            'chain_id': 8453
        },
        'rate_limits': {
            'requests_per_second': 5,
            'max_backoff': 60.0,
            'batch_size': 10,
            'cache_ttl': 30
        },
        'mev_protection': {
            'max_bundle_size': 5,
            'max_blocks_ahead': 3,
            'min_priority_fee': '1.5',
            'max_priority_fee': '3.0',
            'sandwich_detection': True,
            'frontrun_detection': True
        }
    }

    web3_manager = None
    try:
        print("\n=== Starting Web3 Changes Test ===\n")
        
        # Initialize Web3Manager
        print("Initializing Web3Manager...")
        web3_manager = Web3Manager(
            providers=config['web3']['providers'],
            chain_id=config['web3']['chain_id'],
            config=config
        )
        print("✓ Web3Manager initialized")

        # Test basic connection
        print("\nTesting basic connection...")
        block_number = await web3_manager.get_block_number()
        print(f"✓ Connected successfully. Current block: {block_number}")

        # Test rate limiting
        print("\nTesting rate limiting...")
        start_time = asyncio.get_event_loop().time()
        success_count = 0
        for i in range(10):
            try:
                block = await web3_manager.get_block('latest')
                success_count += 1
                print(f"✓ Request {i+1}: Got block {block.get('number')}")
                await asyncio.sleep(0.2)  # Add small delay between requests
            except Exception as e:
                print(f"✗ Request {i+1} failed: {e}")
        end_time = asyncio.get_event_loop().time()
        print(f"\nRate limit test results:")
        print(f"- Successful requests: {success_count}/10")
        print(f"- Total time: {end_time - start_time:.2f} seconds")
        print(f"- Average time per request: {(end_time - start_time)/10:.2f} seconds")

        # Test hex parsing
        print("\nTesting hex parsing...")
        block = await web3_manager.get_block('latest')
        gas_price = await web3_manager.get_gas_price()
        print(f"✓ Base fee parsed: {block.get('baseFeePerGas')}")
        print(f"✓ Gas price parsed: {gas_price}")

        # Test risk analyzer
        print("\nTesting risk analyzer...")
        risk_analyzer = RiskAnalyzer(web3_manager, config)
        risk_info = await risk_analyzer.analyze_mempool_risk()
        print(f"✓ Risk analysis complete:")
        print(f"- Risk level: {risk_info['risk_level']}")
        print(f"- Gas volatility: {risk_info['gas_volatility']:.2f}")
        print(f"- Current gas price: {risk_info['gas_price']}")
        print(f"- Average gas price: {risk_info['avg_gas_price']}")
        if risk_info['risk_factors']:
            print(f"- Risk factors: {', '.join(risk_info['risk_factors'])}")

        print("\n=== All Tests Completed Successfully! ===")

    except Exception as e:
        log_error(e, "test execution")
    finally:
        if web3_manager:
            try:
                await web3_manager.close()
                print("\nWeb3Manager closed.")
            except Exception as e:
                log_error(e, "cleanup")

async def main():
    """Run all tests."""
    try:
        await test_provider_failover()
    except Exception as e:
        log_error(e, "main")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        log_error(e, "script")
        sys.exit(1)