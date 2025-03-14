#
# Arbitrage System Dashboard (PowerShell Version)
# This script starts the new FastAPI-based dashboard
#

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "                        ARBITRAGE SYSTEM DASHBOARD (NEW)                       " -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in an elevated PowerShell session
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Note: Some operations may require Administrator privileges." -ForegroundColor Yellow
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
$venvPath = Join-Path -Path $PSScriptRoot -ChildPath "..\venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    try {
        & $venvPath
        Write-Host "Virtual environment activated successfully." -ForegroundColor Green
    }
    catch {
        Write-Host "Error activating virtual environment: $_" -ForegroundColor Red
        Write-Host "Continuing without virtual environment..." -ForegroundColor Yellow
    }
}
else {
    Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Yellow
    Write-Host "Continuing without virtual environment..." -ForegroundColor Yellow
}

# Check if FastAPI and Uvicorn are installed
Write-Host "Checking required packages..." -ForegroundColor Green
$requiredPackages = @("fastapi", "uvicorn", "python-dotenv")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    if (-not ((pip list 2>$null | Select-String $package) -ne $null)
) {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "Installing missing packages: $($missingPackages -join ', ')..." -ForegroundColor Yellow
    $requirementsPath = Join-Path -Path $PSScriptRoot -ChildPath "dashboard_requirements.txt"
    if (Test-Path $requirementsPath) {
        pip install -r $requirementsPath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error installing requirements. Please check your Python environment." -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host "Requirements file not found at $requirementsPath" -ForegroundColor Red
        exit 1
    }
}

# Check for .env file
$envFilePath = Join-Path -Path $PSScriptRoot -ChildPath ".env"
$envExamplePath = Join-Path -Path $PSScriptRoot -ChildPath ".env.example"

if (-not (Test-Path $envFilePath)) {
    Write-Host "No .env file found. Creating from example..." -ForegroundColor Yellow
    if (Test-Path $envExamplePath) {
        Copy-Item -Path $envExamplePath -Destination $envFilePath
        Write-Host "Created .env file. You need to edit it with your RPC URL!" -ForegroundColor Red
        Write-Host "Please open $envFilePath and set BASE_RPC_URL to your Base network RPC URL" -ForegroundColor Red
        
        # Ask if the user wants to edit it now
        $editNow = Read-Host "Would you like to edit the .env file now? (y/n)"
        if ($editNow -eq "y" -or $editNow -eq "Y") {
            # Try various editors in order of preference
            $editors = @("code", "notepad++", "notepad")
            $editorFound = $false
            
            foreach ($editor in $editors) {
                try {
                    if (Get-Command $editor -ErrorAction SilentlyContinue) {
                        Start-Process $editor -ArgumentList $envFilePath -Wait
                        $editorFound = $true
                        break
                    }
                } catch {
                    continue
                }
            }
            
            if (-not $editorFound) {
                Write-Host "Could not find a suitable editor. Please edit the file manually." -ForegroundColor Yellow
            }
        } else {
            Write-Host "Please remember to edit the .env file before using the dashboard." -ForegroundColor Yellow
        }
    } else {
        Write-Host "ERROR: .env.example not found! Please create a .env file manually." -ForegroundColor Red
        Write-Host "The file should contain at minimum: BASE_RPC_URL=your_rpc_url_here" -ForegroundColor Red
    }
}

# Start the dashboard
Write-Host "Starting dashboard server..." -ForegroundColor Green
$appPath = Join-Path -Path $PSScriptRoot -ChildPath "app.py"
if (Test-Path $appPath) {
    # Create required directories
    New-Item -Path (Join-Path -Path $PSScriptRoot -ChildPath "static") -ItemType Directory -Force | Out-Null
    New-Item -Path (Join-Path -Path $PSScriptRoot -ChildPath "static\css") -ItemType Directory -Force | Out-Null
    New-Item -Path (Join-Path -Path $PSScriptRoot -ChildPath "static\js") -ItemType Directory -Force | Out-Null
    New-Item -Path (Join-Path -Path $PSScriptRoot -ChildPath "templates") -ItemType Directory -Force | Out-Null
    
    try {
        Set-Location -Path $PSScriptRoot
        python $appPath --host localhost --port 8080
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error starting dashboard. Please check the logs for details." -ForegroundColor Red
        }
        Set-Location -Path ".."
    }
    catch {
        Write-Host "Error executing dashboard: $_" -ForegroundColor Red
    }
}
else {
    Write-Host "Dashboard application not found at $appPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")