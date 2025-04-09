# PowerShell script to start both the arbitrage bot and dashboard
# Ensures proper initialization and error handling

# Stop on any error
$ErrorActionPreference = "Stop"

# Store process IDs for cleanup
$Global:BotProcess = $null
$Global:DashProcess = $null

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

# Function to initialize memory bank
function Initialize-MemoryBank {
    Write-Host "Initializing memory bank..."
    python fix_memory_bank.py
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to initialize memory bank"
    }
}

# Function to start the dashboard
function Start-Dashboard {
    Write-Host "Starting dashboard..."
    $env:MEMORY_BANK_PATH = Join-Path $PWD "memory-bank"
    Write-Host "Setting MEMORY_BANK_PATH to: $env:MEMORY_BANK_PATH"
    # Add current directory to PYTHONPATH
    $env:PYTHONPATH = $PWD
    $script:DashProcess = Start-Process -FilePath "python" -ArgumentList "run_dashboard.py" -WorkingDirectory $PWD -PassThru -NoNewWindow
    return $script:DashProcess
}

# Function to start the arbitrage bot
function Start-ArbitrageBot {
    Write-Host "Starting arbitrage bot..."
    $script:BotProcess = Start-Process -FilePath "python" -ArgumentList "run_bot.py" -PassThru -NoNewWindow
    return $script:BotProcess
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
    
    # Kill any processes using port 9050
    try {
        $netstat = netstat -ano | Select-String ":9050"
        if ($netstat) {
            $processId = $netstat -split ' +' | Select-Object -Last 1
            Write-Host "Killing process using port 9050 (PID: $processId)..."
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Host "Warning: Error during process cleanup: $_" -ForegroundColor Yellow
    }
    
    # Wait for processes to terminate
    Write-Host "Waiting for processes to terminate..."
    Start-Sleep -Seconds 2
    
    # Create required directories
    Write-Host "Ensuring required directories exist..."
    Ensure-Directories
    
    # Initialize memory bank
    Initialize-MemoryBank
    
    # Start dashboard
    $dashProcess = Start-Dashboard
    Write-Host "Dashboard started with PID: $($dashProcess.Id)"
    
    # Wait for dashboard to initialize
    Write-Host "Waiting for dashboard to initialize..."
    Start-Sleep -Seconds 5
    
    # Start bot
    $botProcess = Start-ArbitrageBot
    Write-Host "Bot started with PID: $($botProcess.Id)"
    
    # Open dashboard in browser
    Write-Host "Opening dashboard in browser..."
    Start-Process "http://localhost:9050"
    
    Write-Host "Both processes started successfully"
    Write-Host "Dashboard available at http://localhost:9050"
    
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
