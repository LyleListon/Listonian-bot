# Arbitrage System Setup PowerShell Script
# This script automates the setup process for the arbitrage bot system

# Terminal colors for better readability
function Write-ColorOutput($ForegroundColor) {
    # Save current color
    $fc = $host.UI.RawUI.ForegroundColor
    
    # Set the new color
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    
    # Write the output
    if ($args) {
        Write-Output $args
    }
    else {
        # Restore original color
        $host.UI.RawUI.ForegroundColor = $fc
    }
}

function Write-Heading($text) {
    Write-ColorOutput Yellow "`n$text"
    Write-ColorOutput Yellow "==============================================================================="
}

function Write-Success($text) {
    Write-ColorOutput Green "[SUCCESS] $text"
}

function Write-Error($text) {
    Write-ColorOutput Red "[ERROR] $text"
}

function Write-Warning($text) {
    Write-ColorOutput Yellow "[WARNING] $text"
}

function Write-Step($step, $total, $text) {
    Write-ColorOutput Cyan "[$step/$total] $text"
}

Clear-Host
Write-Heading "ARBITRAGE SYSTEM SETUP WIZARD"

Write-Output "This script will automate the setup process for the arbitrage bot system.
It will:
 - Check Python installation
 - Setup a virtual environment
 - Install required dependencies
 - Create configuration files
 - Validate the setup
"

# Step 1: Check Python installation
Write-Step 1 6 "Checking Python installation..."
try {
    $pythonVersion = python --version
    Write-Success "Python is installed: $pythonVersion"
}
catch {
    Write-Error "Python is not installed or not in PATH."
    Write-Output "Please install Python 3.10+ from https://www.python.org/downloads/"
    Write-Output "and ensure it's added to your PATH."
    Read-Host "Press Enter to exit"
    exit
}

# Step 2: Check pip installation
Write-Step 2 6 "Checking pip installation..."
try {
    $pipVersion = python -m pip --version
    Write-Success "pip is installed: $pipVersion"
}
catch {
    Write-Warning "pip is not installed or not working properly."
    
    $answer = Read-Host "Do you want to install pip? (y/n)"
    if ($answer -eq "y") {
        Write-Output "Installing pip..."
        python -m ensurepip --upgrade
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install pip. Please install it manually."
            Read-Host "Press Enter to exit"
            exit
        }
    }
    else {
        Write-Error "pip is required for installation. Exiting."
        Read-Host "Press Enter to exit"
        exit
    }
}

# Step 3: Setup virtual environment
Write-Step 3 6 "Setting up virtual environment..."
if (Test-Path "venv") {
    Write-Output "Virtual environment already exists."
    $recreate = Read-Host "Do you want to recreate it? (y/n)"
    
    if ($recreate -eq "y") {
        Write-Output "Recreating virtual environment..."
        Remove-Item -Recurse -Force venv
        python -m venv venv
    }
}
else {
    Write-Output "Creating new virtual environment..."
    python -m venv venv
}

# Activate virtual environment
Write-Output "Activating virtual environment..."
try {
    .\venv\Scripts\Activate.ps1
    Write-Success "Virtual environment is setup and activated."
}
catch {
    Write-Error "Failed to activate virtual environment."
    Write-Output "Error: $_"
    
    $continue = Read-Host "Do you want to continue without virtual environment? (y/n)"
    if ($continue -ne "y") {
        Read-Host "Press Enter to exit"
        exit
    }
}

# Step 4: Install dependencies
Write-Step 4 6 "Installing dependencies..."
Write-Output "This may take several minutes depending on your internet connection."

Write-Output "`nInstalling core dependencies..."
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some dependencies failed to install."
    $continue = Read-Host "Do you want to continue anyway? (y/n)"
    if ($continue -ne "y") {
        Read-Host "Press Enter to exit"
        exit
    }
}

Write-Output "`nInstalling development dependencies..."
pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some development dependencies failed to install."
    Write-Output "This is not critical for running the system, but may affect development tools."
}

