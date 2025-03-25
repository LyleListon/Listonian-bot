# PowerShell script to start both the arbitrage bot and dashboard
# Ensures proper initialization and error handling

# Stop on any error
$ErrorActionPreference = "Stop"

# Store process IDs for cleanup
$Global:BotProcess = $null
$Global:DashProcess = $null

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
    # Install the package in development mode
    pip install -e .
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install dependencies"
    }
}

# Function to start the arbitrage bot
function Start-ArbitrageBot {
    Write-Host "Starting arbitrage bot..."
    $script:BotProcess = Start-Process -FilePath "python" -ArgumentList "main.py" -PassThru -NoNewWindow -RedirectStandardError "logs/bot.err"
    return $script:BotProcess
}

# Function to start the dashboard
function Start-Dashboard {
    Write-Host "Starting dashboard..."
    $script:DashProcess = Start-Process -FilePath "python" -ArgumentList "run_dashboard.py" -PassThru -NoNewWindow -RedirectStandardError "logs/dashboard.err"
    return $script:DashProcess
}

# Function to cleanup processes
function Cleanup-Processes {
    Write-Host "Cleaning up processes..."
    
    # Stop bot process if running
    if ($script:BotProcess -and -not $script:BotProcess.HasExited) {
        Stop-Process -Id $script:BotProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped bot process (PID: $($script:BotProcess.Id))"
    }
    
    # Stop dashboard process if running
    if ($script:DashProcess -and -not $script:DashProcess.HasExited) {
        Stop-Process -Id $script:DashProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped dashboard process (PID: $($script:DashProcess.Id))"
    }
}

# Register cleanup handler for Ctrl+C
$Global:CleanupHandler = {
    Write-Host "`nReceived shutdown signal"
    Cleanup-Processes
    exit 0
}
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $Global:CleanupHandler
$null = Register-ObjectEvent -InputObject ([Console]) -EventName CancelKeyPress -Action $Global:CleanupHandler

# Main execution
try {
    # Clean up any existing processes first
    Write-Host "Cleaning up any existing processes..."
    
    # Kill any processes using port 8090
    $netstat = netstat -ano | Select-String ":8090"
    if ($netstat) {
        $processId = $netstat -split ' +' | Select-Object -Last 1
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    
    # Kill any existing bot or dashboard processes
    Get-Process | Where-Object { $_.ProcessName -match 'python' } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Start-Sleep -Seconds 2

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
            $name = ($matches[1]).Trim()
            $value = $matches[2]
            
            # Map environment variables to ARBY_ format
            switch ($name) {
                "BASE_RPC_URL" { 
                    [Environment]::SetEnvironmentVariable("ARBY_WEB3__RPC_URL", $value)
                }
                "PRIVATE_KEY" {
                    [Environment]::SetEnvironmentVariable("ARBY_WEB3__PRIVATE_KEY", $value)
                }
                "FLASHBOTS_AUTH_KEY" {
                    [Environment]::SetEnvironmentVariable("ARBY_FLASHBOTS__AUTH_KEY", $value)
                }
            }
            
            # Set original variable
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

    Write-Host "Dashboard available at http://localhost:8090"
    # Wait for processes
    Write-Host "Press Ctrl+C to stop all processes..."
    while ($true) {
        if ($botProcess.HasExited) {
            $exitCode = $botProcess.ExitCode
            throw "Bot process terminated unexpectedly with exit code: $exitCode"
        }
        if ($dashProcess.HasExited) {
            $exitCode = $dashProcess.ExitCode
            throw "Dashboard process terminated unexpectedly with exit code: $exitCode"
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
    Cleanup-Processes
}