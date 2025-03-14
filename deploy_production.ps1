# rrbitrage System Production Deployment Script
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
    } else {
        Write-Output "Virtual environment found. Activating..."
        . .\venv\Scripts\Activate.ps1
        
        # Update dependencies
        Write-Output "Updating dependencies..."
        pip install -r requirements.txt --upgrade
    }
    
    Write-Success "Environment setup complete"
    
    # Step 2: Create production configuration
    Write-Step "2" "Setting up production configuration"
    
    # Check if production config exists
    if (-not (Test-Path ".\configs\production.json")) {
        Write-Output "Production configuration not found. Creating template..."
        
        # Create production config template
        $productionConfig = @"
{
  "web3": {
    "rpc_url": "YOUR_ETHEREUM_NODE_URL",
    "chain_id": 8453,
    "wallet_key": "YOUR_PRIVATE_KEY"
  },

  "tokens": {
    "WETH": {
      "address": "0x4200000000000000000000000000000000000006",
      "decimals": 18
    },
    "USDC": {
      "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "decimals": 6
    },
    "USDT": {
      "address": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
      "decimals": 6
    },
    "DAI": {
      "address": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
      "decimals": 18
    }
  },

  "dexes": {
    "aerodrome": {
      "factory": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
      "router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
      "version": "v2",
      "fee": 30
    },
    "baseswap": {
      "factory": "0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB",
      "router": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
      "version": "v2",
      "fee": 30
    },
    "swapbased": {
      "factory": "0x36218B2F8dC32D43fb5EcF45F2E6113cd52Cc5B9",
      "router": "0x36218B2F8dC32D43fb5EcF45F2E6113cd52Cc5B9",
      "version": "v2",
      "fee": 30
    }
  },

  "flash_loans": {
    "enabled": true,
    "use_flashbots": true,
    "min_profit_basis_points": 200,  // 2% minimum profit
    "max_trade_size": "1000000000000000000",  // 1 ETH in wei
    "slippage_tolerance": 50,  // 0.5%
    "transaction_timeout": 180,  // seconds
    "balancer_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8"
  },

  "flashbots": {
    "relay_url": "https://relay.flashbots.net",
    "auth_key": "YOUR_FLASHBOTS_AUTH_KEY",
    "min_profit": "1000000000000000",  // 0.001 ETH in wei
    "max_gas_price": "500000000000"    // 500 Gwei in wei
  },

  "mev_protection": {
    "enabled": true,
    "use_flashbots": true,
    "max_bundle_size": 5,
    "max_blocks_ahead": 3,
    "min_priority_fee": "1.5",  // Gwei
    "max_priority_fee": "3.0",  // Gwei
    "sandwich_detection": true,
    "frontrun_detection": true,
    "backrun_detection": true,
    "time_bandit_detection": true,
    "profit_threshold": "0.1",  // ETH
    "gas_threshold": "1.5",     // multiplier
    "confidence_threshold": "0.7",
    "adaptive_gas": true
  },

  "scan": {
    "interval": 1.0,  // seconds
    "amount_wei": "1000000000000000000",  // 1 ETH in wei
    "max_paths": 5
  },

  "monitoring": {
    "stats_interval": 300,  // seconds
    "log_level": "INFO"
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
    
    # Step 3: Create logs directory
    Write-Step "3" "Setting up logging"
    
    if (-not (Test-Path ".\logs")) {
        Write-Output "Creating logs directory..."
        New-Item -ItemType Directory -Path ".\logs" | Out-Null
    }
    
    if (-not (Test-Path ".\monitoring_data")) {
        Write-Output "Creating monitoring data directory..."
        New-Item -ItemType Directory -Path ".\monitoring_data" | Out-Null
    }
    
    Write-Success "Logging setup complete"
    
    # Step 4: Deploy the system
    Write-Step "4" "Deploying the system"
    
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
    
    Write-Success "System deployed successfully"
    
    # Step 5: Start the system
    Write-Step "5" "Starting the system"
    
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
    
    # Step 6: Dashboard Information
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