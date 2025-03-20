# Dashboard startup script
# This script:
# 1. Activates the Python virtual environment
# 2. Checks for required environment variables
# 3. Starts the dashboard server

# Stop on first error
$ErrorActionPreference = "Stop"

# Script variables
$VENV_PATH = ".\venv"
$ENV_FILE = ".\.env"
$PYTHON_VERSION = "3.12"

# Function to check Python version
function Check-PythonVersion {
    try {
        $version = python --version 2>&1
        if ($version -match "Python $PYTHON_VERSION") {
            Write-Host "✅ Python $PYTHON_VERSION detected"
            return $true
        }
        Write-Host "❌ Python $PYTHON_VERSION required but found: $version"
        return $false
    }
    catch {
        Write-Host "❌ Python not found"
        return $false
    }
}

# Function to check environment file
function Check-EnvFile {
    if (Test-Path $ENV_FILE) {
        Write-Host "✅ Environment file found"
        return $true
    }
    Write-Host "❌ Environment file not found. Please copy .env.example to .env and configure it"
    return $false
}

# Function to activate virtual environment
function Activate-Venv {
    if (-not (Test-Path $VENV_PATH)) {
        Write-Host "Creating virtual environment..."
        python -m venv $VENV_PATH
    }
    
    # Activate virtual environment
    & "$VENV_PATH\Scripts\Activate.ps1"
    if ($?) {
        Write-Host "✅ Virtual environment activated"
        return $true
    }
    Write-Host "❌ Failed to activate virtual environment"
    return $false
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host "Installing dependencies..."
    pip install -e ".[dev]"
    if ($?) {
        Write-Host "✅ Dependencies installed"
        return $true
    }
    Write-Host "❌ Failed to install dependencies"
    return $false
}

# Main execution
try {
    Write-Host "Starting dashboard initialization..."
    
    # Check requirements
    if (-not (Check-PythonVersion)) { exit 1 }
    if (-not (Check-EnvFile)) { exit 1 }
    if (-not (Activate-Venv)) { exit 1 }
    if (-not (Install-Dependencies)) { exit 1 }
    
    Write-Host "`nStarting dashboard server..."
    Write-Host "Press Ctrl+C to stop the server`n"
    
    # Start the dashboard
    python -m arbitrage_bot.dashboard.run
}
catch {
    Write-Host "❌ Error: $_"
    exit 1
}
finally {
    # Deactivate virtual environment if it was activated
    if (Get-Command deactivate -ErrorAction SilentlyContinue) {
        deactivate
    }
}