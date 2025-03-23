# PowerShell script to start both the arbitrage bot and dashboard
# Ensures proper initialization and error handling

# Stop on any error
$ErrorActionPreference = "Stop"

# Function to check if Python is installed
function Test-Python {
    try {
        python --version
        return $true
    }
    catch {
        return $false
    }
}

# Function to check if pip is installed
function Test-Pip {
    try {
        pip --version
        return $true
    }
    catch {
        return $false
    }
}

# Function to create directories if they don't exist
function Ensure-Directories {
    $directories = @(
        "logs",
        "memory-bank",
        "memory-bank/trades",
        "memory-bank/metrics",
        "memory-bank/state"
    )

    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir | Out-Null
            Write-Host "Created directory: $dir"
        }
    }
}

# Function to check environment setup
function Check-Environment {
    # Check Python
    if (-not (Test-Python)) {
        throw "Python is not installed or not in PATH"
    }

    # Check pip
    if (-not (Test-Pip)) {
        throw "pip is not installed or not in PATH"
    }

    # Check .env file
    if (-not (Test-Path "secure/.env")) {
        throw "secure/.env file not found. Please create it with required credentials."
    }
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host "Installing/Updating dependencies..."
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install dependencies"
    }
}

# Function to start the arbitrage bot
function Start-ArbitrageBot {
    Write-Host "Starting arbitrage bot..."
    $botProcess = Start-Process -FilePath "python" -ArgumentList "run_bot.py" -PassThru -WindowStyle Normal -RedirectStandardError "logs/bot.err"
    return $botProcess
}

# Function to start the dashboard
function Start-Dashboard {
    Write-Host "Starting dashboard..."
    $dashProcess = Start-Process -FilePath "python" -ArgumentList "-m new_dashboard.dashboard.app" -PassThru -WindowStyle Normal -RedirectStandardError "logs/dashboard.err"
    return $dashProcess
}

# Main execution
try {
    # Kill any existing instances
    Write-Host "Cleaning up existing processes..."
    taskkill /F /FI "WINDOWTITLE eq Arbitrage Dashboard*" /T >$null 2>&1
    taskkill /F /FI "WINDOWTITLE eq Arbitrage Bot*" /T >$null 2>&1
    Start-Sleep -Seconds 3

    # Check environment
    Write-Host "Checking environment..."
    Check-Environment

    # Create required directories
    Write-Host "Ensuring required directories exist..."
    Ensure-Directories

    # Install dependencies
    Install-Dependencies

    # Set environment variables
    Write-Host "Loading environment variables..."
    Get-Content "secure/.env" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value)
        }
    }

    # Start bot and dashboard
    $botProcess = Start-ArbitrageBot
    Start-Sleep -Seconds 5  # Wait for bot to initialize
    $dashProcess = Start-Dashboard

    Write-Host "Both processes started successfully"
    Write-Host "Bot PID: $($botProcess.Id)"
    Write-Host "Dashboard PID: $($dashProcess.Id)"
    Write-Host "Monitor logs in logs/bot.err and logs/dashboard.err"

    # Wait for processes
    Write-Host "Press Ctrl+C to stop all processes..."
    while ($true) {
        if ($botProcess.HasExited -or $dashProcess.HasExited) {
            throw "One of the processes has terminated unexpectedly"
        }
        Start-Sleep -Seconds 1
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
finally {
    # Cleanup on exit
    Write-Host "Cleaning up processes..."
    taskkill /F /FI "WINDOWTITLE eq Arbitrage Dashboard*" /T >$null 2>&1
    taskkill /F /FI "WINDOWTITLE eq Arbitrage Bot*" /T >$null 2>&1
}