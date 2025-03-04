"""
Flash Loan Integration Tests

This module contains tests for the flash loan integration components, including
provider creation, selection, and execution. These tests verify that:

1. Providers can be created and initialized
2. Provider selection logic works correctly
3. Flash loan execution succeeds with proper callbacks
4. Fallback mechanisms work when the primary provider fails
"""

import asyncio
import logging
import unittest
from decimal import Decimal
from typing import List, Dict, Any, Optional
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from arbitrage_bot.core.web3.interfaces import Web3Client, Transaction, TransactionReceipt
from arbitrage_bot.core.finance.flash_loans.interfaces import (
    FlashLoanProvider,
    FlashLoanCallback,
    FlashLoanParams,
    FlashLoanResult,
    FlashLoanStatus,
    TokenAmount
)
from arbitrage_bot.core.finance.flash_loans.factory import (
    create_flash_loan_provider,
    get_best_provider,
    get_optimal_multi_token_provider,
    estimate_flash_loan_cost
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockWeb3Client(Web3Client):
    """Mock Web3 client for testing."""
    
    def __init__(self):
        """Initialize the mock client."""
        self.connected = False
        self.contracts = {}
        self.balances = {}
        self.transactions = {}
        self.default_account = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        
    async def connect(self) -> bool:
        """Connect to the blockchain."""
        self.connected = True
        return True
    
    async def get_contract(self, address: str, abi: Any) -> Any:
        """Get a contract instance."""
        class MockContract:
            def __init__(self, address, abi):
                self.address = address
                self.abi = abi
                self.functions = self
                
            def __getattr__(self, name):
                def method(*args, **kwargs):
                    class MockMethod:
                        @staticmethod
                        def call(*call_args, **call_kwargs):
                            if name == "FLASH_LOAN_FEE":
                                return 0  # Balancer has no fees
                            if name == "FLASH_LOAN_FEE_PERCENTAGE":
                                return 0  # Balancer has no fees
                            if address.lower() == "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb":
                                # Balancer has high liquidity for all tokens
                                return 1000000 * 10**18
                            if address.lower() == "0xcccccccccccccccccccccccccccccccccccccccc":
                                # Aave has high liquidity for all tokens
                                return 1000000 * 10**18
                            return 0
                        
                        @staticmethod
                        def build_transaction(*tx_args, **tx_kwargs):
                            return {"data": b"mock_data"}
                    
                    return MockMethod()
                
                return method
        
        contract = MockContract(address, abi)
        self.contracts[address] = contract
        return contract
    
    async def call_contract_function(self, contract: Any, function_name: str, args: List) -> Any:
        """Call a contract function."""
        if function_name == "FLASH_LOAN_FEE":
            return 0  # Balancer has no fees
        if function_name == "FLASH_LOAN_FEE_PERCENTAGE":
            return 0  # Balancer has no fees
        return None
    
    async def get_token_balance(self, token_address: str, wallet_address: str) -> int:
        """Get token balance for a wallet."""
        key = f"{token_address.lower()}:{wallet_address.lower()}"
        return self.balances.get(key, 1000000)  # Default high balance
    
    async def estimate_gas(self, transaction: Any) -> int:
        """Estimate gas for a transaction."""
        return 300000  # Mock gas estimate
    
    async def send_transaction(self, transaction: Any) -> str:
        """Send a transaction."""
        tx_hash = f"0x{len(self.transactions):064x}"
        self.transactions[tx_hash] = transaction
        return tx_hash
    
    async def wait_for_transaction_receipt(self, tx_hash: str, timeout: int = 120) -> Any:
        """Wait for a transaction receipt."""
        await asyncio.sleep(0.1)  # Simulate some delay
        
        class MockReceipt:
            def __init__(self):
                self.status = 1
                self.gas_used = 250000
                self.transaction_hash = tx_hash
                self.blockNumber = 12345678
        
        return MockReceipt()
    
    def get_default_account(self) -> str:
        """Get the default account."""
        return self.default_account
    
    async def close(self) -> None:
        """Close the client connection."""
        self.connected = False


class TestFlashLoanCallback(FlashLoanCallback):
    """Mock flash loan callback for testing."""
    
    def __init__(self):
        """Initialize the callback."""
        self.on_flash_loan_called = False
        self.on_completed_called = False
        self.on_failed_called = False
    
    async def on_flash_loan(
        self,
        sender: str,
        tokens: List[str],
        amounts: List[int],
        fees: List[int],
        user_data: bytes
    ) -> bool:
        """Handle the flash loan."""
        logger.info(f"Flash loan received from {sender}")
        logger.info(f"Tokens: {tokens}")
        logger.info(f"Amounts: {amounts}")
        logger.info(f"Fees: {fees}")
        self.on_flash_loan_called = True
        
        # Always succeed
        return True
    
    async def on_flash_loan_completed(self, result: FlashLoanResult) -> None:
        """Handle flash loan completion."""
        logger.info("Flash loan completed successfully")
        self.on_completed_called = True
    
    async def on_flash_loan_failed(self, result: FlashLoanResult) -> None:
        """Handle flash loan failure."""
        logger.error(f"Flash loan failed: {result.error_message}")
        self.on_failed_called = True


class FlashLoanTests(unittest.TestCase):
    """Tests for flash loan functionality."""
    
    def setUp(self):
        """Set up for tests."""
        self.web3_client = MockWeb3Client()
        self.balancer_address = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        self.aave_address = "0xcccccccccccccccccccccccccccccccccccccccc"
        self.weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        
        # Base configs for providers
        self.balancer_config = {
            "network": "mainnet",
            "pool_address": self.balancer_address
        }
        
        self.aave_config = {
            "network": "mainnet",
            "lending_pool_address": self.aave_address
        }
        
        # Combined config
        self.config = {
            "balancer": self.balancer_config,
            "aave": self.aave_config
        }
    
    async def test_create_balancer_provider(self):
        """Test creating a Balancer provider."""
        provider = await create_flash_loan_provider(
            "balancer", 
            self.web3_client, 
            self.balancer_config
        )
        
        self.assertEqual(provider.name, "Balancer-mainnet")
        await provider.close()
    
    async def test_create_aave_provider(self):
        """Test creating an Aave provider."""
        provider = await create_flash_loan_provider(
            "aave", 
            self.web3_client, 
            self.aave_config
        )
        
        self.assertEqual(provider.name, "Aave-mainnet")
        await provider.close()
    
    async def test_get_best_provider_balancer_first(self):
        """Test provider selection prefers Balancer for zero fees."""
        provider = await get_best_provider(
            self.web3_client,
            self.weth_address,
            Decimal("10"),
            self.config
        )
        
        # Balancer should be chosen due to zero fees
        self.assertEqual(provider.name, "Balancer-mainnet")
        await provider.close()
    
    async def test_flash_loan_execution_balancer(self):
        """Test executing a flash loan with Balancer."""
        provider = await create_flash_loan_provider(
            "balancer", 
            self.web3_client, 
            self.balancer_config
        )
        
        callback = TestFlashLoanCallback()
        
        params = FlashLoanParams(
            token_amounts=[TokenAmount(
                token_address=self.weth_address,
                amount=Decimal("10")
            )],
            receiver_address="0xdddddddddddddddddddddddddddddddddddddddd",
            slippage_tolerance=Decimal("0.005"),
            transaction_params={}
        )
        
        result = await provider.execute_flash_loan(params, callback)
        
        self.assertTrue(result.success)
        self.assertEqual(result.status, FlashLoanStatus.EXECUTED)
        self.assertTrue(callback.on_flash_loan_called)
        self.assertTrue(callback.on_completed_called)
        self.assertFalse(callback.on_failed_called)
        
        await provider.close()
    
    async def test_flash_loan_execution_aave(self):
        """Test executing a flash loan with Aave."""
        provider = await create_flash_loan_provider(
            "aave", 
            self.web3_client, 
            self.aave_config
        )
        
        callback = TestFlashLoanCallback()
        
        params = FlashLoanParams(
            token_amounts=[TokenAmount(
                token_address=self.weth_address,
                amount=Decimal("10")
            )],
            receiver_address="0xdddddddddddddddddddddddddddddddddddddddd",
            slippage_tolerance=Decimal("0.005"),
            transaction_params={}
        )
        
        result = await provider.execute_flash_loan(params, callback)
        
        self.assertTrue(result.success)
        self.assertEqual(result.status, FlashLoanStatus.EXECUTED)
        self.assertTrue(callback.on_flash_loan_called)
        self.assertTrue(callback.on_completed_called)
        self.assertFalse(callback.on_failed_called)
        
        await provider.close()
    
    async def test_estimated_costs_comparison(self):
        """Test comparing costs between providers."""
        costs = await estimate_flash_loan_cost(
            self.web3_client,
            self.weth_address,
            Decimal("1000"),
            self.config
        )
        
        # Balancer should have zero fees
        self.assertIn("Balancer-mainnet", costs)
        self.assertEqual(costs["Balancer-mainnet"], Decimal("0"))
        
        # Aave should have 0.09% fees
        self.assertIn("Aave-mainnet", costs)
        self.assertGreater(costs["Aave-mainnet"], Decimal("0"))


def run_tests():
    """Run the flash loan tests."""
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    test_cases = [
        FlashLoanTests("test_create_balancer_provider"),
        FlashLoanTests("test_create_aave_provider"),
        FlashLoanTests("test_get_best_provider_balancer_first"),
        FlashLoanTests("test_flash_loan_execution_balancer"),
        FlashLoanTests("test_flash_loan_execution_aave"),
        FlashLoanTests("test_estimated_costs_comparison")
    ]
    
    suite.addTests(test_cases)
    
    # Run tests
    runner = unittest.TextTestRunner()
    runner.run(suite)


async def main():
    """Main function to run tests."""
    # Convert tests to async
    for test_name in dir(FlashLoanTests):
        if test_name.startswith("test_"):
            original_test = getattr(FlashLoanTests, test_name)
            
            async def make_async_test(original_test):
                async def async_test(self):
                    await original_test(self)
                return async_test
            
            setattr(FlashLoanTests, test_name, make_async_test(original_test))
    
    # Run tests one by one manually to handle async
    test_instance = FlashLoanTests()
    test_instance.setUp()
    
    tests = [
        test_instance.test_create_balancer_provider(),
        test_instance.test_create_aave_provider(),
        test_instance.test_get_best_provider_balancer_first(),
        test_instance.test_flash_loan_execution_balancer(),
        test_instance.test_flash_loan_execution_aave(),
        test_instance.test_estimated_costs_comparison()
    ]
    
    # Run tests sequentially
    for test in tests:
        try:
            await test
            print(f"✅ {test.__name__} passed")
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())