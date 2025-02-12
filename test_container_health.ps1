# Test Container Health PowerShell Script

Write-Host "`n=== Testing Data Persistence ===" -ForegroundColor Cyan

# Test VSCode remote data persistence
$vsCodeDataPath = "/root/.vscode-remote/data"
$testFile = Join-Path $vsCodeDataPath "test_persistence.json"
$testData = @{
    timestamp = [DateTimeOffset]::Now.ToUnixTimeSeconds()
    test = "persistence"
} | ConvertTo-Json

Write-Host "Writing test data..." -ForegroundColor Yellow
if (!(Test-Path $vsCodeDataPath)) {
    New-Item -Path $vsCodeDataPath -ItemType Directory -Force
}
$testData | Out-File -FilePath $testFile
Write-Host "Test file created at: $testFile"

Write-Host "`n=== Testing Container Health ===" -ForegroundColor Cyan

# Start dashboard in background if not running
$dashboardProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*dashboard*" }
if (!$dashboardProcess) {
    Write-Host "Starting dashboard service..." -ForegroundColor Yellow
    Start-Process python -ArgumentList "start_dashboard.py" -NoNewWindow
    Start-Sleep -Seconds 5  # Wait for dashboard to start
}

# Test dashboard health
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing
    Write-Host "Dashboard Health Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Dashboard health check failed: $_" -ForegroundColor Red
}

# Check Python processes
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "Python processes running: ✓" -ForegroundColor Green
} else {
    Write-Host "No Python processes found: ✗" -ForegroundColor Red
}

# Check PowerShell configuration
$psConfig = "/root/.config/powershell/Microsoft.PowerShell_profile.ps1"
if (Test-Path $psConfig) {
    Write-Host "PowerShell profile exists: ✓" -ForegroundColor Green
} else {
    Write-Host "PowerShell profile missing: ✗" -ForegroundColor Red
}

Write-Host "`n=== Testing Conversation Persistence ===" -ForegroundColor Cyan

# Check Roo Code conversation storage
$rooDataPath = "/root/.vscode-remote/data/User/globalStorage/rooveterinaryinc.roo-cline"
if (Test-Path $rooDataPath) {
    Write-Host "Roo Code data directory exists: ✓" -ForegroundColor Green
    $convFiles = Get-ChildItem -Path (Join-Path $rooDataPath "conversations") -Filter "*.json" -ErrorAction SilentlyContinue
    Write-Host "Found $($convFiles.Count) conversation files"
} else {
    Write-Host "Roo Code data directory missing: ✗" -ForegroundColor Red
}

Write-Host "`nTests completed. Please check results above." -ForegroundColor Cyan