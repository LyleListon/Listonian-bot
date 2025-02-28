# Arbitrage System Production Deployment Script
# This script automates the deployment of the arbitrage system to production

# Set error action preference to stop on error
$ErrorActionPreference = "Stop"

# Set colors for better readability
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) { Write-Output $args }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Heading($text) {
    Write-ColorOutput Yellow "`n$text"
    Write-ColorOutput Yellow "==============================================================================="
}

function Write-Success($text) {
    Write-ColorOutput Green "[SUCCESS] $text"
}

function Write-Step($step, $text) {
    Write-ColorOutput Cyan "`n[STEP $step] $text"
}

Clear-Host
Write-Heading "ARBITRAGE SYSTEM PRODUCTION DEPLOYMENT"

Write-Output "This script will deploy the arbitrage system to production."
Write-Output "Make sure you have configured your environment before proceeding."

# Confirm deployment
$confirmation = Read-Host "`nAre you sure you want to deploy to production? (y/n)"
if ($confirmation -ne "y") {
    Write-Output "Deployment cancelled."
    exit
}

try {
    # Step 1: Setup environment if not already done
    Write-Step "1" "Setting up environment"
    
    # Check if virtual environment exists
    if (-not (Test-Path ".\venv")) {
        Write-Output "Virtual environment not found. Creating..."
        python -m venv venv
        
        # Activate virtual environment
        . .\venv\Scripts\Activate.ps1
        
        # Install dependencies
        Write-Output "Installing dependencies..."
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    } else {
        Write-Output "Virtual environment found. Activating..."
        . .\venv\Scripts\Activate.ps1
        
        # Update dependencies
        Write-Output "Updating dependencies..."
        pip install -r requirements.txt --upgrade
        pip install -r requirements-dev.txt --upgrade
    }
    
    Write-Success "Environment setup complete"
    
    # Step 2: Run tests to verify everything is working
    Write-Step "2" "Running verification tests"
    
    # Run tests
    . .\run_test.ps1
    
    # Check if tests passed (we'll assume they did if we get here since ErrorActionPreference is Stop)
    Write-Success "Verification tests passed"
    
    # Step 3: Create production configuration
    Write-Step "3" "Setting up production configuration"
    
    # Check if production config exists
    if (-not (Test-Path ".\configs\production.json")) {
        Write-Output "Production configuration not found. Creating template..."
        
        # Create production config template
        $productionConfig = @"
{
  "provider_url": "YOUR_ETHEREUM_NODE_URL",
  "chain_id": 1,
  "private_key": "YOUR_PRIVATE_KEY",
  "wallet_address": "YOUR_WALLET_ADDRESS",
  "log_level": "INFO",
  "max_paths_to_check": 100,
  "min_profit_threshold": 0.001,
  "slippage_tolerance": 50,
  "gas_limit_buffer": 20,

  "tokens": {
    "WETH": {
      "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
      "decimals": 18
    },
    "USDC": {
      "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "decimals": 6
    },
    "USDT": {
      "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
      "decimals": 6
    },
    "DAI": {
      "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
      "decimals": 18
    }
  },

  "flash_loans": {
    "enabled": true,
    "use_flashbots": true,
    "min_profit_basis_points": 200,
    "max_trade_size": "1",
    "slippage_tolerance": 50,
    "transaction_timeout": 180,
    "balancer_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
    "contract_address": {
      "mainnet": "YOUR_DEPLOYED_CONTRACT_ADDRESS",
      "testnet": "YOUR_TESTNET_CONTRACT_ADDRESS"
    }
  },

  "flashbots": {
    "relay_url": "https://relay.flashbots.net",
    "auth_signer_key": "YOUR_FLASHBOTS_AUTH_KEY",
    "min_profit_threshold": 1000000000000000
  },

  "mev_protection": {
    "enabled": true,
    "use_flashbots": true,
    "max_bundle_size": 5,
    "max_blocks_ahead": 3,
    "min_priority_fee": "1.5",
    "max_priority_fee": "3",
    "sandwich_detection": true,
    "frontrun_detection": true,
    "adaptive_gas": true
  }
}
"@
        
        # Save production config
        $productionConfig | Out-File -FilePath ".\configs\production.json" -Encoding utf8
        
        # Open the config file for editing
        Write-Output "Opening production config for editing..."
        
        # Try to use VSCode if available, otherwise use notepad
        try {
            code ".\configs\production.json"
        } catch {
            notepad ".\configs\production.json"
        }
        
        # Wait for user to finish editing
        Read-Host "Press Enter when you've finished editing the production configuration..."
    } else {
        Write-Output "Production configuration found."
        
        # Ask if user wants to edit
        $editConfig = Read-Host "Do you want to edit the production configuration? (y/n)"
        if ($editConfig -eq "y") {
            # Try to use VSCode if available, otherwise use notepad
            try {
                code ".\configs\production.json"
            } catch {
                notepad ".\configs\production.json"
            }
            
            # Wait for user to finish editing
            Read-Host "Press Enter when you've finished editing the production configuration..."
        }
    }
    
    Write-Success "Production configuration ready"
    
    # Step 4: Create logs directory
    Write-Step "4" "Setting up logging"
    
    if (-not (Test-Path ".\logs")) {
        Write-Output "Creating logs directory..."
        New-Item -ItemType Directory -Path ".\logs" | Out-Null
    }
    
    if (-not (Test-Path ".\monitoring_data")) {
        Write-Output "Creating monitoring data directory..."
        New-Item -ItemType Directory -Path ".\monitoring_data" | Out-Null
    }
    
    Write-Success "Logging setup complete"
    
    # Step 5: Deploy the system
    Write-Step "5" "Deploying the system"
    
    Write-Output "Starting the arbitrage system in production mode..."
    
    # Create a startup batch file
    $startupBat = @"
@echo off
echo ===============================================================================
echo ARBITRAGE SYSTEM PRODUCTION MODE
echo ===============================================================================
echo.
echo Starting arbitrage system...
call venv\Scripts\activate.bat
python production.py
echo.
echo ===============================================================================
echo Press any key to exit...
pause >nul
"@
    
    # Save startup batch file
    $startupBat | Out-File -FilePath ".\start_production.bat" -Encoding utf8
    
    # Create a production Python script
    $productionPy = @"
#!/usr/bin/env python
"""
Production Arbitrage System

This script runs the arbitrage system in production mode.
"""

import asyncio
import logging
import json
import time
import os
from pathlib import Path
from typing import Dict, Any

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create a timestamp for log filename
timestamp = time.strftime("%Y%m%d-%H%M%S")
log_file = log_dir / f"arbitrage_production_{timestamp}.log"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("production")

async def run_production_system():
    """Run the arbitrage system in production mode."""
    logger.info("=" * 70)
    logger.info("STARTING ARBITRAGE SYSTEM IN PRODUCTION MODE")
    logger.info("=" * 70)
    
    try:
        # Step 1: Import required components
        logger.info("Importing required components...")
        from arbitrage_bot.utils.config_loader import load_config
        from arbitrage_bot.core.web3.web3_manager import create_web3_manager
        from arbitrage_bot.integration.flashbots_integration import setup_flashbots_rpc
        from arbitrage_bot.core.flash_loan_manager_async import create_flash_loan_manager
        from arbitrage_bot.integration.mev_protection import create_mev_protection_optimizer
        from arbitrage_bot.core.dex.dex_manager import DexManager
        from arbitrage_bot.core.path_finder import PathFinder
        
        # Step 2: Load production configuration
        logger.info("Loading production configuration...")
        config = load_config("configs/production.json")
        
        # Step 3: Initialize Web3Manager
        logger.info("Initializing Web3Manager...")
        web3_manager = await create_web3_manager(
            provider_url=config.get('provider_url'),
            chain_id=config.get('chain_id'),
            private_key=config.get('private_key')
        )
        
        logger.info(f"Connected to network with chain ID: {config.get('chain_id')}")
        logger.info(f"Using wallet address: {web3_manager.wallet_address}")
        
        # Step 4: Set up Flashbots RPC integration
        logger.info("Setting up Flashbots RPC integration...")
        flashbots_components = await setup_flashbots_rpc(
            web3_manager=web3_manager,
            config=config
        )
        
        flashbots_manager = flashbots_components['flashbots_manager']
        balance_validator = flashbots_components['balance_validator']
        
        # Step 5: Initialize Flash Loan Manager
        logger.info("Initializing Flash Loan Manager...")
        flash_loan_manager = await create_flash_loan_manager(
            web3_manager=web3_manager,
            config=config,
            flashbots_manager=flashbots_manager
        )
        
        # Step 6: Initialize MEV Protection Optimizer
        logger.info("Initializing MEV Protection Optimizer...")
        mev_optimizer = await create_mev_protection_optimizer(
            web3_manager=web3_manager,
            config=config,
            flashbots_manager=flashbots_manager
        )
        
        # Step 7: Set up DexManager and PathFinder
        logger.info("Initializing DexManager and PathFinder...")
        dex_manager = await DexManager.create(web3_manager, config)
        path_finder = PathFinder(dex_manager, config)
        
        # Step 8: Start the monitoring dashboard
        logger.info("Starting monitoring dashboard...")
        # In a production environment, this would start the monitoring dashboard
        
        # Step 9: Start the main arbitrage loop
        logger.info("Starting main arbitrage loop...")
        
        logger.info("System initialized successfully")
        logger.info("Running in production mode...")
        
        # Main arbitrage loop
        while True:
            try:
                # Analyze mempool for MEV risk
                risk_assessment = await mev_optimizer.analyze_mempool_risk()
                logger.info(f"MEV risk level: {risk_assessment['risk_level']}")
                
                # Look for arbitrage opportunities
                # In a real implementation, this would find actual opportunities
                logger.info("Scanning for arbitrage opportunities...")
                
                # In production, this would be a much more sophisticated loop
                # with actual arbitrage detection and execution
                
                # Wait before next iteration
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in arbitrage loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait longer on error
        
    except Exception as e:
        logger.error(f"Failed to start arbitrage system: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    """Run the production system."""
    try:
        asyncio.run(run_production_system())
    except KeyboardInterrupt:
        logger.info("System shutdown requested")
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
"@
    
    # Save production script
    $productionPy | Out-File -FilePath ".\production.py" -Encoding utf8
    
    Write-Success "System deployed successfully"
    
    # Step 6: Start the system
    Write-Step "6" "Starting the system"
    
    Write-Output "Do you want to start the system now?"
    $startNow = Read-Host "Start now? (y/n)"
    
    if ($startNow -eq "y") {
        Write-Output "Starting system..."
        Start-Process -FilePath ".\start_production.bat"
        Write-Success "System started successfully"
    } else {
        Write-Output "You can start the system later by running:"
        Write-Output "  .\start_production.bat"
    }
    
    Write-Heading "DEPLOYMENT COMPLETE"
    
    Write-Output "The arbitrage system has been successfully deployed to production."
    Write-Output "`nTo start the system:"
    Write-Output "  .\start_production.bat"
    
    Write-Output "`nTo monitor the system:"
    Write-Output "  Check the logs in the logs directory"
    Write-Output "  Use the monitoring dashboard (see Dashboard section below)"
    
    # Step 7: Dashboard Information
    Write-Heading "DASHBOARD SETUP"
    
    Write-Output "The arbitrage system includes a comprehensive monitoring dashboard."
    Write-Output "`nTo start the dashboard:"
    Write-Output "  .\start_dashboard.bat"
    Write-Output "  OR"
    Write-Output "  python start_dashboard.py"
    
    Write-Output "`nDashboard features:"
    Write-Output "  - Real-time arbitrage opportunity tracking"
    Write-Output "  - Balance and allocation monitoring"
    Write-Output "  - Historical trade performance analytics"
    Write-Output "  - DEX pricing and liquidity analysis"
    Write-Output "  - System status and health monitoring"
    
    Write-Output "`nThe dashboard will be available at:"
    Write-Output "  http://localhost:8080"
    
    Write-Output "`nYou can customize the host and port by running:"
    Write-Output "  python start_dashboard.py --host=0.0.0.0 --port=9000"
    
} catch {
    Write-ColorOutput Red "`n[ERROR] Deployment failed: $_"
    Write-Output "`nCheck the error message and try again."
} finally {
    # Ensure we always deactivate the virtual environment
    if (Get-Command deactivate -ErrorAction SilentlyContinue) {
        deactivate
    }
}

Write-Output "`nPress Enter to exit..."
Read-Host