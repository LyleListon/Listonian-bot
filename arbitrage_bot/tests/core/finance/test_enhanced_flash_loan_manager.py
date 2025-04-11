"""
Unit tests for the EnhancedFlashLoanManager.
"""

import pytest
import pytest_asyncio # Import pytest_asyncio
import asyncio
import time # Import time for timestamp
import time # Import time for timestamp
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

# Corrected import path
from arbitrage_bot.core.enhanced_flash_loan_manager import EnhancedFlashLoanManager, FlashLoanRoute, RouteSegment
from arbitrage_bot.core.finance.flash_loans.interfaces import TokenAmount, FlashLoanParams, FlashLoanCallback, FlashLoanResult, FlashLoanStatus
from arbitrage_bot.core.web3.flashbots.flashbots_provider import FlashbotsProvider
from arbitrage_bot.core.memory.memory_bank import MemoryBank
from arbitrage_bot.core.interfaces import TokenPair, LiquidityData
from arbitrage_bot.core.dex.dex_manager import DexManager # Import DexManager

# Mock Web3Client (using MagicMock as a placeholder for web3.Web3 instance)
@pytest.fixture
def mock_web3():
    w3 = MagicMock()
    w3.eth = MagicMock()
    w3.eth.default_account = "0xTestAccount"
    w3.eth.gas_price = 50 * 10**9 # 50 Gwei
    w3.eth.max_priority_fee = 2 * 10**9 # 2 Gwei
    w3.to_checksum_address = lambda x: x # Mock checksum
    w3.eth.contract = MagicMock() # Mock contract creation
    # Add other necessary mock methods/attributes if needed by the manager
    return w3

@pytest.fixture
def mock_flashbots_provider():
    provider = AsyncMock(spec=FlashbotsProvider)
    provider._estimate_gas_price = AsyncMock(return_value=MagicMock(price=50*10**9))
    provider.simulate_bundle = AsyncMock(return_value={"success": True, "profitability": 1000})
    provider._validate_bundle_profit = AsyncMock(return_value=True)
    return provider

@pytest.fixture
def mock_memory_bank():
    bank = AsyncMock(spec=MemoryBank)
    # Mock methods needed by EnhancedFlashLoanManager
    mock_dex1 = AsyncMock(spec=DexManager); mock_dex1.name = "MockDex1" # Create and name mock
    mock_dex2 = AsyncMock(spec=DexManager); mock_dex2.name = "MockDex2" # Create and name mock
    bank.get_active_dexes = AsyncMock(return_value=[mock_dex1, mock_dex2]) # Return named mocks
    bank.get_token_list = AsyncMock(return_value=[{"symbol": "WETH", "address": "0xWETHAddress"}])
    bank.get_contract_address = AsyncMock(return_value="0xArbitrageContract")
    bank.load_abi = AsyncMock(return_value=[]) # Mock ABI
    bank.get_dex = AsyncMock(return_value=AsyncMock()) # Return a generic mock DEX
    return bank

@pytest_asyncio.fixture # Use pytest_asyncio.fixture for async fixtures
async def enhanced_manager(mock_web3, mock_flashbots_provider, mock_memory_bank):
    manager = EnhancedFlashLoanManager(
        web3=mock_web3,
        flashbots_provider=mock_flashbots_provider,
        memory_bank=mock_memory_bank,
        min_profit_threshold=10**15, # 0.001 ETH
        max_slippage=Decimal("0.005"),
        max_paths=3
    )
    # Mock internal provider initialization if necessary (depends on implementation)
    manager._balancer_provider = AsyncMock()
    manager._balancer_provider.initialize = AsyncMock()
    manager._balancer_provider.build_flash_loan_tx = AsyncMock(return_value={ # Mock tx dict
         "from": mock_web3.eth.default_account,
         "to": "0xVaultAddress",
         "data": "0x...",
         "gas": 500000,
         "gasPrice": 50*10**9,
         "nonce": 1
    })
    # Return the manager instance directly
    return manager
    # Cleanup logic after yield is not directly possible with async return fixtures
    # Consider alternative cleanup if needed (e.g., separate cleanup fixture)
    # Add cleanup if necessary, e.g., await manager.close()


# --- Test Cases ---

@pytest.mark.asyncio
async def test_enhanced_manager_initialization(enhanced_manager):
    """Test basic initialization."""
    assert enhanced_manager is not None
    assert enhanced_manager.min_profit_threshold == 10**15
    assert enhanced_manager.max_slippage == Decimal("0.005")

# Mock DEX for route finding tests
async def mock_get_pool_data(token_pair):
    # Return mock liquidity data with required fields
    return LiquidityData(
        liquidity=100 * 10**18,
        fee=3000,
        token0_reserve=50 * 10**18, # Placeholder reserve
        token1_reserve=50000 * 10**18, # Placeholder reserve
        last_update_timestamp=int(time.time()) # Placeholder timestamp
    )

async def mock_estimate_swap_gas(token_pair, amount):
    return 150000 # Example gas

async def mock_calculate_profit(token_pair, amount):
    # Simulate small profit based on amount
    return int(amount * 0.001) # 0.1% profit example

