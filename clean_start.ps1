# Clean Start Script for Listonian Arbitrage Bot
# This script ensures all previous processes are terminated and resources are released
# before starting the bot and dashboard

# Stop on any error
$ErrorActionPreference = "Stop"

# Store process IDs for cleanup
$Global:BotProcess = $null
$Global:DashProcess = $null

Write-Host "=== LISTONIAN ARBITRAGE BOT CLEAN START ===" -ForegroundColor Cyan
Write-Host "This script will terminate all related processes and start fresh" -ForegroundColor Cyan
Write-Host ""

# Function to kill all related processes
function Kill-AllRelatedProcesses {
    Write-Host "Terminating all related processes..." -ForegroundColor Yellow
    
    # Kill cmd.exe processes
    try {
        $cmdProcesses = Get-Process -Name "cmd" -ErrorAction SilentlyContinue
        if ($cmdProcesses) {
            Write-Host "Terminating cmd.exe processes..."
            $cmdProcesses | ForEach-Object {
                try {
                    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                    Write-Host "  Terminated cmd.exe (PID: $($_.Id))"
                } catch {
                    Write-Host "  Failed to terminate cmd.exe (PID: $($_.Id)): $_" -ForegroundColor Red
                }
            }
        }
    } catch {
        Write-Host "Error terminating cmd.exe processes: $_" -ForegroundColor Red
    }
    
    # Kill python.exe processes
    try {
        $pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
        if ($pythonProcesses) {
            Write-Host "Terminating python.exe processes..."
            $pythonProcesses | ForEach-Object {
                try {
                    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                    Write-Host "  Terminated python.exe (PID: $($_.Id))"
                } catch {
                    Write-Host "  Failed to terminate python.exe (PID: $($_.Id)): $_" -ForegroundColor Red
                }
            }
        }
    } catch {
        Write-Host "Error terminating python.exe processes: $_" -ForegroundColor Red
    }
    
    # Kill any processes using port 9050
    try {
        $netstat = netstat -ano | Select-String ":9050"
        if ($netstat) {
            Write-Host "Terminating processes using port 9050..."
            $netstat | ForEach-Object {
                try {
                    $line = $_ -split ' +'
                    $processId = $line[-1]
                    if ($processId -ne "0") {
                        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                        Write-Host "  Terminated process using port 9050 (PID: $processId)"
                    }
                } catch {
                    Write-Host "  Failed to terminate process using port 9050: $_" -ForegroundColor Red
                }
            }
        }
    } catch {
        Write-Host "Error terminating processes using port 9050: $_" -ForegroundColor Red
    }
}

# Function to clean log files
function Clean-LogFiles {
    Write-Host "Cleaning log files..." -ForegroundColor Yellow
    
    # Create logs directory if it doesn't exist
    if (-not (Test-Path "logs")) {
        New-Item -ItemType Directory -Path "logs" | Out-Null
        Write-Host "Created logs directory"
    }
    
    # Delete all log files
    try {
        Remove-Item -Path "logs\*.log" -Force -ErrorAction SilentlyContinue
        Write-Host "Deleted .log files"
    } catch {
        Write-Host "Error deleting .log files: $_" -ForegroundColor Red
    }
    
    # Delete all error files
    try {
        Remove-Item -Path "logs\*.err" -Force -ErrorAction SilentlyContinue
        Write-Host "Deleted .err files"
    } catch {
        Write-Host "Error deleting .err files: $_" -ForegroundColor Red
    }
}

# Function to start the arbitrage bot
function Start-ArbitrageBot {
    Write-Host "Starting arbitrage bot..." -ForegroundColor Green
    $script:BotProcess = Start-Process -FilePath "python" -ArgumentList "run_bot.py" -PassThru -NoNewWindow -RedirectStandardError "logs\bot.err"
    
    if ($script:BotProcess) {
        Write-Host "Bot started successfully (PID: $($script:BotProcess.Id))"
        return $true
    } else {
        Write-Host "Failed to start bot" -ForegroundColor Red
        return $false
    }
}

# Function to start the dashboard
function Start-Dashboard {
    Write-Host "Starting dashboard..." -ForegroundColor Green
    $env:MEMORY_BANK_PATH = Join-Path $PWD "memory-bank"
    Write-Host "Setting MEMORY_BANK_PATH to: $env:MEMORY_BANK_PATH"
    
    # Add current directory to PYTHONPATH
    $env:PYTHONPATH = $PWD
    
    $script:DashProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn new_dashboard.dashboard.app:app --host 0.0.0.0 --port 9050 --no-use-colors" -WorkingDirectory $PWD -PassThru -NoNewWindow -RedirectStandardError "logs\dashboard.err"
    
    if ($script:DashProcess) {
        Write-Host "Dashboard started successfully (PID: $($script:DashProcess.Id))"
        return $true
    } else {
        Write-Host "Failed to start dashboard" -ForegroundColor Red
        return $false
    }
}

# Function to open dashboard in browser
function Open-Dashboard {
    Write-Host "Opening dashboard in browser..." -ForegroundColor Green
    Start-Process "http://localhost:9050"
}

# Function to cleanup processes
function Cleanup-Processes {
    Write-Host "Cleaning up processes..." -ForegroundColor Yellow
    
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
    Write-Host "`nReceived shutdown signal" -ForegroundColor Yellow
    Cleanup-Processes
    exit 0
}
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $Global:CleanupHandler
$null = Register-ObjectEvent -InputObject ([Console]) -EventName CancelKeyPress -Action $Global:CleanupHandler

# Main execution
try {
    # Kill all related processes
    Kill-AllRelatedProcesses
    
    # Wait for processes to terminate and connections to close
    Write-Host "Waiting for processes to terminate and connections to close..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Clean log files
    Clean-LogFiles
    
    # Start bot
    $botStarted = Start-ArbitrageBot
    if (-not $botStarted) {
        throw "Failed to start bot"
    }
    
    # Wait for bot to initialize
    Write-Host "Waiting for bot to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # Start dashboard
    $dashboardStarted = Start-Dashboard
    if (-not $dashboardStarted) {
        throw "Failed to start dashboard"
    }
    
    # Wait for dashboard to initialize
    Write-Host "Waiting for dashboard to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Open dashboard in browser
    Open-Dashboard
    
    Write-Host ""
    Write-Host "=== SYSTEM STARTED SUCCESSFULLY ===" -ForegroundColor Green
    Write-Host "Bot PID: $($script:BotProcess.Id)"
    Write-Host "Dashboard PID: $($script:DashProcess.Id)"
    Write-Host "Bot logs: logs\bot.err"
    Write-Host "Dashboard logs: logs\dashboard.err"
    Write-Host "Dashboard URL: http://localhost:9050"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop all processes" -ForegroundColor Yellow
    
    # Wait for processes
    while ($true) {
        if ($script:BotProcess.HasExited) {
            $exitCode = $script:BotProcess.ExitCode
            throw "Bot process terminated unexpectedly with exit code: $exitCode"
        }
        if ($script:DashProcess.HasExited) {
            $exitCode = $script:DashProcess.ExitCode
            throw "Dashboard process terminated unexpectedly with exit code: $exitCode"
        }
        Start-Sleep -Seconds 1
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
} finally {
    # Cleanup on exit
    Cleanup-Processes
}