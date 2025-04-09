# PowerShell script to start all components of the arbitrage system
# This script ensures proper initialization and startup order

# Stop on any error
$ErrorActionPreference = "Stop"

# Store process IDs for cleanup
$Global:BotProcess = $null
$Global:DashboardProcess = $null
$Global:MCPProcesses = @{}

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

# Function to initialize required directories
function Initialize-RequiredDirectories {
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

# Function to test environment setup
function Test-Environment {
    # Check Python
    if (-not (Test-Python)) {
        throw "Python is not installed or not in PATH"
    }

    # Check .env file
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.production") {
            Copy-Item ".env.production" ".env"
            Write-Host "Copied .env.production to .env"
        } else {
            throw ".env file not found. Please create it with required credentials."
        }
    }
}

# Function to initialize memory bank
function Initialize-MemoryBank {
    Write-Host "Initializing memory bank..."
    python scripts/initialize_memory_bank.py
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to initialize memory bank"
    }
}

# Function to start MCP servers
function Start-MCPServers {
    Write-Host "Starting MCP servers..."

    # Load MCP configuration
    $mcpConfigPath = ".augment/mcp_config.json"
    if (-not (Test-Path $mcpConfigPath)) {
        Write-Host "MCP configuration not found: $mcpConfigPath" -ForegroundColor Yellow
        return $false
    }

    $mcpConfig = Get-Content $mcpConfigPath | ConvertFrom-Json

    # Start each MCP server
    foreach ($serverName in $mcpConfig.mcpServers.PSObject.Properties.Name) {
        $server = $mcpConfig.mcpServers.$serverName

        # Skip disabled servers
        if ($server.disabled) {
            Write-Host "Skipping disabled MCP server: $serverName" -ForegroundColor Yellow
            continue
        }

        Write-Host "Starting MCP server: $serverName"

        # Prepare environment variables
        $env = @{}
        if ($server.env) {
            foreach ($key in $server.env.PSObject.Properties.Name) {
                $value = $server.env.$key

                # Replace environment variable placeholders
                if ($value -match '^\${(.+)}$') {
                    $envVar = $matches[1]
                    if (Test-Path env:$envVar) {
                        $value = (Get-Item env:$envVar).Value
                    }
                }

                $env[$key] = $value
            }
        }

        # Start the server process
        try {
            $command = $server.command
            $cmdArgs = $server.args -join " "

            # Create process info
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = $command
            $psi.Arguments = $cmdArgs
            $psi.UseShellExecute = $false
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError = $true
            $psi.WorkingDirectory = $PWD

            # Add environment variables
            foreach ($key in $env.Keys) {
                $psi.EnvironmentVariables[$key] = $env[$key]
            }

            # Start process
            $process = New-Object System.Diagnostics.Process
            $process.StartInfo = $psi
            $process.Start() | Out-Null

            $Global:MCPProcesses[$serverName] = $process
            Write-Host "MCP server $serverName started with PID: $($process.Id)"
        }
        catch {
            Write-Host "Failed to start MCP server $serverName" -ForegroundColor Red
            Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    # Wait for servers to initialize
    Write-Host "Waiting for MCP servers to initialize..."
    Start-Sleep -Seconds 5

    return $true
}

# Function to start the arbitrage bot
function Start-ArbitrageBot {
    Write-Host "Starting arbitrage bot..."

    # Set environment variables
    $env:PYTHONPATH = $PWD
    $env:MEMORY_BANK_PATH = Join-Path $PWD "memory-bank"

    # Start the bot process
    $script:BotProcess = Start-Process -FilePath "python" -ArgumentList "run_bot.py" -PassThru -NoNewWindow -RedirectStandardError "logs/bot.err"

    Write-Host "Arbitrage bot started with PID: $($script:BotProcess.Id)"
    return $script:BotProcess
}

# Function to start the dashboard
function Start-Dashboard {
    Write-Host "Starting dashboard..."

    # Set environment variables
    $env:PYTHONPATH = $PWD
    $env:MEMORY_BANK_PATH = Join-Path $PWD "memory-bank"

    # Start the dashboard process
    $script:DashboardProcess = Start-Process -FilePath "python" -ArgumentList "run_dashboard.py" -PassThru -NoNewWindow -RedirectStandardError "logs/dashboard.err"

    Write-Host "Dashboard started with PID: $($script:DashboardProcess.Id)"
    return $script:DashboardProcess
}

# Function to open the dashboard in a browser
function Open-Dashboard {
    Write-Host "Opening dashboard in browser..."
    # Get dashboard port from .env file or use default
    $dashboardPort = 9050
    if (Test-Path ".env") {
        $envContent = Get-Content ".env" -ErrorAction SilentlyContinue
        $portLine = $envContent | Where-Object { $_ -match "DASHBOARD_PORT=(.*)" }
        if ($portLine) {
            $dashboardPort = $matches[1]
        }
    }
    Start-Process "http://localhost:$dashboardPort"
}

# Function to stop all processes
function Stop-AllProcesses {
    Write-Host "Cleaning up processes..."

    # Stop dashboard process
    if ($script:DashboardProcess -and -not $script:DashboardProcess.HasExited) {
        Stop-Process -Id $script:DashboardProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped dashboard process (PID: $($script:DashboardProcess.Id))"
    }

    # Stop bot process
    if ($script:BotProcess -and -not $script:BotProcess.HasExited) {
        Stop-Process -Id $script:BotProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped bot process (PID: $($script:BotProcess.Id))"
    }

    # Stop MCP processes
    foreach ($serverName in $Global:MCPProcesses.Keys) {
        $process = $Global:MCPProcesses[$serverName]
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped MCP server $serverName (PID: $($process.Id))"
        }
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

    # Kill any processes using our ports
    $ports = @(9050, 9051, 8772)
    foreach ($port in $ports) {
        $netstat = netstat -ano | Select-String ":$port"
        if ($netstat) {
            $processId = $netstat -split ' +' | Select-Object -Last 1
            Write-Host "Killing process using port $port (PID: $processId)..."
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }

    # Wait for processes to terminate
    Write-Host "Waiting for processes to terminate..."
    Start-Sleep -Seconds 5

    # Check environment
    Write-Host "Checking environment..."
    Test-Environment

    # Create required directories
    Write-Host "Ensuring required directories exist..."
    Initialize-RequiredDirectories

    # Initialize memory bank
    Initialize-MemoryBank

    # Start MCP servers
    Start-MCPServers

    # Start bot and dashboard
    $botProcess = Start-ArbitrageBot
    Start-Sleep -Seconds 5  # Wait for bot to initialize
    $dashboardProcess = Start-Dashboard

    # Wait for dashboard to initialize
    Start-Sleep -Seconds 5

    # Open dashboard in browser
    Open-Dashboard

    Write-Host "All components started successfully"
    Write-Host "Bot PID: $($botProcess.Id)"
    Write-Host "Dashboard PID: $($dashboardProcess.Id)"
    Write-Host "Dashboard URL: http://localhost:9051"

    # Wait for processes
    Write-Host "Press Ctrl+C to stop all processes..."
    while ($true) {
        if ($botProcess.HasExited) {
            $exitCode = $botProcess.ExitCode
            throw "Bot process terminated unexpectedly with exit code: $exitCode"
        }
        if ($dashboardProcess.HasExited) {
            $exitCode = $dashboardProcess.ExitCode
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
    Stop-AllProcesses
}