@pytest.mark.asyncio
async def test_find_optimal_routes(enhanced_manager, mock_memory_bank):
    """Test finding optimal routes."""
    # Setup mock DEXes returned by memory bank
    mock_dex1 = AsyncMock(name="MockDex1")
    mock_dex1.get_pool_data = mock_get_pool_data
    mock_dex1.estimate_swap_gas = mock_estimate_swap_gas
    mock_dex1.calculate_profit = mock_calculate_profit

    mock_dex2 = AsyncMock(name="MockDex2")
    mock_dex2.get_pool_data = mock_get_pool_data
    mock_dex2.estimate_swap_gas = mock_estimate_swap_gas
    mock_dex2.calculate_profit = mock_calculate_profit
    # We need to explicitly set the name attribute on the mock objects
    mock_dex1.name = "MockDex1" # This is needed - 'name' parameter only names the mock itself
    mock_dex2.name = "MockDex2" # This is needed too

    mock_memory_bank.get_active_dexes = AsyncMock(return_value=[mock_dex1, mock_dex2])
    mock_memory_bank.get_dex = AsyncMock(side_effect=lambda name: mock_dex1 if name=="MockDex1" else mock_dex2)


    token_pair = TokenPair(token0="0xTokenA", token1="0xTokenB")
    amount = 100 * 10**18 # 100 tokens
    prices = {"MockDex1": Decimal("1000"), "MockDex2": Decimal("1001")} # Example prices

    routes = await enhanced_manager._find_optimal_routes(token_pair, amount, prices)

    assert isinstance(routes, list)
    # Depending on mock profit calculation, assert number of routes, profitability etc.
    # For this mock, both DEXes should yield a route if liquidity allows
    assert len(routes) > 0
    assert isinstance(routes[0], FlashLoanRoute)
    assert routes[0].total_profit > 0

@pytest.mark.asyncio
async def test_prepare_flash_loan_bundle_success(enhanced_manager, mock_memory_bank):
    """Test preparing a successful flash loan bundle."""
     # Setup mock DEXes returned by memory bank
    mock_dex1 = AsyncMock(name="MockDex1")
    mock_dex1.get_pool_data = mock_get_pool_data
    mock_dex1.estimate_swap_gas = mock_estimate_swap_gas
    mock_dex1.calculate_profit = mock_calculate_profit
    # Mock create_swap_transaction to return a mock Transaction object
    mock_dex1.create_swap_transaction = AsyncMock(return_value=MagicMock())

    mock_dex2 = AsyncMock(name="MockDex2")
    mock_dex2.get_pool_data = mock_get_pool_data
    mock_dex2.estimate_swap_gas = mock_estimate_swap_gas
    mock_dex2.calculate_profit = mock_calculate_profit
    mock_dex2.create_swap_transaction = AsyncMock(return_value=MagicMock())
    # We need to explicitly set the name attribute on the mock objects
    mock_dex1.name = "MockDex1" # This is needed - 'name' parameter only names the mock itself
    mock_dex2.name = "MockDex2" # This is needed too

    mock_memory_bank.get_active_dexes = AsyncMock(return_value=[mock_dex1, mock_dex2])
    mock_memory_bank.get_dex = AsyncMock(side_effect=lambda name: mock_dex1 if name=="MockDex1" else mock_dex2)
    # Mock load_abi to return a non-empty ABI
    mock_memory_bank.load_abi = AsyncMock(return_value=[{"name": "repayFlashLoan", "type": "function", "inputs": [], "outputs": []}])
    # Mock the arbitrage contract's repayFlashLoan function build_transaction
    mock_arb_contract = MagicMock()
    mock_repay_func = MagicMock()
    mock_repay_func.build_transaction = MagicMock(return_value={"from": "0xTestAccount", "to": "0xArbitrageContract", "data": "0xRepay..."})
    mock_arb_contract.functions.repayFlashLoan = MagicMock(return_value=mock_repay_func)
    enhanced_manager.web3.eth.contract = MagicMock(return_value=mock_arb_contract)


    token_pair = TokenPair(token0="0xWETHAddress", token1="0xTokenB") # Use WETH from mock bank
    amount = 50 * 10**18 # 50 WETH
    prices = {"MockDex1": Decimal("2000"), "MockDex2": Decimal("2005")}

    # Mock profitability validation to ensure it passes
    enhanced_manager._validate_profitability = AsyncMock(return_value=True)

    bundle = await enhanced_manager.prepare_flash_loan_bundle(token_pair, amount, prices)

    assert isinstance(bundle, list)
    assert len(bundle) >= 3 # Flash loan tx + at least one route tx + repayment tx
    # Further assertions on transaction properties if needed

@pytest.mark.asyncio
async def test_prepare_flash_loan_bundle_unprofitable(enhanced_manager, mock_memory_bank):
    """Test preparing a bundle when the route is not profitable after gas."""
    # Setup mocks similar to test_prepare_flash_loan_bundle_success...
    mock_dex1 = AsyncMock(name="MockDex1")
    mock_dex1.get_pool_data = mock_get_pool_data
    mock_dex1.estimate_swap_gas = mock_estimate_swap_gas
    mock_dex1.calculate_profit = mock_calculate_profit
    mock_dex1.create_swap_transaction = AsyncMock(return_value=MagicMock())
    mock_memory_bank.get_active_dexes = AsyncMock(return_value=[mock_dex1])
    mock_memory_bank.get_dex = AsyncMock(return_value=mock_dex1)
    # Names are now set in the fixture where mocks are created
    mock_dex1.name = "MockDex1"

    token_pair = TokenPair(token0="0xWETHAddress", token1="0xTokenB")
    amount = 50 * 10**18
    prices = {"MockDex1": Decimal("2000")}

    # Mock profitability validation to ensure it FAILS
    enhanced_manager._validate_profitability = AsyncMock(return_value=False)

    with pytest.raises(ValueError, match="Route not profitable after gas costs"):
        await enhanced_manager.prepare_flash_loan_bundle(token_pair, amount, prices)

# Add more tests:
# - Test _calculate_optimal_split logic
# - Test _validate_bundle logic (requires mocking flashbots simulation more deeply)
# - Test error handling within prepare_flash_loan_bundle (e.g., missing WETH, missing contract address)
# - Test interaction with different flash loan providers if manager logic supports it explicitly
#   (Currently seems tied to Balancer via _create_flash_loan_tx)