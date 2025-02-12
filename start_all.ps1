# Start Listonian Arbitrage Bot Setup
Write-Host "Starting Listonian Arbitrage Bot Setup..."

# Create logs directory if it doesn't exist
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Set timestamp for log files
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Check Python installation
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Please install Python 3.8 or higher."
    exit 1
}

# Create and activate virtual environment
Write-Host "Creating virtual environment..."
python -m venv venv
if ($IsLinux -or $IsMacOS) {
    $env:VIRTUAL_ENV = Join-Path $PWD "venv"
    $env:PATH = "$env:VIRTUAL_ENV/bin:$env:PATH"
} else {
    & ./venv/Scripts/Activate.ps1
}

# Install dependencies (with minimal output)
Write-Host "Installing dependencies..."
pip install -r requirements.txt --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies. Check logs for details."
    exit 1
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

# Start dashboard in background with minimal output
Write-Host "Starting dashboard..."
$dashboardJob = Start-Job -ScriptBlock {
    $env:PYTHONWARNINGS="ignore"
    python start_dashboard.py *> "logs/dashboard_$using:timestamp.log"
}

# Wait for dashboard to initialize
Start-Sleep -Seconds 5

# Start main bot with minimal output
Write-Host "Starting arbitrage bot..."
$botJob = Start-Job -ScriptBlock {
    $env:PYTHONWARNINGS="ignore"
    python main.py *> "logs/bot_$using:timestamp.log"
}

# Display status
Write-Host ""
Write-Host "==============================="
Write-Host "Listonian Arbitrage Bot Status"
Write-Host "==============================="
Write-Host ""
Write-Host "Dashboard: Running (Job ID: $($dashboardJob.Id))"
Write-Host "Bot: Running (Job ID: $($botJob.Id))"
Write-Host ""
Write-Host "Monitor the logs directory for detailed output."
Write-Host "Press Ctrl+C to stop all processes."
Write-Host ""

# Handle cleanup on exit
$cleanupAction = {
    Write-Host "Stopping processes..."
    Get-Job | Stop-Job
    Get-Job | Remove-Job
}

# Register cleanup action
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $cleanupAction | Out-Null

# Keep script running and monitor jobs with minimal output
try {
    while ($true) {
        $dashboardState = Receive-Job $dashboardJob -Keep
        $botState = Receive-Job $botJob -Keep
        if ($dashboardState -match "^ERROR|^CRITICAL|^FATAL") { Write-Host "Dashboard: $dashboardState" }
        if ($botState -match "^ERROR|^CRITICAL|^FATAL") { Write-Host "Bot: $botState" }
        Start-Sleep -Seconds 1
    }
} finally {
    # Cleanup on script end
    & $cleanupAction
}
