"""Test for the UnifiedBalanceManager."""

import logging
import asyncio
import sys
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

async def test_async_interface():
    """Test the asynchronous interface of the UnifiedBalanceManager."""
    from arbitrage_bot.utils.config_loader import load_config
    from arbitrage_bot.core.web3.web3_manager import create_web3_manager
    from arbitrage_bot.core.unified_balance_manager import create_unified_balance_manager
    
    # Load configuration
    config = load_config()
    
    # Create web3 manager
    web3_manager = await create_web3_manager(config)
    logger.info("Web3Manager initialized with provider %s", config['provider_url'])
    
    # Create a unified balance manager
    logger.info("Creating unified balance manager")
    balance_manager = await create_unified_balance_manager(web3_manager, None, config)
    logger.info("UnifiedBalanceManager instance created successfully")
    
    try:
        # Test balance tracking
        await balance_manager.start()
        logger.info("Balance tracking started")
        
        # Wait for initial balance update
        await asyncio.sleep(1)
        
        # Get ETH balance
        eth_balance = await balance_manager.get_balance('ETH')
        logger.info("ETH balance: %s wei", eth_balance)
        
        # Get formatted ETH balance
        eth_formatted = await balance_manager.get_formatted_balance('ETH')
        logger.info("Formatted ETH balance: %s ETH", eth_formatted)
        
        # Get all balances
        all_balances = await balance_manager.get_all_balances()
        logger.info("All balances: %s", all_balances)
        
        # Test allocation functionality
        # Use WETH address from config
        weth_address = config.get('tokens', {}).get('WETH', {}).get('address')
        if weth_address:
            logger.info("Testing allocation functionality for WETH (%s)", weth_address)
            min_amount, max_amount = await balance_manager.get_allocation_range(weth_address)
            logger.info("Allocation range: %s to %s wei", min_amount, max_amount)
            
            # Test amount adjustment
            test_amount = min_amount // 2  # Test with amount below minimum
            adjusted_amount = await balance_manager.adjust_amount_to_limits(weth_address, test_amount)
            logger.info("Adjusted amount (below min): %s -> %s wei", test_amount, adjusted_amount)
            assert adjusted_amount == min_amount, "Amount should be adjusted to minimum"
            
            test_amount = max_amount * 2  # Test with amount above maximum
            adjusted_amount = await balance_manager.adjust_amount_to_limits(weth_address, test_amount)
            logger.info("Adjusted amount (above max): %s -> %s wei", test_amount, adjusted_amount)
            assert adjusted_amount == max_amount, "Amount should be adjusted to maximum"
            
            test_amount = (min_amount + max_amount) // 2  # Test with amount in range
            adjusted_amount = await balance_manager.adjust_amount_to_limits(weth_address, test_amount)
            logger.info("Adjusted amount (in range): %s -> %s wei", test_amount, adjusted_amount)
            assert adjusted_amount == test_amount, "Amount in range should not be adjusted"
        
        logger.info("Stopping balance tracking")
        await balance_manager.stop()
        logger.info("Balance tracking stopped")
        
        logger.info("Async interface tests passed!")
        return True
    
    except Exception as e:
        logger.error("Error in async interface test: %s", str(e))
        return False

def test_sync_interface():
    """Test the synchronous interface of the UnifiedBalanceManager."""
    from arbitrage_bot.utils.config_loader import load_config
    from arbitrage_bot.core.web3.web3_manager import create_web3_manager_sync
    from arbitrage_bot.core.unified_balance_manager import create_unified_balance_manager_sync
    
    # Load configuration
    config = load_config()
    
    # Create web3 manager
    web3_manager = create_web3_manager_sync(config)
    logger.info("Web3Manager initialized with provider %s", config['provider_url'])
    
    # Create a unified balance manager
    logger.info("Creating unified balance manager (sync)")
    balance_manager = create_unified_balance_manager_sync(web3_manager, None, config)
    logger.info("UnifiedBalanceManager instance created successfully (sync)")
    
    try:
        # Test balance tracking
        balance_manager.start_sync()
        logger.info("Balance tracking started (sync)")
        
        # Wait for initial balance update
        import time
        time.sleep(1)
        
        # Get ETH balance
        eth_balance = balance_manager.get_balance_sync('ETH')
        logger.info("ETH balance: %s wei (sync)", eth_balance)
        
        # Get formatted ETH balance
        eth_formatted = balance_manager.get_formatted_balance_sync('ETH')
        logger.info("Formatted ETH balance: %s ETH (sync)", eth_formatted)
        
        # Get all balances
        all_balances = balance_manager.get_all_balances_sync()
        logger.info("All balances: %s (sync)", all_balances)
        
        # Test allocation functionality
        # Use WETH address from config
        weth_address = config.get('tokens', {}).get('WETH', {}).get('address')
        if weth_address:
            logger.info("Testing allocation functionality for WETH (%s) (sync)", weth_address)
            min_amount, max_amount = balance_manager.get_allocation_range_sync(weth_address)
            logger.info("Allocation range: %s to %s wei (sync)", min_amount, max_amount)
            
            # Test amount adjustment
            test_amount = min_amount // 2  # Test with amount below minimum
            adjusted_amount = balance_manager.adjust_amount_to_limits_sync(weth_address, test_amount)
            logger.info("Adjusted amount (below min): %s -> %s wei (sync)", test_amount, adjusted_amount)
            assert adjusted_amount == min_amount, "Amount should be adjusted to minimum"
            
            test_amount = max_amount * 2  # Test with amount above maximum
            adjusted_amount = balance_manager.adjust_amount_to_limits_sync(weth_address, test_amount)
            logger.info("Adjusted amount (above max): %s -> %s wei (sync)", test_amount, adjusted_amount)
            assert adjusted_amount == max_amount, "Amount should be adjusted to maximum"
            
            test_amount = (min_amount + max_amount) // 2  # Test with amount in range
            adjusted_amount = balance_manager.adjust_amount_to_limits_sync(weth_address, test_amount)
            logger.info("Adjusted amount (in range): %s -> %s wei (sync)", test_amount, adjusted_amount)
            assert adjusted_amount == test_amount, "Amount in range should not be adjusted"
        
        logger.info("Stopping balance tracking (sync)")
        balance_manager.stop_sync()
        logger.info("Balance tracking stopped (sync)")
        
        logger.info("Sync interface tests passed!")
        return True
    
    except Exception as e:
        logger.error("Error in sync interface test: %s", str(e))
        return False

