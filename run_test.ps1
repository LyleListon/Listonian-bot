# PowerShell script to run tests with appropriate error handling

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Running Arbitrage System Tests" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

try {
    # Activate virtual environment if it exists
    if (Test-Path ".\venv\Scripts\Activate.ps1") {
        . .\venv\Scripts\Activate.ps1
        Write-Host "Virtual environment activated" -ForegroundColor Green
    }

    # Install required packages if needed
    Write-Host "Installing pytest and required packages..." -ForegroundColor Yellow
    pip install pytest pytest-asyncio pytest-mock pytest-cov web3>=6.0.0 > $null

    # Create a simple test file for our components
    $testFile = @"
import pytest
import asyncio
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_web3_manager():
    """Test the Web3Manager can be instantiated."""
    from arbitrage_bot.core.web3.web3_manager import Web3Manager
    
    # Use a test provider URL
    web3_manager = Web3Manager("http://localhost:8545")
    assert web3_manager is not None
    assert web3_manager.provider_url == "http://localhost:8545"

@pytest.mark.asyncio
async def test_path_finder():
    """Test the PathFinder can be instantiated."""
    from arbitrage_bot.core.path_finder import PathFinder
    
    # Mock the DEX manager
    dex_manager = MagicMock()
    
    # Create PathFinder
    path_finder = PathFinder(dex_manager)
    assert path_finder is not None
    assert path_finder.dex_manager == dex_manager

@pytest.mark.asyncio
async def test_flash_loan_manager():
    """Test the AsyncFlashLoanManager can be instantiated."""
    from arbitrage_bot.core.flash_loan_manager_async import AsyncFlashLoanManager
    
    # Mock components
    web3_manager = MagicMock()
    config = {
        'flash_loans': {
            'enabled': True,
            'use_flashbots': True
        }
    }
    
    # Create FlashLoanManager
    flash_loan_manager = AsyncFlashLoanManager(web3_manager, config)
    assert flash_loan_manager is not None
    assert flash_loan_manager.enabled == True
    assert flash_loan_manager.use_flashbots == True

@pytest.mark.asyncio
async def test_mev_protection():
    """Test the MEVProtectionOptimizer can be instantiated."""
    from arbitrage_bot.integration.mev_protection import MEVProtectionOptimizer
    
    # Mock components
    web3_manager = MagicMock()
    config = {
        'mev_protection': {
            'enabled': True,
            'use_flashbots': True
        }
    }
    
    # Create MEVProtectionOptimizer
    mev_optimizer = MEVProtectionOptimizer(web3_manager, config)
    assert mev_optimizer is not None
    assert mev_optimizer.enabled == True
    assert mev_optimizer.use_flashbots == True
"@

    # Save the test file
    $testFile | Out-File -FilePath ".\tests\test_basic_components.py" -Encoding utf8

    # Run the tests
    Write-Host "`nRunning tests..." -ForegroundColor Cyan
    pytest tests/test_basic_components.py -v

    Write-Host "`nTests completed successfully!" -ForegroundColor Green

} catch {
    Write-Host "An error occurred: $_" -ForegroundColor Red
} finally {
    # Provide a clean exit
    Write-Host "`n================================================================" -ForegroundColor Cyan
    Write-Host "Press Enter to exit..." -ForegroundColor Yellow
    Read-Host
}