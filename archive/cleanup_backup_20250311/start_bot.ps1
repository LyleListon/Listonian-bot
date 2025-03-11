# Enable CTRL-C handling
$PSDefaultParameterValues['*:ErrorAction'] = 'Stop'

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs"
}

# Set log files with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$botLogOut = "logs\bot_$timestamp.log"
$botLogErr = "logs\bot_$timestamp.err"
$dashboardLogOut = "logs\dashboard_$timestamp.log"
$dashboardLogErr = "logs\dashboard_$timestamp.err"

Write-Host "Starting Arbitrage Bot and Dashboard in LIVE MODE..." -ForegroundColor Green

# Check Python installation
try {
    python --version | Out-Null
} catch {
    Write-Host "Error: Python 3.8 or higher is required" -ForegroundColor Red
    exit 1
}

# Check required files
if (-not (Test-Path ".env.production")) {
    Write-Host "Error: .env.production file not found" -ForegroundColor Red
    Write-Host "Please copy .env.production.template and fill in your settings"
    exit 1
}

if (-not (Test-Path "configs\production_config.json")) {
    Write-Host "Error: configs/production_config.json not found" -ForegroundColor Red
    exit 1
}

# Validate paths
$validPaths = @(
    "production.py",
    "arbitrage_bot\dashboard\run.py"
)
foreach ($path in $validPaths) {
    if (-not (Test-Path $path)) {
        Write-Host "Error: Required file not found: $path" -ForegroundColor Red
        exit 1
    }
}

# Load environment variables
$envVars = Get-Content .env.production | Where-Object { $_ -match '^[^#]' } | ForEach-Object {
    $key, $value = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim())
}

# Function to start a Python process
function Start-PythonProcess {
    param(
        [string]$Arguments,
        [string]$LogFileOut,
        [string]$LogFileErr
    )
    
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "python"
    $startInfo.Arguments = $Arguments
    $startInfo.UseShellExecute = $false
    
    $process = Start-Process -FilePath $startInfo.FileName -ArgumentList $startInfo.Arguments -NoNewWindow -PassThru -RedirectStandardOutput $LogFileOut -RedirectStandardError $LogFileErr
    
    return $process
}

Write-Host "Starting bot process..." -ForegroundColor Green
$botProcess = Start-PythonProcess "production.py" $botLogOut $botLogErr

Write-Host "Starting dashboard process..." -ForegroundColor Green
$dashboardProcess = Start-PythonProcess "-m arbitrage_bot.dashboard.run" $dashboardLogOut $dashboardLogErr

Write-Host "Bot and dashboard started in LIVE MODE." -ForegroundColor Green
Write-Host "Bot logs:" -ForegroundColor Yellow
Write-Host "  Output: $botLogOut" -ForegroundColor Yellow
Write-Host "  Errors: $botLogErr" -ForegroundColor Yellow
Write-Host "Dashboard logs:" -ForegroundColor Yellow
Write-Host "  Output: $dashboardLogOut" -ForegroundColor Yellow
Write-Host "  Errors: $dashboardLogErr" -ForegroundColor Yellow

# Function to tail a log file
function Show-LogTail {
    param(
        [string]$LogFile,
        [string]$ProcessName,
        [string]$Type = "OUT"
    )
    
    try {
        Get-Content -Path $LogFile -Wait -Tail 10 | ForEach-Object {
            $color = if ($Type -eq "ERR") { "Red" } else { "White" }
            Write-Host "[$ProcessName] $_" -ForegroundColor $color
        }
    } catch {
        # Ignore errors when file is not yet created
    }
}

try {
    # Start log tailing in background jobs
    $botOutJob = Start-Job -ScriptBlock ${function:Show-LogTail} -ArgumentList $botLogOut,"Bot","OUT"
    $botErrJob = Start-Job -ScriptBlock ${function:Show-LogTail} -ArgumentList $botLogErr,"Bot","ERR"
    $dashboardOutJob = Start-Job -ScriptBlock ${function:Show-LogTail} -ArgumentList $dashboardLogOut,"Dashboard","OUT"
    $dashboardErrJob = Start-Job -ScriptBlock ${function:Show-LogTail} -ArgumentList $dashboardLogErr,"Dashboard","ERR"
    
    # Wait for processes
    Write-Host "`nPress Ctrl+C to stop the bot..." -ForegroundColor Yellow
    Wait-Process -Id $botProcess.Id, $dashboardProcess.Id
} finally {
    # Cleanup
    if ($botProcess -and -not $botProcess.HasExited) {
        Write-Host "Stopping bot process..." -ForegroundColor Yellow
        $botProcess.CloseMainWindow()
    }
    if ($dashboardProcess -and -not $dashboardProcess.HasExited) {
        Write-Host "Stopping dashboard process..." -ForegroundColor Yellow
        $dashboardProcess.CloseMainWindow()
    }
    
    # Stop log tailing jobs
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    
    Write-Host "Shutdown complete" -ForegroundColor Green
}