def test_compatibility_wrappers():
    """Test the compatibility wrappers for BalanceManager and BalanceAllocator."""
    from arbitrage_bot.utils.config_loader import load_config
    from arbitrage_bot.core.web3.web3_manager import create_web3_manager_sync
    from arbitrage_bot.core.dex.dex_manager import create_dex_manager_sync
    from arbitrage_bot.core.balance_manager import create_balance_manager
    from arbitrage_bot.core.balance_allocator import create_balance_allocator
    
    # Load configuration
    config = load_config()
    
    # Create web3 manager
    web3_manager = create_web3_manager_sync(config)
    
    # Create dex manager
    dex_manager = create_dex_manager_sync(web3_manager, config)
    
    # Run in event loop for async tests
    loop = asyncio.get_event_loop()
    
    try:
        # Test BalanceManager compatibility
        logger.info("Testing BalanceManager compatibility wrapper")
        balance_manager = loop.run_until_complete(
            create_balance_manager(web3_manager, dex_manager, config)
        )
        logger.info("BalanceManager compatibility wrapper created successfully")
        
        # Start balance tracking
        loop.run_until_complete(balance_manager.start())
        logger.info("Balance tracking started via compatibility wrapper")
        
        # Wait for initial balance update
        loop.run_until_complete(asyncio.sleep(1))
        
        # Get ETH balance
        eth_balance = loop.run_until_complete(balance_manager.get_balance('ETH'))
        logger.info("ETH balance via compatibility wrapper: %s wei", eth_balance)
        
        # Stop balance tracking
        loop.run_until_complete(balance_manager.stop())
        logger.info("Balance tracking stopped via compatibility wrapper")
        
        # Test BalanceAllocator compatibility
        logger.info("Testing BalanceAllocator compatibility wrapper")
        balance_allocator = loop.run_until_complete(
            create_balance_allocator(web3_manager, config)
        )
        logger.info("BalanceAllocator compatibility wrapper created successfully")
        
        # Test allocation range
        weth_address = config.get('tokens', {}).get('WETH', {}).get('address')
        if weth_address:
            logger.info("Testing allocation range via compatibility wrapper for WETH (%s)", weth_address)
            min_amount, max_amount = loop.run_until_complete(
                balance_allocator.get_allocation_range(weth_address)
            )
            logger.info("Allocation range via compatibility wrapper: %s to %s wei", min_amount, max_amount)
            
            # Test amount adjustment
            test_amount = min_amount // 2
            adjusted_amount = loop.run_until_complete(
                balance_allocator.adjust_amount_to_limits(weth_address, test_amount)
            )
            logger.info("Adjusted amount via compatibility wrapper: %s -> %s wei", test_amount, adjusted_amount)
            
        logger.info("Compatibility wrapper tests passed!")
        return True
    
    except Exception as e:
        logger.error("Error in compatibility wrapper tests: %s", str(e))
        return False

async def main():
    """Run all tests."""
    logger.info("Starting UnifiedBalanceManager tests")
    
    # Test async interface
    logger.info("Testing asynchronous interface...")
    async_result = await test_async_interface()
    
    # Test sync interface
    logger.info("Testing synchronous interface...")
    sync_result = test_sync_interface()
    
    # Test compatibility wrappers
    logger.info("Testing compatibility wrappers...")
    compat_result = test_compatibility_wrappers()
    
    # Check overall result
    if async_result and sync_result and compat_result:
        logger.info("All tests completed successfully!")
    else:
        logger.error("Some tests failed!")

if __name__ == "__main__":
    asyncio.run(main())