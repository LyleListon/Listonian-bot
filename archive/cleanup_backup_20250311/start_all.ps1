# Start Listonian Arbitrage Bot Setup
Write-Host "Starting Listonian Arbitrage Bot Setup..."

# Check Python version
$pythonVersion = py -3.12 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pythonVersion -lt [version]"3.12") {
    Write-Error "Python 3.12 or higher is required. Current version: $pythonVersion"
    Write-Host "Please install Python 3.12 or higher from https://www.python.org/downloads/"
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Force -Path "logs" | Out-Null
}

# Set dashboard port
[Environment]::SetEnvironmentVariable("DASHBOARD_PORT", "5000")

# Set Python path to include current directory
[Environment]::SetEnvironmentVariable("PYTHONPATH", "$PWD")

# Set asyncio debug mode for development
[Environment]::SetEnvironmentVariable("PYTHONASYNCIODEBUG", "1")

# Install dependencies if needed
Write-Host "Checking dependencies..."
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt --quiet --no-input
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies. Please check pip logs for details."
    exit 1
}

# Initialize secure environment if needed
Write-Host "Checking secure environment..."
if (-not (Test-Path secure/.key)) {
    Write-Host "Initializing secure environment..."
    py -3.12 init_secure.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to initialize secure environment. Please check the error messages above."
        exit 1
    }
}

# Check config files
if (-not (Test-Path configs/config.json)) {
    Write-Error "config.json not found. Please create configs/config.json with your settings."
    exit 1
}

if (-not (Test-Path configs/wallet_config.json)) {
    Write-Error "wallet_config.json not found. Please create configs/wallet_config.json with your wallet settings."
    exit 1
}

# Load environment variables
if (Test-Path .env.production) {
    Write-Host "Loading environment variables..."
    Get-Content .env.production | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }
} else {
    Write-Warning ".env.production not found. Using default environment variables."
}

# Kill any existing Python processes
Write-Host "Cleaning up any existing Python processes..."
Get-Process | Where-Object { $_.ProcessName -eq "python" } | ForEach-Object { 
    try {
        Stop-Process -Id $_.Id -Force
        Write-Host "Stopped Python process: $($_.Id)"
    } catch {
        Write-Warning "Could not stop process: $($_.Id)"
    }
}

# Additional cleanup for port 5000
Write-Host "Checking for existing processes on port 5000..."
$existingProcess = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
if ($existingProcess) {
    Write-Host "Found existing process on port 5000. Stopping..."
    Stop-Process -Id $existingProcess -Force
    Start-Sleep -Seconds 2
}

# Ensure required directories exist
Write-Host "Creating required directories..."
@(
    "data/memory",
    "data/storage",
    "minimal_dashboard/static",
    "minimal_dashboard/templates",
    "logs"
) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Force -Path $_ | Out-Null
        Write-Host "Created directory: $_"
    }
}

# Set timestamp for log files
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Start main arbitrage bot
Write-Host "Starting main arbitrage bot..."
$botLogFile = "logs/bot_$timestamp.log"
$botErrorLog = "logs/bot_$timestamp.error.log"

# Start the bot process with output
py -3.12 run_bot.py

# Start dashboard
Write-Host "Starting minimal dashboard..."
$dashboardLogFile = "logs/dashboard_$timestamp.log"
$dashboardErrorLog = "logs/dashboard_$timestamp.error.log"

# Start the dashboard process with output
py -3.12 minimal_dashboard.py

# Display status
Write-Host ""
Write-Host "==============================="
Write-Host "Listonian Arbitrage Bot Status"
Write-Host "==============================="
Write-Host ""
Write-Host "Main Bot: Running (providing live data)"
Write-Host ""
Write-Host "Dashboard: Running (visualizing data)"
Write-Host ""
Write-Host "Monitor the logs directory for detailed output:"
Write-Host "- $botLogFile (main bot logs)"
Write-Host "- $dashboardLogFile (dashboard logs)"
Write-Host ""
Write-Host "Access dashboard at: http://localhost:5000"
Write-Host ""
Write-Host "Press Ctrl+C to stop all processes."
Write-Host ""