Write-Output "`nInstalling additional dependencies for monitoring dashboard..."
pip install aiohttp aiofiles pandas matplotlib
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some dashboard dependencies failed to install."
    Write-Output "This may affect the monitoring dashboard functionality."
}

Write-Success "Dependencies installed."

# Step 5: Setting up configuration
Write-Step 5 6 "Setting up configuration..."

# Create required directories
if (-not (Test-Path "configs")) { New-Item -ItemType Directory -Path "configs" | Out-Null }
if (-not (Test-Path "monitoring_data")) { New-Item -ItemType Directory -Path "monitoring_data" | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
if (-not (Test-Path "analytics")) { New-Item -ItemType Directory -Path "analytics" | Out-Null }

# Create main config file if it doesn't exist
if (-not (Test-Path "configs\config.json")) {
    Write-Output "Creating default configuration file..."
    $configJson = @"
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

    $configJson | Out-File -FilePath "configs\config.json" -Encoding utf8

    Write-Output "`nConfiguration file created. You need to update the following values:"
    Write-Output " - provider_url: Your Ethereum node URL" 
    Write-Output " - private_key: Your wallet private key"
    Write-Output " - wallet_address: Your wallet address"
    Write-Output " - flash_loans.contract_address: Your deployed contract addresses"
    Write-Output " - flashbots.auth_signer_key: Your Flashbots auth key"
}

# Create monitor config if it doesn't exist
if (-not (Test-Path "configs\monitor_config.json")) {
    Write-Output "`nCreating monitor configuration file..."
    $monitorJson = @"
{
  "host": "localhost",
  "port": 8080,
  "refresh_interval": 30,
  "data_directory": "monitoring_data",
  "metrics_history_size": 100,
  "charts_enabled": true,
  "alerts_enabled": true,
  "profit_threshold_alert": 0.001,
  "gas_price_threshold_alert": 150,
  "mev_risk_threshold_alert": "high"
}
"@

    $monitorJson | Out-File -FilePath "configs\monitor_config.json" -Encoding utf8
}

Write-Success "Configuration files created."

# Step 6: Validate installation
Write-Step 6 6 "Validating installation..."

Write-Output "Checking core modules..."
try {
    python -c "import arbitrage_bot"
    Write-Output "Core modules validated."
}
catch {
    Write-Warning "Failed to import arbitrage_bot module. This may indicate an installation issue."
}

Write-Output "Checking dashboard module..."
try {
    python -c "import dashboard"
    Write-Output "Dashboard module validated."
}
catch {
    Write-Warning "Failed to import dashboard module. This may affect the monitoring dashboard functionality."
}

# Completion
Write-Heading "ARBITRAGE SYSTEM SETUP COMPLETE"

Write-Output "Your arbitrage system has been set up successfully!"
Write-Output "`nNext steps:"
Write-ColorOutput Cyan "1. Edit configs\config.json with your actual configuration values"
Write-ColorOutput Cyan "2. Run the system using: powershell -ExecutionPolicy Bypass -File .\run_example.ps1"

Write-Output "`nOptionally:"
Write-ColorOutput Cyan "- Read cline_docs\startup_guide_complete.md for detailed instructions"
Write-ColorOutput Cyan "- Check cline_docs\arbitrage_integration_guide.md for integration details" 
Write-ColorOutput Cyan "- See DOCKER_AI_INTEGRATION.md for future AI enhancements"

$configure = Read-Host "`nDo you want to update your configuration file now? (y/n)"
if ($configure -eq "y") {
    # Try to use VSCode if available, otherwise fall back to notepad
    try {
        code configs\config.json
    }
    catch {
        notepad configs\config.json
    }
}

$launch = Read-Host "`nDo you want to launch the system now? (y/n)"
if ($launch -eq "y") {
    .\run_example.ps1
}

Write-Output "`nSetup completed successfully."
Read-Host "Press Enter to exit"