# Start dashboard initialization
Write-Host "Starting dashboard initialization..."

# Check Python version
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3.12") {
    Write-Host "✅ Python 3.12 detected"
} else {
    Write-Host "❌ Python 3.12 required"
    exit 1
}

# Check environment file
if (Test-Path ".env") {
    Write-Host "✅ Environment file found"
    # Load environment variables
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.+)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$key" -Value $value
        }
    }
} else {
    Write-Host "❌ Environment file missing"
    exit 1
}

# Activate virtual environment
if (-not (Test-Path "venv")) {
    python -m venv venv
}
. .\venv\Scripts\Activate.ps1
Write-Host "✅ Virtual environment activated"

# Install dependencies
Write-Host "Installing dependencies..."
pip install -r requirements.txt
Write-Host "✅ Dependencies installed"

# Start dashboard server
Write-Host "`nStarting dashboard server..."
Write-Host "Press Ctrl+C to stop the server`n"
$port = $env:DASHBOARD_PORT
if (-not $port) { $port = "3000" }
python -m uvicorn app:app --reload --port $port --host $env:DASHBOARD_HOST