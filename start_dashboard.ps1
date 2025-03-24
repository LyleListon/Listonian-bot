# Dashboard startup script

# Stop any existing Python processes
function Stop-PythonProcesses {
    Write-Host "Stopping any existing Python processes..."
    Get-Process | Where-Object { $_.ProcessName -eq "python" } | ForEach-Object {
        try {
            $_ | Stop-Process -Force
            Write-Host "Stopped Python process with PID: $($_.Id)"
        } catch {
            Write-Warning "Failed to stop process: $_"
        }
    }
    Start-Sleep -Seconds 2  # Give processes time to fully stop
}

# Function to check if port is in use
function Test-PortInUse {
    param($port)
    
    $inUse = $false
    $listener = $null
    
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $port)
        $listener.Start()
        $inUse = $false
    } catch {
        $inUse = $true
    } finally {
        if ($listener -ne $null) {
            $listener.Stop()
        }
    }
    
    return $inUse
}

# Function to find an available port
function Find-AvailablePort {
    param(
        [int]$startPort = 9095,
        [int]$endPort = 9100
    )
    
    for ($port = $startPort; $port -le $endPort; $port++) {
        if (-not (Test-PortInUse $port)) {
            return $port
        }
    }
    
    throw "No available ports found between $startPort and $endPort"
}

# Function to ensure required directories exist
function Ensure-Directories {
    $dirs = @(
        "logs",
        "new_dashboard/dashboard/templates",
        "new_dashboard/dashboard/static",
        "new_dashboard/dashboard/static/js",
        "new_dashboard/dashboard/static/css"
    )
    
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            Write-Host "Creating directory: $dir"
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host "Installing/Updating dependencies..."
    pip install -e . | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install package dependencies"
    }
    
    pip install -r requirements.txt | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install requirements"
    }
}

# Function to verify template files
function Verify-Templates {
    Write-Host "Verifying template files..."
    $templateFiles = @(
        "new_dashboard/dashboard/templates/base.html",
        "new_dashboard/dashboard/templates/index.html"
    )
    
    foreach ($file in $templateFiles) {
        if (-not (Test-Path $file)) {
            throw "Template file not found: $file"
        } else {
            Write-Host "Found template: $file"
        }
    }
}

# Function to start the dashboard
function Start-Dashboard {
    param($port)
    
    Write-Host "Starting dashboard on port $port..."
    $env:PYTHONPATH = "."
    $script:DashProcess = Start-Process -FilePath "python" -ArgumentList "-m new_dashboard.dashboard.run --port $port" -PassThru -NoNewWindow -RedirectStandardError "logs/dashboard.err"
    return $script:DashProcess
}

# Function to cleanup processes
function Cleanup-Processes {
    param($port)
    
    Write-Host "Cleaning up processes..."
    if ($script:DashProcess -ne $null) {
        try {
            Stop-Process -Id $script:DashProcess.Id -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Warning "Failed to stop dashboard process: $_"
        }
    }
    
    # Kill any process using our port
    $processId = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
    if ($processId) {
        Write-Host "Stopped process using port $port"
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}

# Function to wait for service
function Wait-ForService {
    param(
        $port,
        $timeoutSeconds = 30
    )
    
    Write-Host "Waiting for service at http://localhost:$port..."
    $start = Get-Date
    $success = $false
    
    while (-not $success -and ((Get-Date) - $start).TotalSeconds -lt $timeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$port" -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "Service is up!"
                $success = $true
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    
    if (-not $success) {
        throw "Timeout waiting for service"
    }
}

# Main execution
try {
    Write-Host "Checking environment..."
    Write-Host "Python Path: $((Get-Command python).Path)"
    Write-Host "Current directory: $(Get-Location)"
    
    # Stop any existing Python processes
    Stop-PythonProcesses
    
    # Find available port
    $port = Find-AvailablePort
    Write-Host "Using port: $port"
    
    # Ensure directories exist
    Write-Host "Ensuring required directories exist..."
    Ensure-Directories
    
    # Install dependencies
    Install-Dependencies
    
    # Verify templates
    Verify-Templates
    
    # Start dashboard
    $process = Start-Dashboard -port $port
    
    # Wait for service
    Wait-ForService -port $port
    
    # Keep script running
    Write-Host "Dashboard is running. Press Ctrl+C to stop."
    while ($true) {
        Start-Sleep -Seconds 1
        if ($process.HasExited) {
            throw "Dashboard process terminated unexpectedly"
        }
    }
} catch {
    Write-Error "Error: $_"
} finally {
    Cleanup-Processes -port $port
}